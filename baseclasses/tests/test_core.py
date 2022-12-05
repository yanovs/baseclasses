from typing import Optional

import pytest

import baseclasses


class Parent(baseclasses.BaseClass):
    x: int
    y: int
    z: Optional[str] = "parent"


class Middle(Parent):
    y: int = 1
    z: Optional[str] = "middle"


class Child(Middle):
    z: Optional[str] = baseclasses.Field(default="child")
    alpha: float


def test_basic():
    with pytest.raises(TypeError):
        Parent()
    with pytest.raises(TypeError):
        Parent(1, 2)
    with pytest.raises(TypeError):
        Parent(x=1)
    with pytest.raises(TypeError):
        Parent(foobar=1)
    with pytest.raises(TypeError):
        Parent(x=1, y=2, foobar=1)

    parent = Parent(x=1, y=2)
    assert parent.x == 1
    assert parent.y == 2
    assert parent.z == "parent"
    assert len(parent.get_fields()) == 3
