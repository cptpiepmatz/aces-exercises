import numpy as np
from scipy.optimize import minimize


def comfort(c, k):
    s = 1.0 / (1.0 + np.exp(-c/k))
    return s


#  objective to maximize comfort
def objective(c):
    return -np.sum(comfort(c, k_values))


#  only positive allocations
bounds = [(0, None) for _ in range(5)]


#  sum of allocations should not exceed supply
def available_supply_constraint(c, g):
    return g - np.sum(c)


#  fairness constraint: tolerable inequality between best-off and worst-off agent
def fairness_constraint(c, beta):
    return beta - np.max(c) - np.min(c)


#  five different values for k to obtain five different comfort functions
k_values = np.linspace(0.001, 0.1, 5)

#  available supply of 10
g = 10.0

#  tolerable deviation of 5
beta = 5.0

#  start with allocating 0 to all agents
c0 = np.zeros(5)

constraints = [
    {'type': 'ineq', 'fun': available_supply_constraint, 'args': (g,)},
    {'type': 'ineq', 'fun': fairness_constraint, 'args': (beta,)}
]

result = minimize(objective, c0, method='SLSQP', bounds=bounds, constraints=constraints)

if result.success:
    print(result.message)
    print("Optimal allocation:", result.x)
else:
    print(result.message)
    print("No optimal allocation available.")