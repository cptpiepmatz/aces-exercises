from pandapower import pandapowerNet, topology
from core import Switch, BusMeasurement, evaluate
from solver.agents import Agent, BusAgent, SwitchAgent
from solver.ids import SwitchId
import networkx as nx
import mango
import asyncio

import logging

ADDRESS = ("localhost", 5555)
log = logging.getLogger(__name__)


def solve(
    switches: list[Switch], bus_measurements: list[BusMeasurement], net: pandapowerNet
) -> None:
    open_network = topology.create_nxgraph(net)
    closed_network = topology.create_nxgraph(net, respect_switches=False)

    communication_topology = create_communication_topology(open_network, closed_network)
    communication_topology = map_busmeasurements_and_switches_to_nodes(
        communication_topology, net, bus_measurements, switches
    )
    agents = create_agents(communication_topology)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_container(agents))

    # This creates a topology representing the actual physical network
    graph = topology.create_nxgraph(net)
    log.info(len(graph.edges))
    log.info(len(graph.nodes))

    # This creates a topology representing the network if all switches are closed
    graph = topology.create_nxgraph(net, respect_switches=False)
    log.info(len(graph.edges))
    log.info(len(graph.nodes))

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

    for node, data in communication_topology.nodes(data=True):
        if node[0] == "bus":
            bus_index = node[1]
            communication_topology.nodes[node]["bus_measurement"] = bus_measurements[
                bus_index
            ]
        elif node[0] == "switch":
            element = node[1]
            switch_index = element_to_switch_index[element]
            communication_topology.nodes[node]["switch"] = switches[switch_index]

    return communication_topology


def create_agents(communication_topology: nx.Graph) -> list[Agent]:
    for i, node in enumerate(communication_topology.nodes):
        communication_topology.nodes[node]["agent_address"] = mango.AgentAddress(
            ADDRESS, f"agent{i}"
        )

    for node in communication_topology.nodes:
        neighboring_nodes = communication_topology.neighbors(node)
        neighbors = [
            communication_topology.nodes[neighbor]["agent_address"]
            for neighbor in neighboring_nodes
        ]
        communication_topology.nodes[node]["neighbors"] = neighbors

    agents = []
    for node, data in communication_topology.nodes(data=True):
        if node[0] == "bus":
            neighbors = communication_topology.nodes[node].get("neighbors")
            bus_measurement = communication_topology.nodes[node].get("bus_measurement")
            bus_agent = BusAgent(neighbors=set(neighbors), bus=bus_measurement)
            agents.append(bus_agent)
        elif node[0] == "switch":
            neighbors = communication_topology.nodes[node].get("neighbors")
            switch = communication_topology.nodes[node].get("switch")
            switch_agent = SwitchAgent(
                neighbors=set(neighbors), switch=switch, sid=SwitchId()
            )
            agents.append(switch_agent)

    return agents


async def run_container(agents: list[Agent]):
    async with mango.run_with_tcp(1, *agents):
        for agent in agents:
            await agent.resolved.wait()
