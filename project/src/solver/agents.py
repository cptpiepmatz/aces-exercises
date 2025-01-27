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
    pending_requests: dict[MessageId, tuple[ZeroBarrier, ReachConnectionResponse]]
    requested_switches: set[SwitchId]

    def __init__(self, *, neighbors: Neighbors, bus: BusMeasurement):
        super().__init__(neighbors=neighbors)
        self.bus = bus
        self.pending_requests = {}
        self.requested_switches = set()

    def on_ready(self):
        if self.bus.connected:
            self.resolved.set()
            self.log('I am connected.')
        elif not self.neighbors:
            self.resolved.set()
            self.log('No solution available.')
        else:

            async def resolve():
                request = ReachConnectionRequest(mid=MessageId(), switches=set())
                targets = self.neighbors
                response = await self.send_reach_connection_requests_wait_for_response(
                    request, targets
                )
                self.log(f'Received final response: {response}.')
                option = BusAgent.best_option(response.switches)
                self.log(f'Selecting best option: {option}.')
                if option is None:
                    self.resolved.set()
                    self.log("No solution found.")
                    return
                for sid in option:
                    self.requested_switches.add(sid)
                    self.log(f'Broadcasting best option to {sid}')
                    await self.broadcast_message(SwitchRequest(mid=MessageId(), sid=sid))

            self.schedule_instant_task(resolve())
            self.log('Resolving connection issue...')

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
            #self.log(f'Sending request with id {request.mid} to {target.aid}')
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
            #self.log(f'I am connected. Sending response to {meta["sender_id"]} to request with id {request.mid} with solution {response.switches}.')
            await self.send_message(response, sender)
            return

        # we have seen that message, do not further propagate
        if request.mid in self.pending_requests:
            response = ReachConnectionResponse.from_request(request, False)
            #self.log(
            #    f'I am not connected. Sending response to {meta["sender_id"]} to request with id {request.mid}: {response.switches}.')
            await self.send_message(response, sender)
            return

        # we aren't connected and haven't seen the message yet, let's propagate
        other_neighbors = [n for n in self.neighbors if n != sender]
        response = await self.send_reach_connection_requests_wait_for_response(
            request, other_neighbors
        )
        #self.log(f'Propagating response to request witd id {request.mid} to {meta["sender_id"]}: {response.switches}.')

        # the response handler will update the response we have,
        # therefore we can just send that one
        await self.send_message(response, sender)

    async def handle_reach_connection_response(self, response, meta):
        mid = response.mid
        assert mid in self.pending_requests, "got response to no request"

        zero_barrier, pending_response = self.pending_requests[mid]
        # merge pending response with received response
        pending_response.reached = pending_response.reached or response.reached
        pending_response.switches = response.switches
        self.pending_requests[mid] = (zero_barrier, pending_response)
        self.pending_requests[mid][0].pop()
        #self.log(f'Received response: {pending_response.switches}')

    async def handle_switch_request(self, request, meta):
        #if request.sid not in self.requested_switches:
            # we don't need that switch, so we don't need to propagate
        #   return

        if request.mid not in self.seen_messages:
            self.requested_switches.add(request.sid)
            self.seen_messages.add(request.mid)
            await self.broadcast_message(request)

    async def handle_switch_message(self, message, meta):
        if message.sid in self.requested_switches:
            self.requested_switches.remove(message.sid)
            if not self.requested_switches:
                self.resolved.set()
                self.log('I am connected.')

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
        #self.log(f'Added myself {self.sid} to solution for request with id {request.mid}.')
        await self.propagate_message(request, meta)

    async def handle_reach_connection_response(self, response, meta):
        await self.propagate_message(response, meta)

    async def handle_switch_request(self, request, meta):
        if request.sid != self.sid:
            return await self.broadcast_message(request)

        if not self.switch.is_switched():
            self.switch.switch(True)
            self.log('Performing switching action.')

        # broadcast even if switched to let requesting agent know that the switch has been set
        await self.broadcast_message(SwitchMessage(mid=MessageId(), sid=self.sid))

    async def handle_switch_message(self, message, meta):
        if message.mid not in self.seen_messages:
            self.seen_messages.add(message.mid)
            await self.broadcast_message(message)
