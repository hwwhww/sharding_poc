import asyncio
import logging

from collator import collator
from proposer import proposer
from main_chain import main_chain

from network import (
    Network,
    broadcast,
    consumer,
    producer,
)
from smc_handler import SMCHandler

loop = asyncio.get_event_loop()

asyncio.ensure_future(broadcast(Network))

address = 0
collator_pool = list(range(5))

smc = SMCHandler(2, 5, collator_pool)
asyncio.ensure_future(main_chain(smc))

for i in collator_pool:
    asyncio.ensure_future(collator(Network, i, smc))
for i in range(5):
    asyncio.ensure_future(proposer(Network, 0, i, smc))
    asyncio.ensure_future(proposer(Network, 1, i+10, smc))

async def stop():
    await asyncio.sleep(20)
    loop.stop()

    print('--------------- SMC ---------------')
    print('smc.headers_per_shard: {}'.format(smc.headers_per_shard))
    print('smc.collators: {}'.format(smc.collators))
    for shard_id in range(smc.num_shards):
        print('[shard_id]: {}'.format(shard_id))
        

        for header in smc.headers_per_shard[shard_id]:
            print('header: {}'.format(header))
            # print('[collation {}] header: {}'.format(
            #     smc.collators[header.shard_id, header.period],
            #     header)
            # )


asyncio.ensure_future(stop())

loop.run_forever()

