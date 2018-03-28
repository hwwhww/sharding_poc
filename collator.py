import asyncio
import logging
import random

from network import (
    Node,
)
from message import (
    CollationHeader,
)
from main_chain import (
    PERIOD_TIME,
)

from cytoolz import (
    iterate,
    nth,
    merge,
)

from eth_utils import (
    big_endian_to_int,
    decode_hex,
)

logger = logging.getLogger("collator")

WINDBACK_LENGTH = 25


async def collator(network, address, smc_handler):
    if address not in smc_handler.collator_pool:
        raise ValueError("Collator pool in SMC does not contain the given address")
    # collation_tasks_and_periods = []  # [(coroutine, period), ...]
    collation_tasks = {}

    while True:
        # remove finished tasks
        collation_tasks = {
            (shard_id, period): task
            for (shard_id, period), task in collation_tasks.items()
            if not task.done()
        }

        # when a new period starts, check if we're eligible for some shard and if so start to
        # collate
        for (shard_id, period) in smc_handler.get_eligible_periods(address):
            if (shard_id, period) in collation_tasks:
                continue  # collation coro already running
            logger.info("Detected eligibility of collator {} for period {} in shard {}".format(
                address,
                period,
                shard_id,
            ))

            task = asyncio.ensure_future(collate(network, shard_id, period, address, smc_handler))
            collation_tasks[shard_id, period] = task

        await smc_handler.wait_for_next_period()


async def collate(network, shard_id, period, address, smc_handler):
    message_queue = asyncio.Queue()
    node = Node(network, address + ' ' + str(period))
    network.login(node)
    network.add_peers(node, message_queue)

    logger.info("Listening for proposals for period {}".format(period))

    shard = smc_handler.shards[shard_id]

    availabilities = {}
    while True:
        # stop once it's time to submit (TODO: timing and cancel windback if necessary)
        if smc_handler.get_current_period() >= period:
            await asyncio.sleep(PERIOD_TIME / 2)
            break

        # get a candidate head of which we don't know if it's available or not
        candidate_iterator = shard.get_candidate_head_iterator()
        try:
            candidate_head = next(
                header for header in candidate_iterator if header.hash not in availabilities
            )
        except StopIteration:
            await smc_handler.wait_for_next_block()
            continue

        # windback
        checked_availabilities = await windback(network, shard, candidate_head, availabilities)
        availabilities = merge(availabilities, checked_availabilities)

    # get best head of which we know is available
    candidate_iterator = shard.get_candidate_head_iterator()
    try:
        parent_header = next(
            header for header in candidate_iterator if availabilities.get(header.hash, False)
        )
    except StopIteration:
        logger.warning("Could not find available chain to built on top of")
        return
    else:
        logger.info("Extend chain with head {}".format(parent_header))

    # filter received proposals
    messages = []

    while not message_queue.empty():
        messages.append(message_queue.get_nowait())

    proposals = [
        message for message in messages
        if isinstance(message, CollationHeader)
        and message.shard_id == shard_id
        and message.period == period
        and message.parent_hash == parent_header.hash
    ]

    # overslept
    if smc_handler.get_current_period() > period:
        logger.warning("Missed submitting proposal".format(period))
        return

    network.remove_peer(node)

    if proposals:
        logger.info("Submitting one of {} collected proposals".format(len(proposals)))
        proposal = random.choice(proposals)
        smc_handler.add_header(address, proposal)
    else:
        logger.warning("No suitable proposals collected".format(period))


async def windback(network, shard, header, availability_cache):
    assert WINDBACK_LENGTH > 0

    def add_parent_header(headers):
        parent_header = shard.headers_by_hash[headers[-1].parent_hash]
        return headers + [parent_header]

    header_chain = iterate(add_parent_header, [header])
    n_parents = min(WINDBACK_LENGTH - 1, header.number)
    headers_to_check = reversed(nth(n_parents, header_chain))  # from root to leaf

    availabilities = {}  # {hash: available, ...} for all headers checked here

    for header in headers_to_check:
        if header.hash in availabilities:
            available = availability_cache[header.hash]
        else:
            available = check_availability(header)
            availabilities[header.hash] = available

        if not available:
            # don't check children of unavailable collations
            break

    # remaining collations are unavailable as one of their ancestors is unavailable
    for header in headers_to_check:
        availabilities[header.hash] = False

    return availabilities


def check_availability(header):
    if header.proposer == 0:
        return False
    else:
        return True
