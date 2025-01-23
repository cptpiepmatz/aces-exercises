import mango
from asyncio import Event
import asyncio
from .ids import SwitchId, MessageId
from core import BusMeasurement, Switch
from typing import Any, Iterable
from .messages import ReachConnectionRequest, ReachConnectionResponse
from .util import ZeroBarrier

Neighbors = set[mango.AgentAddress]


class Agent(mango.Agent):
    neighbors: Neighbors

    # in this setup an agent may starts with unresolved issues
    # upon completion, our problem is solved,
    # using futures allows awaiting until everyone is happy
    resolved: Event

    def __init__(self, *, neighbors: Neighbors):
        super().__init__()
        self.neighbors = neighbors
        self.resolved = Event()

    def handle_message(self, content: Any, meta: dict[str, Any]):
        loop = asyncio.get_event_loop()
        match content:
            case ReachConnectionRequest():
                loop.run_until_complete(
                    self.handle_reach_connection_request(content, meta)
                )
            case ReachConnectionResponse():
                loop.run_until_complete(
                    self.handle_reach_connection_response(content, meta)
                )

    async def handle_reach_connection_request(
        self,
        request: ReachConnectionRequest,
        meta: dict[str, Any],
    ): ...

    async def handle_reach_connection_response(
        self,
        response: ReachConnectionResponse,
        meta: dict[str, Any],
    ): ...


class BusAgent(Agent):
    bus: BusMeasurement
    pending_requests: dict[MessageId, tuple[ZeroBarrier, ReachConnectionResponse]]

    def __init__(self, *, neighbors: Neighbors, bus: BusMeasurement):
        super().__init__(neighbors=neighbors)
        self.bus = bus

    def on_ready(self):
        if self.bus.connected:
            self.resolved.set_result()
        else:

            async def resolve():
                request = ReachConnectionRequest(mid=MessageId(), switches=[])
                targets = self.neighbors
                response = await self.send_reach_connection_requests_wait_for_response(
                    request, targets
                )
                print(f"{response}")
                # TODO: handle final response

            loop = asyncio.get_event_loop()
            loop.run_until_complete(resolve())

    async def send_reach_connection_requests_wait_for_response(
        self,
        request: ReachConnectionRequest,
        targets: Iterable[mango.AgentAddress],
    ) -> ReachConnectionResponse:  # merged response data
        barrier = ZeroBarrier()
        response = ReachConnectionResponse.from_request(request, False)
        self.pending_requests[request.mid] = (barrier, response)
        for target in targets:
            barrier.push()
            await self.send_message(request, target)

        # wait for all sent request to return with a response
        await barrier.wait()
        del self.pending_requests[request.mid]
        return response

    async def handle_reach_connection_request(self, request, meta):
        sender = mango.sender_addr(meta)

        # we are connected, tell that the requester
        if self.bus.connected:
            response = ReachConnectionResponse.from_request(request, True)
            await self.send_message(response, sender)
            return

        # we have seen that message, do not further propagate
        if request.mid in self.pending_requests:
            response = ReachConnectionResponse.from_request(request, False)
            await self.send_message(response, sender)
            return

        # we aren't connected and haven't seen the message yet, let's propagate
        other_neighbors = [n for n in self.neighbors if n != sender]
        response = await self.send_reach_connection_requests_wait_for_response(
            request, other_neighbors
        )

        # the response handler will update the response we have,
        # therefore we can just send that one
        await self.send_message(response, sender)

    async def handle_reach_connection_response(self, response, meta):
        mid = response.mid
        if mid not in self.pending_requests:
            raise  # TODO: some good error here

        pending_response = self.pending_requests[mid][1]
        pending_response.reached = pending_response.reached or response.reached
        pending_response.switches.update(response.switches)
        self.pending_requests[mid][0].pop()


class SwitchAgent(Agent):
    switch: Switch
    sid: SwitchId

    def __init__(
        self,
        *,
        neighbors: Neighbors,
        switch: Switch,
        sid: SwitchId,
    ):
        super().__init__(neighbors=neighbors)
        self.switch = switch
        self.sid = sid

        assert len(self.neighbors) == 2, "switch connects more than two busses"

        # all switches are happy with their initial state
        self.resolved.set()

    async def handle_reach_connection_request(self, request, meta):
        sender = mango.sender_addr(meta)
        other_neighbors = [n for n in self.neighbors if n != sender]
        for neighbor in other_neighbors:
            request.switches.add(self.sid)
            await self.send_message(request, neighbor)

    async def handle_reach_connection_response(self, response, meta):
        sender = mango.sender_addr(meta)
        other_neighbors = [n for n in self.neighbors if n != sender]
        for neighbor in other_neighbors:
            await self.send_message(response, neighbor)
