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
loop.create_task(main_chain(smc))

loop.create_task(collator(Network, 0, address, smc))
loop.create_task(proposer(Network, 0, address, smc))	
loop.run_forever()
