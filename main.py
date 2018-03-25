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
    print('smc.headers_per_shard: {}'.format(smc_handler.headers_per_shard))
    print('smc.collators: {}'.format(smc_handler.collators))
    for shard_id in range(smc_handler.num_shards):
        print('[shard_id]: {}'.format(shard_id))


        for header in smc_handler.headers_per_shard[shard_id]:
            print('header: {}'.format(header))
            # print('[collation {}] header: {}'.format(
            #     smc_handler.collators[header.shard_id, header.period],
            #     header)
            # )


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
asyncio.gather(*coros)
loop.run_forever()

