import asyncio
import logging

from collator import collator
from proposer import proposer
from main_chain import (
    MainChain,
    PERIOD_TIME,
)

from network import (
    Network,
    broadcast,
    consumer,
    producer,
)
from smc_handler import SMCHandler


async def stop():
    await asyncio.sleep(PERIOD_TIME * 5.5)
    loop.stop()

    print('--------------- SMC ---------------')
    for shard_id in smc_handler.shard_ids:
        shard = smc_handler.shards[shard_id]
        print('-------- shard {} --------'.format(shard_id))
        for number in range(-1, shard.best_number + 1):
            for header in shard.headers_by_number[number]:
                collator = smc_handler.collators.get((shard_id, header.period), None)
                print("Header #{} collated by {}: {}".format(number, collator, header))


collator_pool = list(range(5))
proposer_pool = list(range(10))

main_chain = MainChain()
smc_handler = SMCHandler(main_chain, 2, 5, collator_pool)

general_coros = [
    broadcast(Network),
    main_chain.run(),
    smc_handler.run(),
    stop(),
]

collator_coros = [
    collator(Network, address, smc_handler) for address in collator_pool
]

proposer_coros = [
    proposer(Network, 0, address, smc_handler)
    for address in proposer_pool[:len(proposer_pool) // 2]
] + [
    proposer(Network, 1, address, smc_handler)
    for address in proposer_pool[len(proposer_pool) // 2:]
]

coros = general_coros + collator_coros + proposer_coros


loop = asyncio.get_event_loop()
# asyncio.gather(*coros)
for coro in coros:
    loop.create_task(coro)
loop.run_forever()

