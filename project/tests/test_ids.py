from ..src.solver.ids import Id, SwitchId, MessageId, IncompatibleIdError
from copy import copy, deepcopy
import pytest

def test_collision_free():
    amount = 10000
    ids = {Id("test") for _ in range(amount)}
    assert len(ids) == amount

def test_equality():
    id1 = Id("test")
    id2 = Id("test")
    assert id1 != id2

def test_copy():
    id1 = Id("test")
    id2 = copy(id1)
    id3 = deepcopy(id1)

    assert id1 == id2
    assert id2 == id3
    assert id3 == id1

def test_order():
    id1 = Id("test")
    id2 = Id("test")
    id3 = Id("test")
    ids = [id1, id2, id3]

    assert sorted(ids) == sorted(ids)

def test_duplicate_free():
    id1 = Id("test")
    id2 = copy(id1)
    id3 = deepcopy(id1)

    assert len({id1, id2, id3}) == 1

def test_incompatibility():
    switch_id = SwitchId()
    message_id = MessageId()

    with pytest.raises(IncompatibleIdError):
        switch_id == message_id

    with pytest.raises(IncompatibleIdError):
        sorted([switch_id, message_id])
