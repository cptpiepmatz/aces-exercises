from dataclasses import dataclass
from typing import Any
from collections import deque
import mango
import asyncio
import random
import math


@dataclass
@mango.json_serializable
class Report:
    sun_hours: float
    kwh_price: float


class HouseAgent(mango.Agent):
    def __init__(self, index: int, capacity: float, solar_factor: float):
        super().__init__()
        self.index = index
        self.earned = 0.0

        self._stored = 0.0  # how much energy is currently stored
        self._capacity = capacity  # how much energy this house may store
        self._solar_factor = (
            solar_factor  # when the sun shines, how much energy can be stored
        )

        self._price_history = deque([math.inf], random.randint(2, 5))

    def log(self, msg: str):
        print(f"[{self.index}] {msg}")

    def sell(self, price: float):
        self.earned += self._stored * price
        self._stored = 0.0

    def handle_message(self, content, meta: dict[str, Any]):
        if not isinstance(content, Report):
            return

        self._stored = min(
            self._capacity, self._stored + self._solar_factor * content.sun_hours
        )

        self._price_history.append(content.kwh_price)
        if content.kwh_price == max(self._price_history):
            self.log("sell, price is good")
            self.sell(content.kwh_price)
            return

        if self._stored > 0.9 * self._capacity:
            self.log("sell, we are full")
            self.sell(content.kwh_price)
            return


async def main():
    codec = mango.JSON()
    codec.add_serializer(*Report.__serializer__())

    container = mango.create_tcp_container(addr="localhost:5555", codec=codec)
    agents = [
        container.register(HouseAgent(index, *params))
        for index, params in enumerate(
            [
                (200, 4),
                (500, 20),
                (800, 20),
                (300, 40),
            ]
        )
    ]

    def gen_report(last: float) -> tuple[float, Report]:
        delta = random.uniform(-0.5, 0.5)
        new = max(last + delta, 0)

        weather_factor = random.uniform(0, 4)
        energy_summand = random.uniform(-1, 1)
        report = Report(
            sun_hours=(new * weather_factor),
            kwh_price=(new + energy_summand),
        )

        return (new, report)

    async with mango.activate(container) as container:
        x = 1
        for i in range(100):
            print(f"\n=== Round {i:02} ===")
            # TODO: let agents influence energy price
            (x, report) = gen_report(x)
            [await container.send_message(report, a.addr) for a in agents]
            await asyncio.sleep(0.02)

        print("\n=== Results ===")
        [a.log(f"earned {a.earned}") for a in agents]


asyncio.run(main())
