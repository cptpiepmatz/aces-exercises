import asyncio
import json
import logging
import types
from typing import Any

import mango
import mango.container
import mango.container.core
import matplotlib.pyplot as plt
import networkx as nx
from core import BusMeasurement, Switch, evaluate
from pandapower import pandapowerNet, topology

from solver.agents import Agent, BusAgent, SwitchAgent
from solver.ids import MessageId, SwitchId
from solver.messages import Message

ADDRESS = ("localhost", 5555)
log = logging.getLogger(__name__)


def solve(
    switches: list[Switch], bus_measurements: list[BusMeasurement], net: pandapowerNet
) -> None:
    open_network = topology.create_nxgraph(net)
    closed_network = topology.create_nxgraph(net, respect_switches=False)

    communication_topology = create_communication_topology(open_network, closed_network)
    # Draw the graph

    def layouter(network: nx.Graph) -> dict:
        return nx.nx_pydot.graphviz_layout(network)

    # pos = layouter(communication_topology)  # Layout for node positions
    # nx.draw(
    #     communication_topology,
    #     pos,
    #     with_labels=True,
    #     node_color="lightblue",
    #     edge_color="gray",
    #     node_size=500,
    #     font_size=10,
    # )
    # plt.savefig(
    #     "communication_topology.png",
    #     dpi=300,
    #     bbox_inches="tight",
    # )  # Save with high resolution
    # plt.close()

    # pos = layouter(open_network)
    # nx.draw(
    #     open_network,
    #     pos,
    #     with_labels=True,
    #     node_color="lightblue",
    #     edge_color="gray",
    #     node_size=500,
    #     font_size=10,
    # )
    # plt.savefig(
    #     "open_network.png",
    #     dpi=300,
    #     bbox_inches="tight",
    # )  # Save with high resolution
    # plt.close()

    # pos = layouter(closed_network)
    # nx.draw(
    #     closed_network,
    #     pos,
    #     with_labels=True,
    #     node_color="lightblue",
    #     edge_color="gray",
    #     node_size=500,
    #     font_size=10,
    # )
    # plt.savefig(
    #     "closed_network.png",
    #     dpi=300,
    #     bbox_inches="tight",
    # )  # Save with high resolution
    # plt.close()

    communication_topology = map_busmeasurements_and_switches_to_nodes(
        communication_topology, net, bus_measurements, switches
    )

    def node_color(node: Any, nodedata: Any) -> str:
        if node[0] == "bus" and nodedata.get("bus_measurement").connected:
            return "#4CAF50"
        elif node[0] == "bus":
            return "#E53935"
        elif node[0] == "switch":
            return "#1E88E5"
        else:
            msg = f"unknown node type: {node[0]}"
            raise Exception(msg)

    pos = layouter(communication_topology)  # Layout for node positions
    nx.draw(
        communication_topology,
        pos,
        with_labels=True,
        labels={node: node[1] for node in communication_topology.nodes.keys()},
        node_color=[
            node_color(node, nodedata)
            for node, nodedata in communication_topology.nodes.items()
        ],
        edge_color="gray",
        node_size=300,
        font_size=10,
    )
    plt.savefig(
        "agent_topology.png",
        dpi=300,
        bbox_inches="tight",
    )  # Save with high resolution
    plt.close()

    agents = create_agents(communication_topology)

    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(run_container(agents))
    asyncio.run(run_container(agents))

    # This creates a topology representing the actual physical network
    # graph = topology.create_nxgraph(net)
    # log.info(len(graph.edges))
    # log.info(len(graph.nodes))

    # This creates a topology representing the network if all switches are closed
    # graph = topology.create_nxgraph(net, respect_switches=False)
    # log.info(len(graph.edges))
    # log.info(len(graph.nodes))

    # evaluate(net)


def create_communication_topology(
    open_network: nx.Graph, closed_network: nx.Graph
) -> nx.Graph:
    communication_topology = nx.Graph()
    communication_topology.add_nodes_from(("bus", node) for node in open_network.nodes)
    communication_topology.add_edges_from(
        (("bus", u), ("bus", v), data) for u, v, data in open_network.edges(data=True)
    )

    switch_edges = closed_network.edges - open_network.edges
    for u, v, info in switch_edges:
        switch_node = ("switch", info[1])
        communication_topology.add_node(switch_node)
        communication_topology.add_edge(("bus", u), switch_node)
        communication_topology.add_edge(("bus", v), switch_node)

    return communication_topology


