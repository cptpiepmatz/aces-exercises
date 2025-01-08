"""
Modify this file! For evaluating We will include this file and other !new! files you may provide!
"""
from pandapower import pandapowerNet, topology
from core import Switch, BusMeasurement, evaluate

import logging

log = logging.getLogger(__name__)

# Optional, if you want to evaluate on more self-defined networks
def create_additional_networks() -> list[pandapowerNet]:
    return []

def solve(switches: list[Switch], bus_measurements: list[BusMeasurement], net: pandapowerNet):
    """
    !Your code shall be in this function! (do not modify the signature!)

    To get feedback for your solution call `evaluate(net)`.
    """
    # The following only demonstrates the usage and can safely be deleted

    # Hint: This mini project need topology information to use the correct switch, pandapower networks can be converted to
    # networkx graphs

    # Note that the information in this topologies need to be distributed to the agents
    # such that a single agent only knows its neighbor components

    # This creates a topology representing the actual physical network
    graph = topology.create_nxgraph(net)
    log.info(graph.edges)
    log.info(graph.nodes)

    # This creates a topology representing the network if all switches are closed
    graph = topology.create_nxgraph(net, respect_switches=False)
    log.info(graph.edges)
    log.info(graph.nodes)

    # Switches can be closed and the state can be read
    log.info(switches[0].is_switched())
    switches[0].switch(True)
    log.info(switches[0].is_switched())
    switches[0].switch(False)

    # The bus measurement object checks whether the bus is still connected (if vm_pu is not NaN)
    log.info(bus_measurements[0].connected)

    # This will calculate new network results using the current configuration.
    evaluate(net)
