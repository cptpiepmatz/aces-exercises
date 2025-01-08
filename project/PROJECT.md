# Mini-Project: Reconfiguration

In the reconfiguration project, your task will be to create a cooperative agent system with ``mango-agents``, which shall distributedly reconfigure a power grid after line failures. You need to detect the broken line and close the necessary switches to activate reserve lines, which reconnects disconnected parts of the grid.

We will provide a reconfiguration environment where you can test your approach. In this test environment, there will always be exactly one line failure.

*Your specific objective*:

* Reconnect **as many buses as possible**
* Minimize the **number of switching operations**

As there is no guarantee that you can reconnect any buses, detecting that the line failure can **not** be mitigated using reconfiguration is also a valid solution of the multi-agent system!

**Be aware** that you need to solve the problem fully distributedly, **every agent can only observe one bus or control one switch, and no agent is allowed to know the whole topology at any point!**. Generally, strategies like sending all information to one agent and solving the problem centrally are not allowed! The only way to share knowledge is by sending messages using the mango messaging modules. For simplicity, you can run all agents in one container.

## The Environment

The environment is provided. It is built using ``pandapower`` ([Docs](https://pandapower.readthedocs.io/en/latest/)). The environment includes:

* An AC power grid model
* An evaluation function which will 
   * update the AC power grid model such that the agents can observe the effect of their actions, and 
   * return whether the buses are connected to the main grid and how many switch actions have been used
   * raise an exception if the AC model calculation (the power flow) does not converge at all, if that happens, your solution is invalid

To simplify the usage of the environment, we provide a test instance (pandapower grid), the evaluation function implementing the two objectives above, and Objects, which provides access to the information you need.

* **Switch**: A switch ``switch: Switch`` represents a (initially open) switch in the power grid. You can read whether it is closed via ``switch.is_closed()``, to close/open the switch you can call ``switch.switch(True)``.
* **BusMeasurement**: A bus representation ``bus: BusMeasurement`` represents a bus and its relevant measurement for the given problem. Here it is mandatory that the bus can signal whether it is connected to the main grid. To check this you can use ``bus.connected``.

Look at the template for usage examples. This project also needs the topology information of the grid, the `template.py` contains some hints how you could extract them from the pandapower grid.

## Evaluation

We will evaluate your project results in a freshly set up environment and only include your agent system (``template.py`` + new .py files you might have created). 

We will evaluate your agent system on multiple test instances (other pandapower grids, which might contain different numbers of buses, other topologies, etc.).

## Grading

There are multiple requirements for passing:

1. Presentation of your project results at the final discussion (all group members must be present!)
2. Your project is adequately documented. We expect a short description of your agents and their strategies and, depending on your implementation, unique usage characteristics for your project. (-> README is sufficient)
3. Your project fulfills the project goals adequately
   * Your system works in the provided environment (~= creates a valid non-trivial solution; your system works distributedly as described in the introduction)
   * Your system has a reasonable solution strategy (~= makes logical sense and includes the available information in a sensible way)
   * Your system does not rely on the specific values of the parameters used by the provided environment  (i.e., the number of buses, the specific switches, grid topology, etc.)

To receive the grade-improving bonus, you need to hit one of the following marks:

* Your agent system is outstanding and of excellent quality (code and methodological!)
* Your system can additionally handle multi-line failures
* If you have an idea to extend the scope of the mini project, discuss this with us, and for a successful implementation, you will also receive the grade-improving bonus