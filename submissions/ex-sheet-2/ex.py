import asyncio
from asyncio import TaskGroup
from dataclasses import dataclass

import mango
from mango import Agent, AgentAddress
from networkx import Graph

MESSAGE_COUNTER: int = 0


@dataclass
class NeighborhoodMessage:
    neighbors: list[AgentAddress]


@dataclass
class GreetingsMessage:
    my_id: AgentAddress


class ResidentAgent(Agent):
    neighbors: None | list[AgentAddress]
    received_ids: list[AgentAddress]

    def __init__(self):
        super().__init__()
        self.neighbors = None
        self.received_ids = []

    def handle_message(self, content, meta):
        if isinstance(content, NeighborhoodMessage):
            self.neighbors = content.neighbors
            self.schedule_instant_task(self.send_neighbors(GreetingsMessage(self.addr)))
        if isinstance(content, GreetingsMessage):
            self.received_ids.append(content.my_id)

    async def send_neighbors(self, content):
        assert self.neighbors is not None, "neighbors are unknown"
        async with TaskGroup() as tg:
            for neighbor in self.neighbors:
                global MESSAGE_COUNTER
                MESSAGE_COUNTER += 1
                tg.create_task(self.send_message(content, neighbor))


class TopologyAgent(Agent):
    def __init__(self, addrs: list[AgentAddress]):
        super().__init__()
        self.addrs = {a.aid: a for a in addrs}
        # self.topology = self.construct_ring_topology(addrs)
        self.topology = self.construct_small_world_topology(addrs, 2)

    @staticmethod
    def construct_ring_topology(addrs: list[AgentAddress]) -> Graph:
        graph = Graph()
        for a, b in zip(addrs, addrs[1:]):
            graph.add_edge(a.aid, b.aid)
        graph.add_edge(addrs[-1].aid, addrs[0].aid)  # wrap around
        return graph

    @staticmethod
    def construct_small_world_topology(addrs: list[AgentAddress], k: int) -> Graph:
        graph = TopologyAgent.construct_ring_topology(addrs)

        for _ in range(1, k):
            view = graph.copy()
            for n in view.nodes():
                for neighbor in view.neighbors(n):
                    for neighbors_neighbor in view.neighbors(neighbor):
                        if neighbors_neighbor != n:
                            graph.add_edge(n, neighbors_neighbor)

        return graph

    async def distribute_topology(self):
        async with TaskGroup() as tg:
            for i, neighbors in self.topology.adjacency():
                aid = self.addrs[i]
                neighbors = [self.addrs[n] for n in neighbors.keys()]
                content = NeighborhoodMessage(neighbors)
                global MESSAGE_COUNTER
                MESSAGE_COUNTER += 1
                tg.create_task(self.send_message(content, aid))


async def main():
    container = mango.create_tcp_container(addr="localhost:5555")
    agents = [container.register(ResidentAgent(), f"resident-{i}") for i in range(10)]
    addrs = [a.addr for a in agents]
    topology_agent = container.register(TopologyAgent(addrs), "topology")

    async with mango.activate(container) as container:
        await topology_agent.distribute_topology()
        await asyncio.sleep(2)
        for a in agents:
            aid = a.addr.aid
            received_ids = sorted([rid.aid for rid in a.received_ids])
            neighborhood = sorted([n.aid for n in a.neighbors])
            print(
                f"{aid=}", f"{received_ids=}", f"{neighborhood=}", sep="\n", end="\n\n"
            )

        global MESSAGE_COUNTER
        print("Sent Messages:", MESSAGE_COUNTER)


asyncio.run(main())
