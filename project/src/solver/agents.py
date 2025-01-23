from asyncio import Event
from typing import Any, Iterable

import mango
from core import BusMeasurement, Switch

from .ids import MessageId, SwitchId
from .messages import (
    ReachConnectionRequest,
    ReachConnectionResponse,
    SwitchMessage,
    SwitchRequest,
)
from .util import ZeroBarrier

Neighbors = set[mango.AgentAddress]


class Agent(mango.Agent):
    neighbors: Neighbors
    seen_messages: set[MessageId]

    # in this setup an agent may starts with unresolved issues
    # upon completion, our problem is solved,
    # using futures allows awaiting until everyone is happy
    resolved: Event

    def __init__(self, *, neighbors: Neighbors):
        super().__init__()
        self.neighbors = neighbors
        self.resolved = Event()

    def handle_message(self, content: Any, meta: dict[str, Any]):
        match content:
            case ReachConnectionRequest():
                self.schedule_instant_task(
                    self.handle_reach_connection_request(content, meta)
                )
            case ReachConnectionResponse():
                self.schedule_instant_task(
                    self.handle_reach_connection_response(content, meta)
                )
            case SwitchRequest():
                self.schedule_instant_task(self.handle_switch_request(content, meta))
            case SwitchMessage():
                self.schedule_instant_task(self.handle_switch_message(content, meta))

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

    async def handle_switch_request(
        self, request: SwitchRequest, meta: dict[str, Any]
    ): ...

    async def handle_switch_message(
        self, message: SwitchMessage, meta: dict[str, Any]
    ): ...

    async def broadcast_message(self, message: Any):
        for neighbor in self.neighbors:
            await self.send_message(message, neighbor)

    async def propagate_message(self, message: Any, meta: dict[str, Any]):
        sender = mango.sender_addr(meta)
        other_neighbors = [n for n in self.neighbors if n != sender]
        for neighbor in other_neighbors:
            await self.send_message(message, neighbor)


class BusAgent(Agent):
    bus: BusMeasurement
    pending_requests: dict[MessageId, tuple[ZeroBarrier, ReachConnectionResponse]]
    requested_switches: set[SwitchId]

    def __init__(self, *, neighbors: Neighbors, bus: BusMeasurement):
        super().__init__(neighbors=neighbors)
        self.bus = bus
        self.pending_requests = {}
        self.requested_switches = set()

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
                option = BusAgent.best_option(response.switches)
                if option is None:
                    # TODO: handle this better
                    raise "no solution found"
                for sid in option:
                    await self.broadcast_message(SwitchRequest(mid=MessageId(), sid=sid))

            self.schedule_instant_task(resolve())

    @staticmethod
    def best_option(options: set[frozenset[SwitchId]]) -> None | frozenset[SwitchId]:
        # sort by length first, then lexicographically by SwitchId
        sorted_options = sorted(options, key=lambda s: (len(s), sorted(s)))
        return sorted_options[0] if sorted_options else None

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
        assert mid in self.pending_requests, "got response to no request"

        # merge pending response with received response
        pending_response = self.pending_requests[mid][1]
        pending_response.reached = pending_response.reached or response.reached
        pending_response.switches.update(response.switches)
        self.pending_requests[mid][0].pop()

    async def handle_switch_request(self, request, meta):
        if request.sid not in self.requested_switches:
            # we don't need that switch, so we don't need to propagate
            return

        if request.mid not in self.seen_messages:
            self.seen_messages.add(request.mid)
            await self.propagate_message(request, meta)

    async def handle_switch_message(self, message, meta):
        if message.sid in self.requested_switches:
            self.requested_switches.remove(message.sid)
            if not self.requested_switches:
                self.resolved.set()

        if message.mid not in self.seen_messages:
            self.send_message.add(message.mid)
            await self.propagate_message(message, meta)


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
        request.switches.add(self.sid)
        await self.propagate_message(request, meta)

    async def handle_reach_connection_response(self, response, meta):
        await self.propagate_message(response, meta)

    async def handle_switch_request(self, request, meta):
        if request.sid != self.sid:
            return await self.propagate_message(request, meta)

        if not self.switch.is_switched():
            self.switch.switch(True)
            await self.broadcast_message(SwitchMessage(mid=MessageId(), sid=self.sid))

    async def handle_switch_message(self, message, meta):
        if message.mid not in self.seen_messages:
            self.seen_messages.add(message.mid)
            await self.propagate_message(message, meta)
