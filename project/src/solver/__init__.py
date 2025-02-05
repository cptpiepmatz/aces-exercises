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
    switches: list[Switch], 
    bus_measurements: list[BusMeasurement], 
    net: pandapowerNet,
) -> None:
    """
    Solve the line failure by creating a communication topology, creating agents and
    running the multi-agent system.
    """
    open_network = topology.create_nxgraph(net)
    closed_network = topology.create_nxgraph(net, respect_switches=False)

    communication_topology = create_communication_topology(open_network, closed_network)
    communication_topology = map_busmeasurements_and_switches_to_nodes(
        communication_topology,
        net,
        bus_measurements,
        switches,
    )

    draw_graph(communication_topology)

    agents = create_agents(communication_topology)
    asyncio.run(run_container(agents))


def create_communication_topology(
    open_network: nx.Graph, closed_network: nx.Graph
) -> nx.Graph:
    """
    Creates a communication topology based on the network with open and closed switches.

    For every edge present in the `closed_network` that is not present in the 
    `open_network`, a node is added to the communication topology. 
    Edges are added between this node and the nodes connected by the edge in the 
    `closed_network`. 
    All other edges and nodes are taken from the `open_network`.

    :param open_network: network without switchable lines
    :param closed_network: network with switchable lines
    :return: communication topology graph
    """

    # create empty graph and add nodes and edges from open network
    communication_topology = nx.Graph()
    communication_topology.add_nodes_from(("bus", node) for node in open_network.nodes)
    communication_topology.add_edges_from(
        (("bus", u), ("bus", v), data) for u, v, data in open_network.edges(data=True)
    )

    # edges which are present in the closed, but not in the open network are switch edges
    switch_edges = closed_network.edges - open_network.edges
    # for each switch edge, add a node to the communication topology and connect it to
    # the buses connected by the switchable line
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
    """
    BusMeasurements and Switches are associated with the correct node in the communication
    topology.
    """

    # iterate over net.switch to associate each switch with each index in the list of 
    # switches
    element_to_switch_index: dict[int, int] = {}
    for index, _ in net.switch.iterrows():
        if not net.switch.loc[index, "closed"]:
            # element is part of a node's name in the graph created by 
            # topology.create_nxgraph(net, respect_switches=False)
            element = net.switch.loc[index, "element"]
            element_to_switch_index[element] = len(element_to_switch_index)

    # iterate over net.bus to associate each bus with each index in the list of 
    # BusMeasurements
    bus_to_bus_index: dict[int, int] = {}
    for index, _ in net.bus.iterrows():
        bus_to_bus_index[index] = len(bus_to_bus_index)

    # use the data dictionary associated with each node to store the correct 
    # BusMeasurement or the correct Switch
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
    """
    Creates the agents of the multi-agent system, with there being one agent per
    node in the communication topology.

    :return: dictionary with agent_ids serving as keys and Agents as values
    """

    # add agent_id and agent_address to the data dictionary associated with each node
    for node, data in communication_topology.nodes(data=True):
        agent_id = f"{node[0]}-{node[1]}-agent"
        communication_topology.nodes[node]["agent_id"] = agent_id
        communication_topology.nodes[node]["agent_address"] = mango.AgentAddress(
            ADDRESS, agent_id
        )

    # add neighbors, i.e., a list of neighboring AgentAddresses to the data dictionary
    # of each node
    for node in communication_topology.nodes:
        neighboring_nodes = communication_topology.neighbors(node)
        neighbors = [
            communication_topology.nodes[neighbor]["agent_address"]
            for neighbor in neighboring_nodes
        ]
        communication_topology.nodes[node]["neighbors"] = neighbors

    # create all agents by using the data dictionaries associated with each node
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
    """
    Apply a proxy function to the `send_message` method of a Mango `Container` to trace 
    container messages.

    This creates a proxy function which will insert the message to be sent in a 
    dictionary in order to read out a full tracing of all messages sent in the 
    container.
    The proxy function than normally calls the original `send_message`.

    :return: dictionary mapping message IDs to a list of tuples containing the sender, receiver and message.
    """

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
    """
    Run the multi-agent system.
    :param agents: dictionary of the system's agents
    """
    container = mango.create_tcp_container(addr=ADDRESS, copy_internal_messages=True)
    transfers = trace_container_messages(container)

    for aid, agent in agents.items():
        container.register(agent, aid)

    async with mango.activate(container):
        async with asyncio.TaskGroup() as tg:
            for agent in agents.values():
                # wait until all agents have been re-connected to the grid
                # (or have established that there is no solution)
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


def draw_graph(topology: nx.Graph):
    def node_color(node: Any, nodedata: Any) -> str:
        """
        Select a color for every node.

        - Connected busses: green
        - Disconnected busses: red
        - Switches: blue

        Raises an exception if the graph contained a node of unknown type.
        """
        if node[0] == "bus" and nodedata.get("bus_measurement").connected:
            return "#4CAF50"
        elif node[0] == "bus":
            return "#E53935"
        elif node[0] == "switch":
            return "#1E88E5"
        else:
            msg = f"unknown node type: {node[0]}"
            raise Exception(msg)

    pos = nx.nx_pydot.graphviz_layout(topology)
    nx.draw(
        topology,
        pos,
        with_labels=True,
        labels={node: node[1] for node in topology.nodes.keys()},
        node_color=[
            node_color(node, nodedata) for node, nodedata in topology.nodes.items()
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
