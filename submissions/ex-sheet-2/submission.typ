#import "../template/template.typ": *

#show: template.with(
  course: "Agent-based Control in Energy Systems", 
  authors: ("Tim Hesse", "Michael Krah").sorted(),
  group: 8,
  number: 2,
  tutor: "Rico Schrage",
  tutor-mail: "rico.schrage@uni-oldenburg.de",
  // date: datetime(day: 05, month: 11, year: 2024)
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
With the small world topology, a total of 50 messages were sent.

== Exercise 6 
For the current setup, the `TopologyAgent` would have to distribute a topology that 
contains every agent in the same neighborhood, a fully meshed graph.
This could either be done by increasing $k$ until everything is directly connected or 
without constructing the graph in the first place and sending just the list of every agent 
address to every agent.
