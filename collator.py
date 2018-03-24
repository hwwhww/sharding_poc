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


async def collator(network, address, smc):
    if address not in smc.collator_pool:
        raise ValueError("Collator pool in SMC does not contain the given address")
    collation_coros_and_periods = []  # [(coroutine, period), ...]

    last_period = None
    while True:
        # wait for next period
        while smc.period == last_period:
            await asyncio.sleep(PERIOD_TIME / 2)
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
        for (shard_id, period) in smc.get_eligible_periods(address):
            if period in [p for _, p in collation_coros_and_periods]:
                continue  # collation coro already running
            logger.info("Detected eligibility of collator {} for period {} in shard {}".format(
                address,
                period,
                shard_id,
            ))

            coro = asyncio.ensure_future(collate(network, shard_id, period, address, smc))
            collation_coros_and_periods.append((coro, period))


async def collate(network, shard_id, period, address, smc):
    message_queue = asyncio.Queue()
    network.outputs.append(message_queue)
    logger.info("Listening for proposals for period {}".format(period))

    while smc.period < period:
        await asyncio.sleep(PERIOD_TIME / 2)
    await asyncio.sleep(PERIOD_TIME / 2)

    messages = []
    while not message_queue.empty():
        messages.append(message_queue.get_nowait())
    proposals = [
        message for message in messages
        if isinstance(message, CollationHeader)
        and message.shard_id == shard_id
        and message.period == period
    ]

    # overslept
    if smc.period != period:
        logger.warning("Missed submitting proposal".format(period))
        return

    network.outputs.remove(message_queue)
    if proposals:
        logger.info("[P: {}] Received {} proposals".format(period, len(proposals)))
        proposal = random.choice(proposals)
        smc.add_header(address, proposal)
    else:
        logger.warning("[P: {}] No proposal collected".format(period))
