"""
Important: Do not modify this file!
"""
import math
import random

from pandapower import runpp, pandapowerNet
import pandapower as pp
import simbench

import logging

log = logging.getLogger(__name__)

num_switches = 0

def reset_switch_count():
    global num_switches
    num_switches = 0

def create_switchable_line_between(net, from_bus, to_bus):
    line_id = pp.create_line(net, from_bus, to_bus, 1, "NAYY 4x150SE 0.6/1kV")
    return pp.create_switch(net, to_bus, line_id, "l", closed=False, name="Reserve Line Switch")

def create_test_network():
    net = simbench.get_simbench_net("1-LV-semiurb4--2-sw")

    net.line.loc[int(random.random()*len(net.line)), "in_service"] = False
    
    create_switchable_line_between(net, 11, 12)
    create_switchable_line_between(net, 23, 1)
    create_switchable_line_between(net, 26, 33)
    create_switchable_line_between(net, 17, 22)
    create_switchable_line_between(net, 4, 7)
    create_switchable_line_between(net, 21, 5)
    create_switchable_line_between(net, 34, 9)
    create_switchable_line_between(net, 15, 30)
    create_switchable_line_between(net, 10, 37)
    
    return net

def evaluate_result_obtained(row):
    return row["vm_pu"] is not None and not math.isnan(row["vm_pu"])

def evaluate(net, log_result=False):
    # Running the ordinary power flow of pandapower, here most of the constraints are included
    # i.e. power balance equations, voltage and power flow equations, ...
    runpp(net)
    
    net.res_bus["connected?"] = net.res_bus.apply(evaluate_result_obtained, axis=1)
    connected = net.res_bus["connected?"].all()

    if log_result:
        log.info("The connection status (connected to the external grid by power lines) of the following buses:")
        log.info(net.res_bus[["connected?"]])
        log.info("All buses of the network are connected again! :)" if connected else "There are still unconnected areas!")
        log.info(f"You needed {num_switches} number of switches")

    return num_switches, connected


class BusMeasurement:
    def __init__(self, vm_pu_get_func) -> None:
        self.__vm_pu_get_func = vm_pu_get_func

    @property
    def connected(self):
        return math.isnan(self.__vm_pu_get_func())
    
    def __str__(self) -> str:
        return f"connected: {self.connected}"

class Switch:

    def __init__(self, get_set_switch_tuple) -> None:
        self.__get_switch, self.__set_switch  = get_set_switch_tuple

    def switch(self, new_value: bool):
        global num_switches
        num_switches += 1
        self.__set_switch(new_value)
    
    def is_switched(self):
        return self.__get_switch()


def set_value(net, index):
    def inner(new_value):
        net.switch.loc[index, "closed"] = new_value
    return inner

def get_value(net, index):
    return lambda: net.switch.loc[index, "closed"]

def to_components(net: pandapowerNet):
    active_components = []
    passive_components = []
    for index, _ in net.switch.iterrows():
        # only not closed ones are relevant here
        if not net.switch.loc[index, "closed"]:
            active_components.append(Switch((get_value(net, index), set_value(net, index))))
    for index, _ in net.bus.iterrows():
        component = BusMeasurement(lambda: net.res_bus.loc[index, "vm_pu"])
        passive_components.append(component)
    return active_components, passive_components
