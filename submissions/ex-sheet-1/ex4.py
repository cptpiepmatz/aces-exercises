import asyncio
from dataclasses import dataclass

from mango import Agent, AgentAddress, activate, create_tcp_container, json_serializable


@dataclass(repr=False)
@json_serializable
class AgentMessage:
    weather_is_great: bool


class ReflexiveAgent(Agent):
    other_agents: list[AgentAddress] = []

    def log(self, msg):
        print(f"[{self.__class__.__name__}] {msg}")

    def handle_message(self, content, meta):
        if meta["sender_id"] is None:
            return self.handle_environmental_message(content, meta)
        return self.handle_social_message(content, meta)

    def handle_social_message(self, content, meta):
        """
        Handle a message that was sent by another agent.


        """
        pass

    def handle_environmental_message(self, content, meta):
        """
        Handle a message that was sent by the environment.

        These messages are sent by the container itself and represent changes in the
        environment.
        """
        if isinstance(content, WeatherMessage):
            match (content.clouds, content.rain):
                case (False, False):
                    self.log("The weather is great! I should tell the others.")
                    for other_agent_addr in self.other_agents:
                        self.schedule_instant_message(
                            AgentMessage(weather_is_great=True), other_agent_addr
                        )
                case (True, False):
                    self.log("The weather is ok.")
                case (True, True):
                    self.log("Ther weather is awful! I should tell the others.")
                    for other_agent_addr in self.other_agents:
                        self.schedule_instant_message(
                            AgentMessage(weather_is_great=False), other_agent_addr
                        )


class DeliberateAgent(Agent):
    # keep state about previous weather and own position
    last_rain: bool
    is_outside: bool

    def log(self, msg):
        print(f"[{self.__class__.__name__}] {msg}")

    def __init__(self):
        super().__init__()
        self.last_rain = False
        self.is_outside = False

    def on_ready(self):
        # perform an action without any external triggers
        self.log("I go outside!")
        self.is_outside = True

    def handle_message(self, content, meta):
        if isinstance(content, WeatherMessage):
            self.deliberate(content.rain)
            self.last_rain = content.rain
        if isinstance(content, AgentMessage):
            weather_condition = "great" if content.weather_is_great else "bad"
            self.log(f"It seems to be that the weather is {weather_condition}")

    def deliberate(self, is_raining: bool):
        match (self.is_outside, self.last_rain, is_raining):
            case (False, True, True):
                self.log("Is is still raining, I should stay inside")
            case (True, False, True):
                self.log("It started to rain, I should head inside.")
                self.is_outside = False
            case (True, False, False):
                self.log("It is still dry outside, I can stay outside")
            case (False, True, False):
                self.log("It stopped raining, I can go outside.")
                self.is_outside = True

@dataclass(repr=False)
@json_serializable
class WeatherMessage:
    rain: bool
    clouds: bool
    temp: float

    @classmethod
    def rainy(cls):
        return WeatherMessage(rain=True, clouds=True, temp=10)

    @classmethod
    def cloudy(cls):
        return WeatherMessage(rain=False, clouds=True, temp=13)

    @classmethod
    def sunny(cls):
        return WeatherMessage(rain=False, clouds=False, temp=20)


async def main():
    container = create_tcp_container("localhost:5555")

    reflexive_agent: ReflexiveAgent = container.register(ReflexiveAgent())
    deliberate_agent: DeliberateAgent = container.register(DeliberateAgent())

    reflexive_agent.other_agents.append(deliberate_agent.addr)

    weather_reports = [
        WeatherMessage.rainy(),
        WeatherMessage.rainy(),
        WeatherMessage.rainy(),
        WeatherMessage.cloudy(),
        WeatherMessage.cloudy(),
        WeatherMessage.sunny(),
        WeatherMessage.sunny(),
        WeatherMessage.rainy(),
        WeatherMessage.rainy(),
        WeatherMessage.sunny(),
        WeatherMessage.sunny(),
    ]

    async with activate(container) as container:
        for report in weather_reports:
            await container.send_message(report, reflexive_agent.addr)
            await container.send_message(report, deliberate_agent.addr)
            await asyncio.sleep(1)


asyncio.run(main())
