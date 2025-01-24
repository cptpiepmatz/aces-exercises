"""
Modify this file! For evaluating We will include this file and other !new! files you may provide!
"""
import pandapower as pp
from pandapower import pandapowerNet
from core import Switch, BusMeasurement, create_switchable_line_between
import solver


# Optional, if you want to evaluate on more self-defined networks
def create_additional_networks() -> list[pandapowerNet]:
    net = create_simple_network()
    return [net]

def create_simple_network() -> pandapowerNet:
    # modified based on pandapower tutorial
    # create empty net
    net = pp.create_empty_network()

    # create buses
    bus0 = pp.create_bus(net, vn_kv=20., name="Bus 0")
    bus1 = pp.create_bus(net, vn_kv=0.4, name="Bus 1")
    bus2 = pp.create_bus(net, vn_kv=0.4, name="Bus 2")
    bus3 = pp.create_bus(net, vn_kv=0.4, name="Bus 3")
    bus4 = pp.create_bus(net, vn_kv=0.4, name="Bus 4")
    bus5 = pp.create_bus(net, vn_kv=0.4, name="Bus 5")

    # create bus elements
    pp.create_ext_grid(net, bus=bus0, vm_pu=1.02, name="Grid Connection")
    pp.create_load(net, bus=bus2, p_mw=0.100, q_mvar=0.05, name="Load 1")
    pp.create_load(net, bus=bus4, p_mw=0.050, q_mvar=0.02, name="Load 2")

    # create branch elements
    trafo = pp.create_transformer(net, hv_bus=bus0, lv_bus=bus1,
                                  std_type="0.4 MVA 20/0.4 kV", name="Trafo")
    line = pp.create_line(net, from_bus=bus1, to_bus=bus2, length_km=0.1,
                          std_type="NAYY 4x50 SE", name="Line 1", in_service=True)
    line2 = pp.create_line(net, from_bus=bus2, to_bus=bus3, length_km=0.2,
                           std_type="NAYY 4x50 SE", name="Line 2", in_service=True)
    line3 = pp.create_line(net, from_bus=bus3, to_bus=bus4, length_km=0.15,
                           std_type="NAYY 4x50 SE", name="Line 3", in_service=True)
    line4 = pp.create_line(net, from_bus=bus0, to_bus=bus5, length_km=0.1,
                           std_type="NAYY 4x50 SE", in_service=False)
    line5 = pp.create_line(net, from_bus=4, to_bus=bus5, length_km=0.1,
                           std_type="NAYY 4x50 SE", in_service=True)
    pp.create_switch(net, bus=bus2, element=line2, et="l", closed=False,
                     name="Switch Line 1")
    pp.create_switch(net, bus=bus3, element=line3, et="l", closed=False,
                     name="Switch Line 2")
    pp.create_switch(net, bus=bus4, element=line5, et="l", closed=False,
                     name="Switch Line 3")
    return net

def solve(
    switches: list[Switch], bus_measurements: list[BusMeasurement], net: pandapowerNet
):
    solver.solve(switches, bus_measurements, net)
