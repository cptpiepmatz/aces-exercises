#import "../template/template.typ": *

#show: template.with(
  course: "Agent-based Control in Energy Systems", 
  authors: ("Tim Hesse", "Michael Krah").sorted(),
  group: 8,
  number: 2,
  tutor: "Rico Schrage",
  tutor-mail: "rico.schrage@uni-oldenburg.de",
  date: datetime(day: 12, month: 11, year: 2024)
)

== Exercise 2
The `ResidentAgent`s store their neighbors inside a plain list by storing the transmitted 
`mango.AgentAddress`es as they are.

The `TopologyAgent` stores the entire topology in a `networkx.Graph`, making extracting 
certain neighbors easily accessible.

== Exercise 4
For every `ResidentAgent`, the set of received IDs is the same as the neighborhood IDs.
This happens because we send the ID of the `ResidentAgent` to all neighbors.
So for every agent, it receives a message from every of its neighbors.

== Exercise 5
Using only the ring topology, a total of 30 messages (including the initial topology 
distribution messages) were sent.
With the small world topology ($k = 2, p = 0$), a total of 50 messages were sent.

== Exercise 6 
For the current setup, the `TopologyAgent` would have to distribute a topology that 
contains every agent in the same neighborhood, a fully meshed graph.
This could either be done by increasing $k$ until everything is directly connected, 
setting $p$ to $1$ or without constructing the graph in the first place and sending just 
the list of every agent address to every agent.

== Exercise 7

=== Observability
The `QueenAgent` knows the entire board (fully) including where every other agent is placed.

=== Multi Agent System (MAS)
The system is a multi agent system, since the problem requires at least two queens to not 
be totally trivially.

=== Competitive vs. Cooperative
The task is cooperative as every agent works on the same, overarching goal.

=== Deterministic vs. Stochastic vs. Non-deterministic
The task environment is deterministic, we have some input (where each queen is placed) and 
can deterministically derive whether we found a solution.

=== Episodical vs. Sequential
The state of the board doesn't depend on the previous board states for that problem.
Therefore the environment state is episodical.

=== Static vs. Dynamic
During deliberation (i.e. when the `QueenAgent` decides on its Move) the board doesn't 
change, therefore the task environment is static.

=== Discrete vs. Continous
The positions of the queens is discretely sectioned in columns and rows.
Also we only check the placed states of every piece and do not consider the moving itself.
Every percept is a single, stable state in which every piece can be assigned to a discrete 
position (e.g., Queen 2 => E5).
This makes the environment discrete.

=== Known vs. Unknown
The environment is totally known and every consequence of every action is known as we 
know all the rules of the problem.

== Exercise 8
The problem could be solved using backtracking. In this case, we would place the first
`QueenAgent` in the first column, the second agent in the second column such that it 
cannot be taken by the first agent, and so on. When a `QueenAgent` cannot be placed in a
row where it is not taken by another agent, the position of the previous one is adjusted 
and so on.

For an agent-based solution, we could first place the agents randomly on the board.
Then, every agent detects which other agents would be taken by itself.
If no agent can be taken, stay.
Otherwise, move to a position where others do not take the agent.
If no such position could be found, demand that another conflicting agent moves.
That agent tries to resolve the issue in the same way the first agent tried to find an open 
position, and if that is not possible, it also sends the request further.
If no agent can currently move into an open state, a random agent moves to a random 
location and starts the process again.
This exchange happens until a solution is found.

This solution could have an infinite runtime, as we only terminate when a solution is 
found.

== Exercise 9
The built-in topology API directly provides a way to define the topology via a graph.
This can be either done by adding edges or using a `networkx.Graph`.
Using that API, avoids the use of containers (at least from the outside) and only models 
the overlay topology while completely ignoring the possible hardware abstraction that 
containers provide.
This is useful in situations, where modeling agents on different hardware is not necessary 
and only topologies needs to be evaluated.
