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
        for period in smc.get_eligible_periods(shard_id, address):
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

    while smc.period < period:
        await asyncio.sleep(PERIOD_TIME / 2)

    proposals = []
    while not message_queue.empty():
        message = await message_queue.get()
        if isinstance(message, CollationHeader):
            logger.info('[P: {}] In the queue, current_period: {}, message: {}'.format(period, smc.period, message))
            if message.shard_id == shard_id and message.period == period:
                proposals.append(message)

    # overslept
    if smc.period != period:
        logger.warning("Missed submitting proposal".format(period))
        return

    network.outputs.remove(message_queue)
    if proposals:
        proposal = random.choice(proposals)
        logger.info('[P: {}] proposals: {}, proposal: {}'.format(period, proposals, proposal))
        smc.add_header(address, proposal)
    else:
        logger.warning("[P: {}] No proposal collected".format(period))
