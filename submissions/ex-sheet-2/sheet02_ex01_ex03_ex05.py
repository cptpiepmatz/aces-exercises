from mango import Agent, create_tcp_container, activate, addr, Performatives, \
    sender_addr, json_serializable, JSON, Role, agent_composed_of
from dataclasses import dataclass
import asyncio
import random
import numpy as np
import itertools
import pandas as pd


@json_serializable
@dataclass
class CommunicateNeighborhoodMsg:
    neighborhood: list


@json_serializable
@dataclass
class CommunicateIDMsg:
    id: int


class NeighborhoodRole(Role):

    def __init__(self):
        super().__init__()

        self.my_neighborhood = []
        self.my_neighborhood_done = asyncio.Future()
        self.received_ids = []
        self.msg_counter = 0

    def setup(self):
        self.context.subscribe_message(
            self,
            self.handle_communicate_neighborhood,
            lambda content, meta: isinstance(content, CommunicateNeighborhoodMsg),
        )
        self.context.subscribe_message(
            self,
            self.handle_communicate_id,
            lambda content, meta: isinstance(content, CommunicateIDMsg),
        )

    def on_start(self):
        self.context.schedule_instant_task(self.run())

    def log(self, msg):
        self.msg_counter += 1
        print(f'{self.context.aid}: {msg}')

    def handle_communicate_neighborhood(self, content, meta):
        self.my_neighborhood = content.neighborhood
        self.log('Received neighborhood.')
        self.my_neighborhood_done.set_result(True)

    def handle_communicate_id(self, content, meta):
        self.received_ids.append(content.id)
        self.log(f'Received ID from {content.id.aid}.')

    async def run(self):
        await self.my_neighborhood_done
        my_id = self.context.addr
        for addr in self.my_neighborhood:
            self.context.schedule_instant_message(content=CommunicateIDMsg(my_id),
                                                  receiver_addr=addr)


class TopologyCommunicator(Role):

    def __init__(self, agents, k, prob_factor):
        super().__init__()

        self.agents = agents
        self.k = k
        self.prob_factor = prob_factor
        self.topology = np.full((len(self.agents), len(self.agents)), False, dtype=bool)

    def on_start(self):
        self.context.schedule_instant_task(self.run())

    def create_small_world_topology(self):
        #fills topology matrix with true given k and probability factor
        for i, agent in enumerate(self.agents[: (len(self.agents) + 1)]):
            #add edges based on k
            for j in range(self.k):
                self.topology[i, (i - j - 1) % len(self.agents)] = True
                self.topology[i, (i + j + 1) % len(self.agents)] = True
                self.topology[(i - j - 1) % len(self.agents), i] = True
                self.topology[(i + j + 1) % len(self.agents), i] = True
            #add aditional edges based on probability factor
            for j in range(len(self.agents)):
                r = random.uniform(0, 1)
                if r < self.prob_factor:
                    self.topology[i, j] = True
                    self.topology[j, i] = True

    async def communicate_neighborhood(self):
        for i, agent in enumerate(self.agents):
            neighbors = np.where(self.topology[i])[0]
            neighborhood = [self.agents[j].addr for j in neighbors]
            self.context.schedule_instant_message(
                content=CommunicateNeighborhoodMsg(neighborhood),
                receiver_addr=agent.addr)

    async def run(self):
        self.create_small_world_topology()
        self.communicate_neighborhood()


async def main(k, prob_fac, df, index):
    CONTAINER_ADDRESS = ("127.0.0.1", 5555)
    my_codec = JSON()
    my_codec.add_serializer(*CommunicateNeighborhoodMsg.__serializer__())
    my_codec.add_serializer(*CommunicateIDMsg.__serializer__())

    container = create_tcp_container(CONTAINER_ADDRESS, codec=my_codec)

    number_of_agents = 10
    agents = []
    for i in range(number_of_agents):
        agent = container.register(agent_composed_of(NeighborhoodRole()),
                                   suggested_aid=f'Agent {i}')
        agents.append(agent)

    topology_agent = random.choice(agents)

    topology_agent.add_role(TopologyCommunicator(agents, k, prob_fac))

    async with activate(container):
        await asyncio.sleep(1)

    no_messages = 0
    for agent in agents:
        no_messages += agent.roles[0].msg_counter
    df.at[index, 'no_messages'] = no_messages


if __name__ == "__main__":
    k = [1, 2, 3]
    prob_fac = [0, 0.2]

    #itertools idea from chatgpt
    df = pd.DataFrame(list(itertools.product(k, prob_fac)), columns=['k', 'prob_fac'])
    df['no_messages'] = None

    for index, row in df.iterrows():
        k = row['k']
        prob_fac = row['prob_fac']
        asyncio.run(main(k, prob_fac, df, index))

    print(df)
