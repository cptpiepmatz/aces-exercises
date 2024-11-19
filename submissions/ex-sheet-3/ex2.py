import asyncio
import random
from dataclasses import dataclass

from mango import (
    JSON,
    Agent,
    complete_topology,
    json_serializable,
    per_node,
    run_with_tcp,
)


@json_serializable
@dataclass
class UpdatedColorStateMsg:
    color_state: dict


class ColorAgent(Agent):
    def __init__(self, domain, agents_colors, i):
        super().__init__()

        self.domain = domain
        self.color_state = agents_colors
        self.id = f"ColorAgent{i}"
        self.my_color = agents_colors.get(self.id)

    def handle_message(self, content, meta):
        if isinstance(content, UpdatedColorStateMsg):
            self.color_state = content.color_state
            self.change_color()

    def change_color(self):
        colors_in_use = set(self.color_state.values())
        available_colors = list(set(self.domain) - colors_in_use)
        if len(available_colors) == 0:
            print(f"Solution found: {self.color_state}")
        elif len(available_colors) == 1:
            self.my_color = available_colors[0]
            print(f"{self.id}: Changing my color to {self.my_color}.")
            self.color_state[self.id] = self.my_color
            self.send_color_state_msg()
        elif len(available_colors) == 2:
            self.my_color = random.choice(available_colors)
            print(f"{self.id}: Changing my color to {self.my_color}.")
            self.color_state[self.id] = self.my_color
            self.send_color_state_msg()

    def send_color_state_msg(self):
        neighbors = self.neighbors()
        for neighbor in neighbors:
            self.schedule_instant_message(
                content=UpdatedColorStateMsg(self.color_state), receiver_addr=neighbor
            )


def initialize_agents_with_random_colors(colors):
    # assign random colors until an invalid solution is found
    while True:
        agent1_color = random.choice(colors)
        agent2_color = random.choice(colors)
        agent3_color = random.choice(colors)

        # set, where duplicate colors are be removed
        agent_color_set = {agent1_color, agent2_color, agent3_color}

        # check if there is at least one duplicate color
        if len(agent_color_set) < 3:
            break

    agents_colors = {
        "ColorAgent0": agent1_color,
        "ColorAgent1": agent2_color,
        "ColorAgent2": agent3_color,
    }

    return agents_colors


async def main():
    colors = ["red", "blue", "green"]
    agents_colors = initialize_agents_with_random_colors(colors)
    print(f"Initial color state: {agents_colors}")

    codec = JSON()
    codec.add_serializer(*UpdatedColorStateMsg.__serializer__())

    topology = complete_topology(3)
    for i, node in enumerate(per_node(topology)):
        agent = ColorAgent(colors, agents_colors, i)
        node.add(agent)

    async with run_with_tcp(1, *topology.agents):
        topology.agents[0].change_color()
        await asyncio.sleep(1)


asyncio.run(main())
