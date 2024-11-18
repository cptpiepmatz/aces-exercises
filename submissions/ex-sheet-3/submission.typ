#import "../template/template.typ": *

#show: template.with(
  course: "Agent-based Control in Energy Systems", 
  authors: ("Tim Hesse", "Michael Krah").sorted(),
  group: 8,
  number: 3,
  tutor: "Rico Schrage",
  tutor-mail: "rico.schrage@uni-oldenburg.de",
  // date: datetime(day: 05, month: 11, year: 2024)
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
  The MAS provides acceptable solutions by randomly selecting colors, which means 
  solutions are also found randomly. 
  When an agent's color conflicts with another agent's, it picks a new color at random. 
  The use of the asyncio runtime ensures that color selection avoids data races, 
  maintaining proper operation.

3.
  Since the colors are chosen at random and new colors are chosen at random, the MAS has 
  the potential to eventually find all possible solutions.

4.
  The MAS terminates when a valid solution is found. 
  However, if no solution exists, it will run indefinitely. 
  The system does not guarantee convergence because conflicts are resolved by randomly 
  picking new colors. 
  This means the newly chosen color might also create a conflict, making it possible for 
  the system to revert to a worse state (further from a solution) than before.
