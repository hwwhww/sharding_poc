import asyncio
import logging
from collections import namedtuple
import time
import random
from cytoolz import (
    first,
)

from eth_utils import (
    encode_hex,
    int_to_big_endian,
)

from collator import (
    check_availability,
)
from message import (
    CollationHeader,
    Collation,
)
from main_chain import (
    PERIOD_TIME,
)
from utils import (
    receive_and_broadcast_message,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proposer")


async def proposer(network, shard_id, address, smc_handler):
    node = network.find_node(address)

    shard = smc_handler.shards[shard_id]

    my_proposal = None
    my_collation = None

    while True:
        await receive_and_broadcast_message(node)

        # publish proposal for next collation
        current_collation_header = next(
            header for header in shard.get_candidate_head_iterator()
            if check_availability(header)
        )

        my_proposal = CollationHeader(
            shard_id=shard_id,
            proposer=address,
            number=current_collation_header.number + 1,
            period=smc_handler.get_current_period(),
            hash=encode_hex(int_to_big_endian(random.getrandbits(8 * 4)))[2:],
            parent_hash=current_collation_header.hash,
        )
        my_collation = Collation(
            my_proposal,
            "",
        )
        logger.info("{} proposing: {}".format(address, my_proposal))
        await node.input.put(my_proposal)

        logger.info('added message {} to the queue'.format(my_proposal))
        # latency = network.latency_distribution()
        # await asyncio.sleep(latency)
        asyncio.ensure_future(reveal(network, node, smc_handler, my_collation))

        await smc_handler.wait_for_next_period()


async def reveal(network, node, smc_handler, collation):
    await smc_handler.wait_for_period(collation.header.period + 1)

    shard = smc_handler.shards[collation.header.shard_id]
    if collation.header.hash in shard.headers_by_hash:
        logger.info("revealing: {}".format(collation))
        await node.input.put(collation.body)
