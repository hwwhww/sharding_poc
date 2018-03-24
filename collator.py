import asyncio
import logging
import random
import time

from message import (
    CollationHeader,
)
from main_chain import (
    PERIOD_TIME,
)

logger = logging.getLogger("collator")


async def collator(network, shard_id, address, smc):
    if address not in smc.collator_pool:
        raise ValueError("Collator pool in SMC does not contain the given address")
    collation_coros_and_periods = []  # [(coroutine, period), ...]

    last_period = None
    while True:
        # wait for next period
        while smc.period == last_period:
            asyncio.sleep(PERIOD_TIME / 2)
        last_period = smc.period

        # remove finished coroutines
        collation_coros_and_periods = [
            (coro, period)
            for coro, period
            in collation_coros_and_periods
            if not coro.done()
        ]

        # when a new period starts, check if we're eligible for some shard and if so start to
        # collate
        for period in smc.get_eligible_periods(shard_id, address):
            if period in [p for _, p in collation_coros_and_periods]:
                continue  # collation coro already running
            logger.info("Detected eligibility of collator {} for period {} in shard {}".format(
                address,
                period,
                shard_id,
            ))

            coro = await collate(network, shard_id, period, address, smc)
            collation_coros_and_periods.append((coro, period))


async def collate(network, shard_id, period, address, smc):
    logger.info('smc.period: {}, period: {}'.format(smc.period, period))
    while smc.period < period:
        await asyncio.sleep(PERIOD_TIME / 5)

    # overslept
    if smc.period != period:
        logger.warning("Missed submitting proposal".format(period))
        return

    end_time = time.time() + PERIOD_TIME / 2

    message_queue = asyncio.Queue()
    network.outputs.append(message_queue)
    proposals = await collect_proposals(network, shard_id, period, message_queue, end_time)
    network.outputs.remove(message_queue)
    if proposals:
        smc.add_header(address, random.choice(proposals))
    else:
        logger.warning("No proposal collected")


async def collect_proposals(network, shard_id, period, message_queue, end_time):
    logger.info("Collecting proposals")
    proposals = []
    while True:
        try:
            coro = collect_proposal(shard_id, period, message_queue)
            proposal = await asyncio.wait_for(coro, timeout=end_time - time.time())
            proposals.append(proposal)
        except asyncio.TimeoutError:
            logger.info("Collected {} proposals".format(len(proposals)))
            return proposals


async def collect_proposal(shard_id, period, message_queue):
    while True:
        message = await message_queue.get()
        logger.info('collecting proposal')
        if isinstance(message, CollationHeader):
            if message.shard_id == shard_id and message.period == period:
                return message
