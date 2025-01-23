"""
Modify this file! For evaluating We will include this file and other !new! files you may provide!
"""

from pandapower import pandapowerNet
from core import Switch, BusMeasurement
import solver


# Optional, if you want to evaluate on more self-defined networks
def create_additional_networks() -> list[pandapowerNet]:
    return []


def solve(
    switches: list[Switch], bus_measurements: list[BusMeasurement], net: pandapowerNet
):
    solver.solve(switches, bus_measurements, net)
