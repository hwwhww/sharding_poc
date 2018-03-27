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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proposer")


async def proposer(network, shard_id, address, smc_handler):
    message_queue = asyncio.Queue()
    network.outputs.append(message_queue)

    shard = smc_handler.shards[shard_id]

    my_proposal = None
    my_collation = None

    while True:
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
        logger.info("proposing: {}".format(my_proposal))
        await network.input.put(my_proposal)
        # latency = network.latency_distribution()
        # await asyncio.sleep(latency)
        asyncio.ensure_future(reveal(network, smc_handler, my_collation))

        await smc_handler.wait_for_next_period()


async def reveal(network, smc_handler, collation):
    await smc_handler.wait_for_period(collation.header.period)

    shard = smc_handler.shards[collation.header.shard_id]
    if collation.header.hash in shard.headers_by_hash:
        logger.info("revealing: {}".format(collation))
        await network.input.put(collation.body)
