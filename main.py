import asyncio

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

smc = SMCHandler(1, 5, [0])
asyncio.ensure_future(main_chain(smc))

asyncio.ensure_future(collator(Network, 0, address, smc))
for i in range(1):
    asyncio.ensure_future(proposer(Network, 0, i, smc))
loop.run_forever()
