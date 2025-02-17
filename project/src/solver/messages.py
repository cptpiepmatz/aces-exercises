from dataclasses import dataclass
from .ids import MessageId, SwitchId
from typing import Self

@dataclass
class Message:
    """Base Message class to easily abstract that messages have a message id."""
    mid: MessageId

@dataclass
class ReachConnectionRequest(Message):
    """
    Request to reach a connection.

    This request will be propagated through the entire network until it reaches either
    a dead end or a bus agent with a connected bus.
    To avoid circular spreading check the message id and only propagate if this message 
    is new to an agent.

    Switch agents add their switch id to this request in order to track which switches
    have to connect to re-establish a connection.
    """

    bridged: bool
    "Initially this is set to `False`. When crossing a switch, this is set to `True`."

    switches: set[SwitchId]
    "Switches that were passed in the request chain."


@dataclass
class ReachConnectionResponse(Message):
    """
    Response to a `ReachConnectionRequest`.

    This response is sent as a response to the `ReachConnectionRequest`.
    It will backtrack to its original requester merging all possibilities to 
    re-establish a connection.
    When created by a dead end, `reached` will be set to `False` while a bus 
    agent with a connect bus will set it to `True`. 

    The `switches` describe a set of all options and each option contains all the 
    switches that would need to be switched to reach connection.
    """
    switches: set[frozenset[SwitchId]]
    reached: bool

    @classmethod
    def from_request(cls, request: ReachConnectionRequest, reached: bool) -> Self:
        if reached:
            assert request.switches, "could not have reached if no switches were used"

        return cls(
            mid=request.mid,
            switches={frozenset(request.switches)} if reached else set(),
            reached=reached,
        )

@dataclass
class SwitchRequest(Message):
    """
    A request to switch a switch to connect two busses.

    This request will be propagated through the entire network to reach the necessary 
    switch agent.
    The switch agent will then switch the switch if it isn't already switched.
    In response to that request a `SwitchMessage` will be broadcasted to let other 
    agents know that this switch is switched.
    They can then directly stop further propagating the request. 
    """
    sid: SwitchId

@dataclass
class SwitchMessage(Message):
    """
    A status message that the switch agent has switched its switch.

    This message will be broadcasted through the entire network to let everyone know 
    that the switch is switched.
    When receiving this message, the corresponding `SwitchRequest` can immediately be 
    dropped.

    This is not a response type as this message only reacts to the request but does not 
    specify a direct path back to the requester.
    """
    sid: SwitchId
