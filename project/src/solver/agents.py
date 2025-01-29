from asyncio import Event, TimeoutError
from typing import Any, Iterable
import asyncio

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
        self.seen_messages = set()

    def log(self, *msg):
        match len(msg):
            case 1:
                print(f"{self.aid}: {msg[0]}")
            case _:
                print(f"{self.aid}:")
                [print(f"\t{msg}") for msg in msg]

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
    deferred_requests: list[tuple[mango.AgentAddress, ReachConnectionRequest]]
    pending_requests: dict[MessageId, tuple[ZeroBarrier, ReachConnectionResponse]]
    requested_switches: set[SwitchId]

    def __init__(self, *, neighbors: Neighbors, bus: BusMeasurement):
        super().__init__(neighbors=neighbors)
        self.bus = bus
        self.deferred_requests = []
        self.pending_requests = {}
        self.requested_switches = set()

    def on_ready(self):
        if self.bus.connected:
            self.resolved.set()
            self.log("I am connected.")
        elif not self.neighbors:
            self.resolved.set()
            self.log("No solution available.")
        else:

            async def resolve():
                request = ReachConnectionRequest(
                    mid=MessageId(), bridged=False, switches=set()
                )
                targets = self.neighbors
                response = await self.send_reach_connection_requests_wait_for_response(
                    request, targets
                )
                self.log(f"Received final response: {response}.")
                option = BusAgent.best_option(response.switches)
                self.log(f"Selecting best option: {option}.")
                if option is None:
                    self.resolved.set()
                    self.log("No solution found.")
                    await self.respond_deferred_requests(False)
                    return
                for sid in option:
                    self.requested_switches.add(sid)
                    self.log(f"Broadcasting best option to {sid}")
                    await self.broadcast_message(
                        SwitchRequest(mid=MessageId(), sid=sid)
                    )
                await self.respond_deferred_requests(True)

            self.schedule_instant_task(resolve())
            self.log("Resolving connection issue...")

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
        try:
            await asyncio.wait_for(barrier.wait(), timeout=10)
            del self.pending_requests[request.mid]
        except TimeoutError:
            self.log("response timed out, will respond with intermediate results")
        return response

    async def respond_deferred_requests(self, reached: bool):
        for addr, req in self.deferred_requests:
            res = ReachConnectionResponse.from_request(req, reached)
            await self.send_message(res, addr)

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
        
        if request.bridged:
            res = ReachConnectionResponse.from_request(request, False)
            await self.send_message(res, sender)
            return

        # TODO: handle more than 2 disconnects here

        # # defer bridged request if we cannot answer them right away
        # if request.bridged:
        #     self.deferred_requests.append((sender, request))
        #     return

        # # if we get request where we already got a bridge request, respond with `False`
        # deferred_requests = [req[1] for req in self.deferred_requests if req[1].mid == request.mid]
        # self.log(self.deferred_requests)
        # for req in deferred_requests:
        #     res = ReachConnectionResponse.from_request(req, False)
        #     await self.send_message(res, sender)
        #     # do not return, we still have work to do

        # we aren't connected and haven't seen the message yet, let's propagate
        other_neighbors = [n for n in self.neighbors if n != sender]

        self.log(
            f"Request {request.mid}",
            f"From {sender.aid}",
            f"Sending response to {[n.aid for n in other_neighbors]}",
        )

        response = await self.send_reach_connection_requests_wait_for_response(
            request, other_neighbors
        )

        # the response handler will update the response we have,
        # therefore we can just send that one
        await self.send_message(response, sender)

    async def handle_reach_connection_response(self, response, meta):
        mid = response.mid
        assert mid in self.pending_requests, "got response to no request"

        zero_barrier, pending_response = self.pending_requests[mid]
        # merge pending response with received response
        pending_response.reached = pending_response.reached or response.reached
        pending_response.switches.update(response.switches)
        zero_barrier.pop()

    async def handle_switch_request(self, request, meta):
        if request.mid not in self.seen_messages:
            self.requested_switches.add(request.sid)
            self.seen_messages.add(request.mid)
            await self.broadcast_message(request)

    async def handle_switch_message(self, message, meta):
        if message.sid in self.requested_switches:
            self.requested_switches.remove(message.sid)
            if not self.requested_switches:
                self.resolved.set()
                self.log("I am connected.")

        if message.mid not in self.seen_messages:
            self.seen_messages.add(message.mid)
            await self.broadcast_message(message)


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
        request.bridged = True
        await self.propagate_message(request, meta)

    async def handle_reach_connection_response(self, response, meta):
        await self.propagate_message(response, meta)

    async def handle_switch_request(self, request, meta):
        if request.sid != self.sid:
            return await self.broadcast_message(request)

        if not self.switch.is_switched():
            self.switch.switch(True)
            self.log("Performing switching action.")

        # broadcast even if switched to let requesting agent know that the switch has been set
        await self.broadcast_message(SwitchMessage(mid=MessageId(), sid=self.sid))

    async def handle_switch_message(self, message, meta):
        if message.mid not in self.seen_messages:
            self.seen_messages.add(message.mid)
            await self.broadcast_message(message)
