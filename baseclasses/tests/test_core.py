import pydoc
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence

import cached_property
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
    z: Optional[str] = baseclasses.Field(default="child")  # type: ignore
    alpha: float


def test_basic():
    with pytest.raises(TypeError):
        Parent()
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

    with pytest.raises(TypeError):
        Child()

    child0 = Child(x=1, alpha=2.5)
    assert child0.x == 1
    assert child0.y == 1
    assert child0.z == "child"
    assert child0.alpha == 2.5

    child1 = Child(x=1, y=3, z="foo", alpha=3.5)
    assert child1.x == 1
    assert child1.y == 3
    assert child1.z == "foo"
    assert child1.alpha == 3.5


class DefaultFactory(baseclasses.BaseClass):
    x: int
    y: List[int] = baseclasses.Field(default_factory=list)  # type: ignore
    z: int = baseclasses.Field(  # type: ignore
        default_factory=lambda **kwargs: kwargs["x"] + 1
    )


class DefaultFactoryWithPreInit(baseclasses.BaseClass):
    x: int
    y: List[Dict] = baseclasses.Field(default_factory=dict)  # type: ignore
    z: int = baseclasses.Field(  # type: ignore
        default_factory=lambda **kwargs: kwargs["x"] + 1
    )

    def __pre_init__(self, kwargs: MutableMapping[str, Any]):
        super().__pre_init__(kwargs)
        kwargs["x"] *= 2


def test_default_factory():
    obj0 = DefaultFactory(x=1)
    assert obj0.x == 1
    assert isinstance(obj0.y, list) and len(obj0.y) == 0
    assert obj0.y is not DefaultFactory(x=1)
    assert obj0.z == 2

    obj1 = DefaultFactoryWithPreInit(x=1)
    assert obj1.x == 2
    assert isinstance(obj1.y, dict) and len(obj1.y) == 0
    assert obj1.y is not DefaultFactoryWithPreInit(x=1)
    assert obj1.z == 3


class StrClass(baseclasses.BaseClass):
    x: int
    y: str
    z: int = baseclasses.Field(  # type: ignore
        default=3, str=False
    )  # str is disabled, but repr is still True

    _state = baseclasses.InternalStateField(
        default=None
    )  # Never show this bc both str and repr are disabled


class StrClassWithColl(baseclasses.BaseClass):
    x: int
    values: Mapping[str, StrClass]


def test_repr_str():
    assert repr(StrClass(x=1, y="abc", z=3)) == "StrClass(x=1, y='abc', z=3)"
    assert str(StrClass(x=1, y="abc", z=3)) == "StrClass(x=1, y=abc)"

    # If we didn't have custom __str__ logic for collections,
    # the inner value would have be called with repr()
    assert (
        str(StrClassWithColl(x=1, values={"a": StrClass(2, "a")}))
        == "StrClassWithColl(x=1, values={'a': StrClass(x=2, y=a)})"
    )


class MutableParent(baseclasses.BaseClass):
    x: int


class FrozenMiddle(MutableParent, frozen=True):
    y: float


class MutableChild(FrozenMiddle, frozen=False):
    z: str = "abc"


def test_frozen():
    parent = MutableParent(x=1)
    parent.x = 100
    assert parent.x == 100

    middle = FrozenMiddle(x=1, y=2.0)
    with pytest.raises(baseclasses.FrozenInstanceError):
        middle.x = 100

    child = MutableChild(x=1, y=2.0)
    child.x = 100
    child.y = 200
    assert child.x == 100
    assert child.y == 200
    assert child.z == "abc"


class ProcessesKwargs(baseclasses.BaseClass):
    x: int
    y: Optional[int] = None

    def __pre_init__(self, kwargs: MutableMapping[str, Any]):
        super().__pre_init__(kwargs)
        if kwargs.get("y", None) is None:
            kwargs["y"] = kwargs["x"] * 2.0


def test_process_kwargs():
    obj0 = ProcessesKwargs(x=1)
    assert obj0.x == 1
    assert obj0.y == 2

    obj1 = ProcessesKwargs(x=1, y=10)
    assert obj1.x == 1
    assert obj1.y == 10


def test_eq():
    assert FrozenMiddle(x=1, y=2.0) == FrozenMiddle(x=1, y=2.0)
    assert FrozenMiddle(x=1, y=2.0) != FrozenMiddle(x=2, y=2.0)


def test_lt():
    assert FrozenMiddle(x=1, y=2.0) <= FrozenMiddle(x=1, y=2.0)
    assert FrozenMiddle(x=1, y=2.0) < FrozenMiddle(x=2, y=2.0)
    assert FrozenMiddle(x=1, y=2.0) < FrozenMiddle(x=2, y=3.0)


def test_hash():
    with pytest.raises(TypeError):
        hash(MutableChild(x=1, y=2.0))

    assert hash(FrozenMiddle(x=1, y=2.0)) == hash(FrozenMiddle(x=1, y=2.0))
    assert hash(FrozenMiddle(x=1, y=2.0)) != hash(FrozenMiddle(x=2, y=2.0))


class CachedProperty(baseclasses.FrozenBaseClass):
    x: int

    @cached_property.cached_property
    def y(self) -> int:
        return self.x + 1


def test_cached_property():
    obj = CachedProperty(x=1)
    assert obj.x == 1
    assert obj.y == 2
    assert obj.y == 2


class ClassVars(baseclasses.BaseClass):
    CONSTANT = 0  # No type annotation implies class var

    x: int
    y: int


def test_class_vars():
    obj0 = ClassVars(x=1, y=2)
    assert obj0.CONSTANT == 0
    assert ClassVars.CONSTANT == 0
    assert "CONSTANT" not in obj0.__dict__

    with pytest.raises(TypeError):
        ClassVars(x=1, y=2, CONSTANT=100)

    obj0.__class__.CONSTANT = 2  # pyright: ignore
    assert obj0.CONSTANT == 2

    obj1 = ClassVars(x=1, y=2)
    assert obj0.CONSTANT == 2
    assert obj1.CONSTANT == 2


def test_help():
    help_lines: Sequence[str] = pydoc.render_doc(Parent).splitlines()
    help_signature = help_lines[3].split("Parent")[1]
    expected_results = [
        "(*, x: int, y: int, z: Optional[str] = 'parent') -> None",
        "(*, x: int, y: int, z: Union[str, NoneType] = 'parent') -> None",
    ]
    assert help_signature in expected_results


class PosArgs(baseclasses.FrozenBaseClass):
    x: int
    y: int = 1
    z: int


def test_positional_args():
    obj0 = Parent(1, 2, z="foo")
    assert obj0.x == 1
    assert obj0.y == 2
    assert obj0.z == "foo"

    obj1 = Parent(10, 20, "bar")
    assert obj1.x == 10
    assert obj1.y == 20
    assert obj1.z == "bar"

    with pytest.raises(TypeError):
        Parent(1, 2, y=3, z="bar")

    with pytest.raises(TypeError):
        Middle(1, 2, z="baz")
    with pytest.raises(TypeError):
        Child(1, 2, z="baz", abc=1.2)

    obj2 = PosArgs(1, 2, 3)
    assert obj2.x == 1
    assert obj2.y == 2
    assert obj2.z == 3
