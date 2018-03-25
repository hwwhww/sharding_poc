# https://gist.github.com/pipermerriam/8a71d6455c79a5e23d8ff63208b31e8d
import asyncio
import logging
import sys

from distribution import (
    normal_distribution,
    transform,
)


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger('sharding_poc.network')


LATENCY = 1


class Network:
    input = asyncio.Queue()
    outputs = []
    latency_distribution = transform(
        normal_distribution(LATENCY, (LATENCY * 2) // 5), lambda x: max(x, 0)
    )


async def broadcast(network):
    while True:
        # logger.info('broadcast waiting for message')
        message = await network.input.get()
        # logger.info('broadcast got message: {0}'.format(message))
        # logger.info('broadcasting to {0} consumers'.format(
        #     len(network.outputs))
        # )
        for out in network.outputs:
            await out.put(message)


async def consumer(network, num):
    """
    A consumer coroutine for testing
    """
    my_queue = asyncio.Queue()
    network.outputs.append(my_queue)
    while True:
        message = await my_queue.get()
        latency = network.latency_distribution()
        await asyncio.sleep(latency)
        # logger.info('consumer {0} got message {1}'.format(num, message))


async def producer(network, num):
    """
    A producer coroutine for testing
    """
    asyncio.sleep(1)
    for i in range(10):
        # logger.info('producer {0} producing message {1}'.format(num, i))
        await network.input.put('message {0} from {1}'.format(i, num))
        latency = network.latency_distribution()
        await asyncio.sleep(latency)
