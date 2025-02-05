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
    """
    Base agent class extending the Mango Agent to simplify implement the `BusAgent` and
    `SwitchAgent`.

    Mainly this class provides the `log` method to easily log messages from agents and
    the different handlers for our messages which all are marked as async to allow the
    usage of `send_message` which requires an async context.
    """

    neighbors: Neighbors
    seen_messages: set[MessageId]

    resolved: Event
    """
    An agent is resolved when it doesn't need any further changes to be fully connected.

    Using this event allows external code to properly wait until every agent is done 
    working.
    """

    def __init__(self, *, neighbors: Neighbors):
        super().__init__()
        self.neighbors = neighbors
        self.resolved = Event()
        self.seen_messages = set()

    def log(self, *msg):
        """
        Log a message with the agent aid prefixed.

        On multiple messages this will format the output to have multiple indented
        lines to more easily distinguish which agent posted what.
        This is helpful in situations when the provided context gets quite large.
        """
        match len(msg):
            case 1:
                print(f"{self.aid}: {msg[0]}")
            case _:
                print(f"{self.aid}:")
                [print(f"\t{msg}") for msg in msg]

    def handle_message(self, content: Any, meta: dict[str, Any]):
        """
        Schedule message handlers for all of our message types.

        This allows using async message handlers without having to call
        `schedule_instant_task` everywhere in the derived agents.
        """
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
    """
    Agent placed on bus nodes.

    This agent represents a bus and contains a `BusMeasurement` to interact with the
    pandapower network.
    `on_ready` it checks if it is connected and if not, it starts resolving the problem
    by sending a `ReachConnectionRequest` if it has any members to find a way to connect
    with the rest of the network again.
    """

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
            self.log("I am connected.")
        elif not self.neighbors:
            self.resolved.set()
            self.log("No solution available.")
        else:

            async def resolve():
                """
                Try to resolve the connection issue.

                Resolve the connection issue by first sending out
                `ReachConnectionRequest`s across the network.
                When all responses reached us back again, we can determine the best
                option and either report that no option was found to send request to
                all the necessary switches to reconnect again.
                """
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
                    return
                for sid in option:
                    self.requested_switches.add(sid)
                    self.log(f"Broadcasting best option to {sid}")
                    await self.broadcast_message(
                        SwitchRequest(mid=MessageId(), sid=sid)
                    )

            self.schedule_instant_task(resolve())
            self.log("Resolving connection issue...")

    @staticmethod
    def best_option(options: set[frozenset[SwitchId]]) -> None | frozenset[SwitchId]:
        """
        Search for the best option give a set of options.

        An option is preferred if it shorter than another one.
        Then the IDs are used to get the best response.
        IDs have an order but that order itself is irrelevant as each switch is equally
        good to enable again.
        We just need to make sure that every agent decides on the same switch.
        """
        sorted_options = sorted(options, key=lambda s: (len(s), sorted(s)))
        return sorted_options[0] if sorted_options else None

    async def send_reach_connection_requests_wait_for_response(
        self,
        request: ReachConnectionRequest,
        targets: Iterable[mango.AgentAddress],
    ) -> ReachConnectionResponse:  # merged response data
        """
        Send a `ReachConnectionRequest` to all targets and wait for their responses and 
        merging them.

        The merging behavior is implemented in the `handle_reach_connection_response` 
        method. 
        """
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

        # the request bridged over a switch but we aren't connected, return this as a 
        # dead end
        if request.bridged:
            res = ReachConnectionResponse.from_request(request, False)
            await self.send_message(res, sender)
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
