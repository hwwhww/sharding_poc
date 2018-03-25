import asyncio
import logging
from collections import namedtuple
import time

from message import (
    CollationHeader,
    Collation,
)
from main_chain import (
    PERIOD_TIME,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proposer")


async def proposer(network, shard_id, address, smc_handler):
    await asyncio.sleep(0.1)  # give collator head start
    message_queue = asyncio.Queue()
    network.outputs.append(message_queue)

    my_proposal = None
    my_collation = None
    last_number = 0

    while True:
        # publish proposal for next collation
        current_collation_header = smc_handler.get_head(shard_id)

        my_proposal = CollationHeader(
            shard_id,
            address,
            current_collation_header.number + 1,
            smc_handler.get_current_period()
        )
        my_collation = Collation(
            my_proposal,
            "",
        )
        logger.info("proposing: {}".format(my_proposal))
        await network.input.put(my_proposal)
        # latency = network.latency_distribution()
        # await asyncio.sleep(latency)
        asyncio.ensure_future(reveal(network, smc_handler, my_collation))

        await smc_handler.wait_for_next_period()


async def reveal(network, smc_handler, collation):
    await smc_handler.wait_for_period(collation.header.period)

    if smc_handler.get_head(collation.header.shard_id) == collation.header:
        logger.info("revealing: {}".format(collation))
        await network.input.put(collation.body)
