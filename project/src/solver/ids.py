import uuid


class Id:
    _value: str

    def __init__(self, prefix: str):
        unique = str(uuid.uuid4()).split("-")[0]
        self._value = f"{prefix}-{unique}"

    def __str__(self):
        self._value

    def __repr__(self):
        return f"{self.__class__.__name__}({self._value})"


class MessageId(Id):
    def __init__(self):
        super().__init__("message")


class SwitchId(Id):
    def __init__(self):
        super().__init__("switch")
