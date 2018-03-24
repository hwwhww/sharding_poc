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


async def proposer(network, shard_id, address, smc):
    message_queue = asyncio.Queue()
    network.outputs.append(message_queue)

    my_proposal = None
    my_collation = None
    last_period = 0
    
    while True:
        while smc.period < last_period:
            await asyncio.sleep(PERIOD_TIME / 5)
        last_period = smc.period
            
        # if my last proposal got accepted reveal the corresponding collation

        # publish proposal for next collation
        current_collation_header = smc.get_head(shard_id)
        logger.info('current_collation_header: {}'.format(current_collation_header))
        
        my_proposal = CollationHeader(
            shard_id,
            address,
            current_collation_header.number + 1,
            smc.period
        )
        my_collation = Collation(
            my_proposal,
            "",
        )
        logger.info("proposing: {}".format(my_proposal))
        await network.input.put(my_proposal)
        latency = network.latency_distribution()
        await asyncio.sleep(latency)

        asyncio.ensure_future(reveal(network, smc, my_collation))

        


async def reveal(network, smc, collation):
    while smc.period < collation.header.period:
        await asyncio.sleep(PERIOD_TIME / 5)

    if smc.get_head(collation.header.shard_id) == collation.header:
        logger.info("revealing: {}".format(collation))
        await network.input.put(collation.body)
