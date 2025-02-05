"""
Important: Do not modify this file!
"""

from pandapower import runpp
from core import create_test_network, to_components, evaluate, reset_switch_count
from template import solve, create_additional_networks

import logging

logging.basicConfig(encoding='utf-8', level=logging.INFO)
log = logging.getLogger(__name__)

def evaluate_solution(net):
    runpp(net)
    generators, bus_measurements = to_components(net)
    solve(generators, bus_measurements, net)
    evaluate(net, log_result=True)
    reset_switch_count()

if __name__ == "__main__":
    # Additional network evaluation
    log.info("Starting additional network evaluation!")
    for net in create_additional_networks():
       evaluate_solution(net)

    # The default network evaluation
    log.info("Starting default network evaluation!")
    net = create_test_network()
    evaluate_solution(net)
