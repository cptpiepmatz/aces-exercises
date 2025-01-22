from dataclasses import dataclass
from .ids import MessageId, SwitchId
from typing import Self

@dataclass
class ReachConnectionRequest:
    """
    Request to reach a connection.

    This request will be propagated through the entire network until it reaches either
    a dead end or a bus agent with a connected bus.
    To avoid circular spreading check the message id and only propagate if this message 
    is new to an agent.

    Switch agents add their switch id to this request in order to track which switches
    have to connect to re-establish a connection.
    """
    mid: MessageId
    switches: set[SwitchId]


@dataclass
class ReachConnectionResponse:
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
    mid: MessageId
    switches: set[frozenset[SwitchId]]
    reached: bool

    @classmethod
    def from_request(cls, request: ReachConnectionRequest, reached: bool):
        return cls(
            mid=request.mid,
            switches=request.switches,
            reached=reached,
        )
