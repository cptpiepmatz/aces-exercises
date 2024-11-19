import asyncio
import random
from asyncio import TaskGroup
from enum import Enum
from typing import Any, Self

import mango
from mango import Agent, AgentAddress


class Color(Enum):
    Red = "red"
    Blue = "blue"
    Black = "black"  # in the slides this is a very dark blue, but black is simpler

    @classmethod
    def pick(cls) -> Self:
        return random.choice([cls.Red, cls.Blue, cls.Black])


class ColorAgent(Agent):
    color: Color
    neighbors: list[AgentAddress]

    def __init__(self):
        super().__init__()
        self.color = Color.pick()
        self.neighbors = list()

    def on_ready(self):
        self.schedule_instant_task(self.share_color())

    async def share_color(self):
        async with TaskGroup() as tg:
            for neighbor in self.neighbors:
                tg.create_task(self.send_message(self.color, neighbor))

    def handle_message(self, content: Color, meta: dict[str, Any]):
        if content == self.color:
            self.color = Color.pick()
            self.schedule_instant_task(self.share_color())


async def main():
    container = mango.create_tcp_container("localhost:5000")

    a: ColorAgent = container.register(ColorAgent())
    b: ColorAgent = container.register(ColorAgent())
    c: ColorAgent = container.register(ColorAgent())

    a.neighbors = [b.addr, c.addr]
    b.neighbors = [a.addr, c.addr]
    c.neighbors = [a.addr, b.addr]

    print(f"Initial = A: {a.color.value}, B: {b.color.value}, C: {c.color.value}")

    async with mango.activate(container):
        ab, bc, ca = False, False, False
        while not (ab and bc and ca):
            ab = a.color != b.color
            bc = b.color != c.color
            ca = c.color != a.color
            await asyncio.sleep(0.1)

        print(f"Solution = A: {a.color.value}, B: {b.color.value}, C: {c.color.value}")


asyncio.run(main())
