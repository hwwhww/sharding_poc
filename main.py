import asyncio
import logging
import random

from collator import collator
from proposer import proposer
from main_chain import (
    MainChain,
    PERIOD_TIME,
)

from network import (
    Network,
    broadcast,
    Node,
)
from smc_handler import SMCHandler


random.seed(0)

logger = logging.getLogger("collator")


async def stop():
    await asyncio.sleep(PERIOD_TIME * 10.5)
    loop.stop()

    logger.info('--------------- SMC ---------------')
    for shard_id in smc_handler.shard_ids:
        shard = smc_handler.shards[shard_id]
        logger.info('-------- shard {} --------'.format(shard_id))
        for number in range(-1, shard.best_number + 1):
            for header in shard.headers_by_number[number]:
                collator = smc_handler.collators.get((shard_id, header.period), None)
                logger.info("Header #{} collated by {}: {}".format(number, collator, header))


collator_pool = ['collator_{}'.format(i) for i in range(5)]
proposer_pool = ['proposer_{}'.format(i) for i in range(10)]

main_chain = MainChain()
smc_handler = SMCHandler(main_chain, 2, 5, collator_pool)

network = Network()

# Set the p2p connections between proposers
nodes = [Node(network, address) for address in proposer_pool]
network.nodes = nodes
network.generate_peers()

general_coros = [
    main_chain.run(),
    smc_handler.run(),
    stop(),
]

collator_coros = [
    collator(network, address, smc_handler)
    for address in collator_pool
]

proposer_coros = [
    proposer(network, 0, address, smc_handler)
    for address in proposer_pool[:len(proposer_pool) // 2]
] + [
    proposer(network, 1, address, smc_handler)
    for address in proposer_pool[len(proposer_pool) // 2:]
] + [
    broadcast(network, address)
    for address in proposer_pool
]

coros = general_coros + collator_coros + proposer_coros


loop = asyncio.get_event_loop()
# asyncio.gather(*coros)
for coro in coros:
    loop.create_task(coro)
loop.run_forever()
