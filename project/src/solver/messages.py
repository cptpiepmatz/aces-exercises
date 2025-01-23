from dataclasses import dataclass
from .ids import MessageId, SwitchId
#from typing import Self

@dataclass
class ReachConnectionRequest:
    mid: MessageId
    switches: list[SwitchId]


@dataclass
class ReachConnectionResponse:
    mid: MessageId
    switches: list[SwitchId]
    reached: bool

    @classmethod
    def from_request(cls, request: ReachConnectionRequest, reached: bool):
        return cls(
            mid=request.mid,
            switches=request.switches,
            reached=reached,
        )