def map_busmeasurements_and_switches_to_nodes(
    communication_topology: nx.Graph,
    net: pandapowerNet,
    bus_measurements: list[BusMeasurement],
    switches: list[Switch],
) -> nx.Graph:
    element_to_switch_index: dict[int, int] = {}
    for index, _ in net.switch.iterrows():
        if not net.switch.loc[index, "closed"]:
            element = net.switch.loc[index, "element"]
            element_to_switch_index[element] = len(element_to_switch_index)

    bus_to_bus_index: dict[int, int] = {}
    for index, _ in net.bus.iterrows():
        bus_to_bus_index[index] = len(bus_to_bus_index)

    for node, data in communication_topology.nodes(data=True):
        if node[0] == "bus":
            bus = node[1]
            bus_index = bus_to_bus_index[bus]
            communication_topology.nodes[node]["bus_measurement"] = bus_measurements[
                bus_index
            ]
        elif node[0] == "switch":
            element = node[1]
            switch_index = element_to_switch_index[element]
            communication_topology.nodes[node]["switch"] = switches[switch_index]

    return communication_topology


def create_agents(communication_topology: nx.Graph) -> dict[str, Agent]:
    for node, data in communication_topology.nodes(data=True):
        agent_id = f"{node[0]}-{node[1]}-agent"
        communication_topology.nodes[node]["agent_id"] = agent_id
        communication_topology.nodes[node]["agent_address"] = mango.AgentAddress(
            ADDRESS, agent_id
        )

    for node in communication_topology.nodes:
        neighboring_nodes = communication_topology.neighbors(node)
        neighbors = [
            communication_topology.nodes[neighbor]["agent_address"]
            for neighbor in neighboring_nodes
        ]
        communication_topology.nodes[node]["neighbors"] = neighbors

    agents: dict[str, Agent] = {}
    for node, data in communication_topology.nodes(data=True):
        if node[0] == "bus":
            neighbors = communication_topology.nodes[node].get("neighbors")
            bus_measurement = communication_topology.nodes[node].get("bus_measurement")
            bus_agent = BusAgent(neighbors=set(neighbors), bus=bus_measurement)
            agent_id = communication_topology.nodes[node].get("agent_id")
            agents[agent_id] = bus_agent
        elif node[0] == "switch":
            neighbors = communication_topology.nodes[node].get("neighbors")
            switch = communication_topology.nodes[node].get("switch")
            switch_agent = SwitchAgent(
                neighbors=set(neighbors), switch=switch, sid=SwitchId()
            )
            agent_id = communication_topology.nodes[node].get("agent_id")
            agents[agent_id] = switch_agent

    return agents


def trace_container_messages(
    container: mango.container.core.Container,
) -> dict[MessageId, list[tuple[str, str, Message]]]:
    transfers: dict[MessageId, list[tuple[str, str, Message]]] = {}

    # proxy original send_message to get message content
    original_send_message = container.send_message

    async def proxy_send_message(
        self: mango.container.core.Container,
        content: Message,
        receiver_addr: mango.AgentAddress,
        sender_id: None | str = None,
        **kwargs,
    ) -> bool:
        nonlocal transfers

        mid = content.mid
        if mid not in transfers:
            transfers[mid] = []
        transfers[mid].append((sender_id, receiver_addr.aid, content))
        return await original_send_message(content, receiver_addr, sender_id, **kwargs)

    container.send_message = types.MethodType(proxy_send_message, container)
    return transfers


async def run_container(agents: dict[str, Agent]):
    container = mango.create_tcp_container(addr=ADDRESS, copy_internal_messages=True)
    transfers = trace_container_messages(container)

    for aid, agent in agents.items():
        container.register(agent, aid)

    async with mango.activate(container):
        async with asyncio.TaskGroup() as tg:
            for agent in agents.values():
                tg.create_task(agent.resolved.wait())

    # write traced container messages to file
    with open("transfers.toml", "w") as f:
        for mid, transfers in transfers.items():
            f.write(f"[{mid}]\n")
            f.write("transfers = [\n")
            for transfer in transfers:
                sender = json.dumps(transfer[0])
                receiver = json.dumps(transfer[1])
                message = json.dumps(repr(transfer[2]))
                f.write(f"  [{sender:>17}, {receiver:>17}, {message}],\n")
            f.write("]\n\n")
