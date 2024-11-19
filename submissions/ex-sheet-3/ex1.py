import argparse
import asyncio
from asyncio import Future, TaskGroup
from enum import Enum
from itertools import chain

import mango
from mango import Agent, AgentAddress
from networkx import Graph


class NeighborhoodMode(Enum):
    FULLY = "fully"
    STAR = "star"


class FiniteAgent(Agent):
    done: Future

    def __init__(self):
        super().__init__()
        self.done = Future()


class ResidentAgent(FiniteAgent):
    neighbors: list[AgentAddress]

    def __init__(self):
        super().__init__()
        self.neighbors = list()

    def handle_message(self, content, meta):
        if isinstance(content, list) and all(
            isinstance(item, AgentAddress) for item in content
        ):
            self.neighbors = content
            self.done.set_result(None)


class TopologyAgent(Agent):
    topology: Graph
    addrs: dict[str, AgentAddress]

    def __init__(self, mode: NeighborhoodMode, agents: dict[int, list[AgentAddress]]):
        super().__init__()
        self.addrs = {
            agent.aid: agent for agents in agents.values() for agent in agents
        }

        match mode:
            case NeighborhoodMode.FULLY:
                self.topology = TopologyAgent._fully_meshed_topology(agents)
            case NeighborhoodMode.STAR:
                self.topology = TopologyAgent._star_topology(agents)

    @staticmethod
    def _fully_meshed_topology(agents: dict[int, list[AgentAddress]]) -> Graph:
        graph = Graph()
        all_agents = list(chain.from_iterable(agents.values()))
        for a in all_agents:
            for b in all_agents:
                if a != b:
                    graph.add_edge(a.aid, b.aid)
        return graph

    @staticmethod
    def _star_topology(agents: dict[int, list[AgentAddress]]) -> Graph:
        graph = Graph()

        # the center is fully meshed
        center_agents = [a[0] for a in agents.values()]
        for a in center_agents:
            for b in center_agents:
                if a != b:
                    graph.add_edge(a.aid, b.aid)

        # the outer agents are just attached to their previous on forming a star/octopus
        for agent_list in agents.values():
            for a, b in zip(agent_list, agent_list[1:]):
                graph.add_edge(a.aid, b.aid)

        return graph

    async def distribute_topology(self):
        async with TaskGroup() as tg:
            for i, neighbors in self.topology.adjacency():
                aid = self.addrs[i]
                neighbors = [self.addrs[n] for n in neighbors.keys()]
                tg.create_task(self.send_message(neighbors, aid))


async def main(
    main_port: int,
    containers: list[tuple[int, int]],  # list of [port, agent_count]
    agent_count: int,
    mode: NeighborhoodMode,
    topology: bool,  # whether we should construct a topology agent
):
    # model other containers to acquire necessary agent addresses
    agents: dict[int, list[Agent]] = {}
    for port, n in containers:
        container = mango.create_tcp_container(("localhost", port))
        a: list[Agent] = []
        for i in range(n):
            aid = f"agent-{port}-{i}"
            a.append(container.register(ResidentAgent(), aid))
        agents[port] = a

    # create own container with same naming scheme
    my_container = mango.create_tcp_container(("localhost", main_port))
    local_agents: list[ResidentAgent] = []
    for i in range(agent_count):
        aid = f"agent-{main_port}-{i}"
        local_agents.append(my_container.register(ResidentAgent(), aid))
    agents[main_port] = local_agents

    topology_agent: TopologyAgent | None = None
    if topology:
        addrs = {
            key: [agent.addr for agent in agent_list]
            for key, agent_list in agents.items()
        }
        topology_agent = my_container.register(TopologyAgent(mode, addrs))

    async with mango.activate(my_container):
        print("Container ready.")

        if topology_agent is not None:
            await topology_agent.distribute_topology()

        for a in local_agents:
            await a.done
            neighborhood = [n.aid for n in a.neighbors]
            print(f"Neighborhood of {a.addr.aid}: {neighborhood}")


def parse_other_container(input):
    try:
        port, count = map(int, input.split(":"))
        return port, count
    except ValueError:
        raise argparse.ArgumentTypeError(
            "Expected format 'port:agent_count' (e.g., 5001:5)"
        )


def args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "main_port",
        type=int,
        help="The main port on which the container is exposed",
    )
    parser.add_argument(
        "-c",
        "--containers",
        default=[],
        type=parse_other_container,
        action="append",
        help="Additional container port with expected agent counts (format 'port:agent_count', can be repeated)",
    )
    parser.add_argument(
        "-a",
        "--agents",
        type=int,
        default=5,
        help="Agent count (default is 5)",
    )
    parser.add_argument(
        "-m",
        "--mode",
        default="fully",
        choices=["fully", "star"],
        help="Mode, either 'fully' or 'star'",
    )
    parser.add_argument(
        "-t", "--topology", action="store_true", help="Create a topology agent"
    )

    return parser.parse_args()


args = args()
asyncio.run(
    main(
        args.main_port,
        args.containers,
        args.agents,
        NeighborhoodMode(args.mode),
        args.topology,
    )
)
