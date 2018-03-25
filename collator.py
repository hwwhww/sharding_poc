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


async def collator(network, address, smc_handler):
    if address not in smc_handler.collator_pool:
        raise ValueError("Collator pool in SMC does not contain the given address")
    collation_tasks_and_periods = []  # [(coroutine, period), ...]

    while True:
        # remove finished tasks
        collation_tasks_and_periods = [
            (task, period)
            for task, period
            in collation_tasks_and_periods
            if not task.done()
        ]

        # when a new period starts, check if we're eligible for some shard and if so start to
        # collate
        for (shard_id, period) in smc_handler.get_eligible_periods(address):
            if period in [p for _, p in collation_tasks_and_periods]:
                continue  # collation coro already running
            logger.info("Detected eligibility of collator {} for period {} in shard {}".format(
                address,
                period,
                shard_id,
            ))

            task = asyncio.ensure_future(collate(network, shard_id, period, address, smc_handler))
            collation_tasks_and_periods.append((task, period))

        await smc_handler.wait_for_next_period()


async def collate(network, shard_id, period, address, smc_handler):
    message_queue = asyncio.Queue()
    network.outputs.append(message_queue)
    logger.info("Listening for proposals for period {}".format(period))

    await smc_handler.wait_for_period(period)
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
    if smc_handler.get_current_period() > period:
        logger.warning("Missed submitting proposal".format(period))
        return

    network.outputs.remove(message_queue)

    if proposals:
        logger.info("Received {} proposals".format(len(proposals)))
        proposal = random.choice(proposals)
        smc_handler.add_header(address, proposal)
    else:
        logger.warning("No proposals collected".format(period))
