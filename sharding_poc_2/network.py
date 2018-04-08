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
    peers = None  # peers[node_id] = list of peers

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
            if node.node_id in peer_node.outputs:
                peer_node.outputs.pop(node.node_id)

    def add_peers(self, node, message_queue=None, num_peers=4):
        self.peers[node.node_id] = []
        while len(self.peers[node.node_id]) < num_peers:
            candidate = random.choice(self.nodes)
            if candidate.node_id not in self.peers:
                self.peers[candidate.node_id] = []

            if (
                node.node_id == candidate.node_id or
                candidate.node_id in self.peers[node.node_id]
            ):
                pass
            elif (
                node.node_id.startswith('collator')
                and candidate.node_id.startswith('collator')
            ):
                pass
            else:
                self.peers[node.node_id].append(candidate.node_id)
                if message_queue is not None:
                    node.message_queue = message_queue
                node.outputs[candidate.node_id] = candidate.message_queue
                candidate.outputs[node.node_id] = node.message_queue

    def generate_peers(self, num_peers=4):
        self.clear_peers()
        for node in self.nodes:
            self.add_peers(node, num_peers=num_peers)

    def find_node(self, node_id):
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        logger.info('self.nodes: {}'.format([node.node_id for node in self.nodes]))
        raise ValueError(
            'the node_id {} is not is the nodes list'.format(node_id)
        )

class Node:
    node_id = None
    network = None
    message_queues = None
    message_logs = None
    input = None
    outputs = None
    latency_distribution = transform(
        normal_distribution(LATENCY, (LATENCY * 2) // 5), lambda x: max(x, 0)
    )

    def __init__(self, network, node_id, message_queue=None):
        self.network = network
        self.node_id = node_id
        self.input = asyncio.Queue()
        self.outputs = {}  # node_id -> Queue
        if message_queue is None:
            self.message_queue = asyncio.Queue()
        else:
            self.message_queue = message_queue
        self.message_logs = {}   # hash -> message

        if self not in network.nodes:
            network.login(self)


async def broadcast(network, node_id):
    while True:
        node = network.find_node(node_id)
        if node.node_id == node_id:
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
        logger.info('consumer {0} got message {1}'.format(num, message))


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
