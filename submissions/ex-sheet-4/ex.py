from mango import (Agent, json_serializable, create_tcp_container, JSON, activate, run_with_tcp, per_node,
                   complete_topology)
from dataclasses import dataclass
import asyncio
import random
import time

@json_serializable
@dataclass
class UpdatedColorStateMsg:
    color_state: dict

@json_serializable
@dataclass
class SolutionMsg:
    color_state: dict

@json_serializable
@dataclass
class UpdateMsg:
    no_messages: int
    start_time: int

@json_serializable
@dataclass
class SetSystemMsg:
    agents_colors: dict
    colors: list
    id: int


class ColorAgent(Agent):

    def __init__(self):
        super().__init__()

        # domain, color state, etc. are set by the Controller
        self.domain = None
        self.color_state = None
        self.id = None
        self.my_color = None
        # observer passed later on once container has been started
        self.observer = None

    def handle_message(self, content, meta):
        if isinstance(content, UpdatedColorStateMsg):
            self.color_state = content.color_state
            self.change_color()
        if isinstance(content, SetSystemMsg):
            # setting of domain, color, state, etc. upon receiving message from Controller
            self.domain = content.colors
            self.color_state = content.agents_colors
            self.id = f'ColorAgent{content.id}'
            self.my_color = content.agents_colors.get(self.id)
            # ColorAgent0 starts changing color once the system state is set by the Controller
            if self.id == 'ColorAgent0':
                self.change_color()

    def change_color(self):
        colors_in_use = set(self.color_state.values())
        available_colors = list(set(self.domain) - colors_in_use)
        if len(available_colors) == 0:
            # inform Observer about solution
            self.schedule_instant_message(content=SolutionMsg(self.color_state), receiver_addr=self.observer)
        elif len(available_colors) == 1:
            # change to available color
            self.my_color = available_colors[0]
            self.color_state[self.id] = self.my_color
            self.send_color_state_msg()
        elif len(available_colors) == 2:
            # change to random available color
            self.my_color = random.choice(available_colors)
            self.color_state[self.id] = self.my_color
            self.send_color_state_msg()

    def send_color_state_msg(self):
        # inform neighbors about new color state
        neighbors = self.neighbors()
        for neighbor in neighbors:
            self.schedule_instant_message(content=UpdatedColorStateMsg(self.color_state), receiver_addr=neighbor)
        # inform Observer about new color state
        self.schedule_instant_message(content=UpdatedColorStateMsg(self.color_state), receiver_addr=self.observer)


class Observer(Agent):

    def __init__(self):
        super().__init__()

        self.color_state_history = {}
        self.solution_found = asyncio.Event()
        self.controller = None  # controller set once container has been started
        self.start_time = None  # starting timestamp in ns (set after receiving SetStateMsg by Controller)
        self.no_messages = 0

    def handle_message(self, content, meta):
        if isinstance(content, UpdatedColorStateMsg):
            for i, state in enumerate(content.color_state):
                self.color_state_history[i+1] = state
                self.no_messages += 1
        if isinstance(content, SolutionMsg):
            # check if solution_found is set to prevent double-sending of message to controller
            if not self.solution_found.is_set():
                self.solution_found.set()
                self.schedule_instant_message(
                    content=UpdateMsg(self.no_messages, self.start_time),
                    receiver_addr=self.controller,
                )
        if isinstance(content, SetSystemMsg):
            self.color_state_history = {0: content.agents_colors}  # add initial color state to history
            self.solution_found.clear()  # clear solution found Event
            self.no_messages = 0  # (re)set number of messages
            self.start_time = time.perf_counter_ns()


class Controller(Agent):

    def __init__(self):
        super().__init__()
        self.observer = None  # set once container is started
        self.agents = []  # set once container is started
        self.solution_history = {}
        self.solutions_received = 0
        self.solution_found = asyncio.Event()

    def handle_message(self, content, meta):
        if isinstance(content, UpdateMsg):
            self.solutions_received += 1
            # store solution in solution history
            self.solution_history[f'Solution {self.solutions_received}'] = {
                'no_messages': content.no_messages,
                'solution_time': time.perf_counter_ns() - content.start_time,
            }
            self.solution_found.set()

    async def set_system_state(self):
        colors = ["red", "blue", "green"]

        while True:
            agent1_color = random.choice(colors)
            agent2_color = random.choice(colors)
            agent3_color = random.choice(colors)

            # set, where duplicate colors are be removed
            agent_color_set = {agent1_color, agent2_color, agent3_color}

            # check if there is at least one duplicate color
            if len(agent_color_set) < 3:
                break

        agents_colors = {"ColorAgent0": agent1_color,
                         "ColorAgent1": agent2_color,
                         "ColorAgent2": agent3_color}

        # send message to observer first to ensure time measurements are correct
        await self.send_message(content=SetSystemMsg(agents_colors, colors, 0), receiver_addr=self.observer)

        # send system state to ColorAgents
        async with asyncio.TaskGroup() as tg:
            for i, agent in enumerate(self.agents):
                tg.create_task(self.send_message(content=SetSystemMsg(agents_colors, colors, i), receiver_addr=agent))

        # clear Event for second iteration
        self.solution_found.clear()


    async def run(self):
        await self.set_system_state()
        await self.solution_found.wait()
        await self.set_system_state()
        await self.solution_found.wait()
        print(self.solution_history)


async def main():

    codec = JSON()
    codec.add_serializer(*UpdatedColorStateMsg.__serializer__())
    codec.add_serializer(*SolutionMsg.__serializer__())
    codec.add_serializer(*UpdateMsg.__serializer__())
    codec.add_serializer(*SetSystemMsg.__serializer__())

    topology = complete_topology(3)
    for i, node in enumerate(per_node(topology)):
        agent = ColorAgent()
        node.add(agent)

    observer = Observer()
    controller = Controller()

    async with run_with_tcp(1,
                            observer, controller, *topology.agents,
                            codec=codec) as cl:
        for agent in topology.agents:
            agent.observer = observer.addr
            controller.agents.append(agent.addr)
        controller.observer = observer.addr
        observer.controller = controller.addr
        await controller.run()

asyncio.run(main())
