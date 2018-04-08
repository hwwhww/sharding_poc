from collections import (
    defaultdict,
)
import bisect

import networkx as nx

import matplotlib as mpl
mpl.use('PS')

import matplotlib.pyplot as plt

from cytoolz import (
    first,
)


def create_shard_graph(shard):
    graph = nx.DiGraph()

    graph.graph["shard"] = shard

    root = shard.headers_by_number[0][0].hash
    graph.graph["root"] = root

    # add nodes
    headers = list(shard.headers_by_hash.values())
    graph.add_nodes_from([(
        header.hash,
        {
            "number": header.number,
            "period": header.period
        }
    ) for header in headers])

    # add edges from child to parent
    for header in shard.headers_by_hash.values():
        if header.hash != graph.graph["root"]:
            graph.add_edge(header.hash, header.parent_hash)

    # mark branches so we can draw them separately
    mark_branches(graph)

    return graph


def ancestors(graph, node):
    while node:
        yield node

        parents = [edge[1] for edge in graph.out_edges(node)]
        assert len(parents) <= 1

        if not parents:
            break
        else:
            node = parents[0]


def mark_branches(graph):
    shard = graph.graph['shard']
    processed_nodes = set()

    branch_ranges = []  # [(branch start period, branch end period), ...]

    for header in shard.get_candidate_head_iterator():
        if header.hash in processed_nodes:
            continue

        attrs = graph.node[header.hash]
        current_branch_end = attrs["period"]

        for node in ancestors(graph, header.hash):
            if node in processed_nodes:
                break

            attrs = graph.node[node]

            # number of branches with higher precedence that run concurrently
            concurrent_branch_index = 0
            for other_branch_start, other_branch_end in branch_ranges:
                if other_branch_start <= attrs["period"] <= other_branch_end:
                    concurrent_branch_index += 1

            attrs["concurrent_branch_index"] = concurrent_branch_index

            processed_nodes.add(node)

        current_branch_start = attrs["period"]
        branch_ranges.append((current_branch_start, current_branch_end))


def plot_shard(shard):
    fig, ax = plt.subplots(1, figsize=(20, 10))

    graph = create_shard_graph(shard)

    positions = {}
    labels = {}
    for node in graph:
        attrs = graph.nodes[node]

        x_pos = attrs["period"]
        y_pos = -attrs["concurrent_branch_index"]
        positions[node] = (x_pos, y_pos)

        labels[node] = "#{}".format(attrs["number"])

    nx.draw_networkx(
        graph,
        node_size=1000,
        node_color="#ADD8E6",
        node_shape="s",
        arrows=False,
        pos=positions,
        labels=labels,
        ax=ax
    )

    ax.get_yaxis().set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.set_xlabel("Period")

    plt.savefig("test.png")
