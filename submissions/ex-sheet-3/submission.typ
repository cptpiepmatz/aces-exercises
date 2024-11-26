#import "../template/template.typ": *

#show: template.with(
  course: "Agent-based Control in Energy Systems", 
  authors: ("Tim Hesse", "Michael Krah").sorted(),
  group: 8,
  number: 3,
  tutor: "Rico Schrage",
  tutor-mail: "rico.schrage@uni-oldenburg.de",
  date: datetime(day: 19, month: 11, year: 2024)
)

== Exercise 1

=== Usage
The script requires at least one argument: the port number where the container should run.
This is the first and only positional argument. 
The script can be run in either passive mode (without a `TopologyAgent`) or active mode, 
which is controlled by the `--topology` (`-t`) flag.

You can choose the topology mode using the `--mode` (`-m`) flag. 
By default, the script runs in fully meshed mode (`--mode fully`). 
Alternatively, you can select a star (octopus) topology with `--mode star`, which only 
fully meshes the first agent in each container and chains the other agents to it, creating 
a star shape.

The number of agents each container should spin up can be set using the `--agents` (`-a`) 
flag.

To connect to other processes, use the `--container` (`-c`) flag, specifying the port of 
the other process and the number of agents it runs. 
Use `--help` to display detailed usage instructions. 
The script assumes all processes run on the same host, so only ports need to be specified, 
not full addresses.

#box[
  *Example commands:*
  1. Run the first process:
    ```
    python ex1.py 5001 -c 5000:5
    ```

  2. Run the second process:
    ```
    python ex1.py 5000 -c 5001:5 -t -m star
    ```
]

The first command starts a passive process on port 5001, expecting another container with 
5 agents on port 5000. 
The second command starts an active container on port 5000 with a `TopologyAgent` that 
creates a star topology, expecting 5 agents on port 5001. 
The active container manages its agents and coordinates with the other process's agents 
to distribute the topology.

=== Behavior
Like in the previous exercise, this setup includes `ResidentAgent`s that know their 
neighbors and a `TopologyAgent` responsible for creating and distributing the topology.

Cross-process container behavior is simulated by constructing all known containers based 
on the provided `--container` flags, using a consistent scheme for determining agent AIDs. 
Only the local container is activated, and other processes are expected to wait for 
instructions from the container running the `TopologyAgent`.

#pagebreak()

== Exercise 2

2.
  The MAS provides acceptable solutions by backtracking.
  The solution found depends upon the initial instance, which is randomly generated and an invalid solution.
  The first agent changes its color depending on the colors of the other agents and, then,
  communicates the new system state to its neighbors. The neighbors change their respective
  colors accordingly until a solution is found.

3.
  Yes, the initial state is random. For all initial random states, the MAS will find a valid
  solution. Since the initial state is random, we are able to find all possible solutions.

4.
  The MAS terminates when a valid solution is found. 
  The search for a solution converges, since a version of domain pruning is used.
  When changing its color state, an agent checks for available colors, i.e., those
  not used by other agents. It, then, picks one from the colors still available.
