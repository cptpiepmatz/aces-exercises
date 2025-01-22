from pandapower import pandapowerNet, topology
from core import Switch, BusMeasurement, evaluate
from solver.agents import BusAgent, SwitchAgent
from solver.ids import SwitchId

import logging

log = logging.getLogger(__name__)

def solve(
    switches: list[Switch], 
    bus_measurements: list[BusMeasurement], 
    net: pandapowerNet
) -> None:
    bus_agents = [BusAgent(neighbors=set(), bus=bus) for bus in bus_measurements]
    switch_agents = [SwitchAgent(neighbors=set(), switch=switch, sid=SwitchId()) for switch in switches]

    # TODO: connect everything

    open_network = topology.create_nxgraph(net)
    closed_network = topology.create_nxgraph(net, respect_switches=False)

    # This creates a topology representing the actual physical network
    graph = topology.create_nxgraph(net)
    log.info(len(graph.edges))
    log.info(len(graph.nodes))

    # This creates a topology representing the network if all switches are closed
    graph = topology.create_nxgraph(net, respect_switches=False)
    log.info(len(graph.edges))
    log.info(len(graph.nodes))

    
    # evaluate(net)
