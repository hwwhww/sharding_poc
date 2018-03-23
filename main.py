import asyncio

from network import (
    Network,
    broadcast,
    consumer,
    producer,
)


loop = asyncio.get_event_loop()

asyncio.ensure_future(broadcast(Network))
for i in range(2):
    asyncio.ensure_future(consumer(Network, i))
for i in range(3):
    asyncio.ensure_future(producer(Network, i))
loop.run_forever()
