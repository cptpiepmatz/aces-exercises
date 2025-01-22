import uuid
from typing import Self
from functools import total_ordering


@total_ordering
class Id:
    _value: str

    def __init__(self, prefix: str):
        unique = str(uuid.uuid4()).split("-")[0]
        self._value = f"{prefix}-{unique}"

    def __str__(self):
        return self._value

    def __repr__(self):
        return f"{self.__class__.__name__}({self._value})"

    def __eq__(self, other: object):
        if type(self) is type(other):
            assert isinstance(other, Id)
            return self._value == other._value
        if isinstance(other, Id):
            raise IncompatibleIdError(self, other)
        return NotImplemented

    def __lt__(self, other: Self):
        if type(self) is type(other):
            return self._value < other._value
        if isinstance(other, Id):
            raise IncompatibleIdError(self, other)
        return NotImplemented
    
    def __hash__(self):
        return hash(self._value)


class IncompatibleIdError(Exception):
    _left: Id
    _right: Id

    def __init__(self, left: Id, right: Id):
        left_name = type(left).__name__
        right_name = type(right).__name__
        message = (
            f"IDs of different types are incompatible, got {left_name} and {right_name}"
        )
        super().__init__(message)
        self._left = left
        self._right = right

    @property
    def left(self):
        return self._left
    
    @property
    def right(self):
        return self._right


class MessageId(Id):
    def __init__(self):
        super().__init__("message")


class SwitchId(Id):
    def __init__(self):
        super().__init__("switch")
