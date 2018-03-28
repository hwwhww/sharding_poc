# https://gist.github.com/pipermerriam/8a71d6455c79a5e23d8ff63208b31e8d
import asyncio
import logging
import sys
import random

from distribution import (
    normal_distribution,
    transform,
)


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger('sharding_poc.network')


LATENCY = 1


class Network:

    nodes = None  # all nodes
    peers = None  # peers[address] = list of peers

    def __init__(self):
        self.nodes = []
        self.peers = {}

    def login(self, node):
        self.nodes.append(node)

    def clear_peers(self):
        self.peers = {}
        for node in self.nodes:
            node.outputs = {}

    def remove_peer(self, node):
        if node in self.nodes:
            self.nodes.remove(node)
        for peer_node in self.nodes:
            if node.address in peer_node.outputs:
                peer_node.outputs.pop(node.address)


    def add_peers(self, node, message_queue=None, num_peers=4):
        self.peers[node.address] = []
        logger.info('--- add_peers for {}'.format(node.address))
        while len(self.peers[node.address]) < num_peers:
            candidate = random.choice(self.nodes)
            if candidate.address not in self.peers:
                self.peers[candidate.address] = []

            if (
                node.address == candidate.address or
                candidate.address in self.peers[node.address]
            ):
                pass
            else:
                logger.info('candidate: {}'.format(candidate.address))

                self.peers[node.address].append(candidate.address)
                if message_queue is None:
                    message_queue = asyncio.Queue()
                node.outputs[candidate.address] = candidate.message_queue
                # self.peers[candidate.address].append(node.address)
                candidate.outputs[node.address] = message_queue


    def generate_peers(self, num_peers=4):
        self.clear_peers()
        for node in self.nodes:
            self.add_peers(node, num_peers=num_peers)

    def find_node(self, address):
        for node in self.nodes:
            if node.address == address:
                return node
        return None

class Node:
    address = None
    network = None
    input = None
    message_queues = None
    outputs = None
    latency_distribution = transform(
        normal_distribution(LATENCY, (LATENCY * 2) // 5), lambda x: max(x, 0)
    )

    def __init__(self, network, address, message_queue=None):
        self.network = network
        self.address = address
        self.input = asyncio.Queue()
        self.outputs = {}  # address: Queue
        if message_queue is None:
            self.message_queue = asyncio.Queue()
        else:
            self.message_queue = message_queue


async def broadcast(network, address):
    while True:
        # logger.info('broadcast waiting for message of address {}'.format(address))
        node = network.find_node(address)
        if node.address == address:
            message = await node.input.get()
            # logger.info('broadcast got message: {0}'.format(message))
            # logger.info('broadcasting to {0} consumers'.format(
            #     len(node.outputs))
            # )
            for key, value in node.outputs.items():
                await value.put(message)


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
