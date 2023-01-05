import dataclasses
from typing import Any, MutableMapping, Optional

import pytest

import baseclasses

# Advantage 1: Adding fields and overriding is easy (no extra classes)
# and less verbose (no redundant `@dataclasses.dataclass(frozen=True)`)


class BCParent(baseclasses.FrozenBaseClass):
    x: int
    y: int
    z: Optional[str] = "parent"


class BCChildX(BCParent):  # Inherits frozen state
    x: int = 2  # Overrides non-defaulted with default value
    z: Optional[str] = "child"  # Overrides defaulted with new default value
    alpha: float  # New field


class BCChildY(BCParent):  # Inherits frozen state
    y: int = 2  # Overrides non-defaulted with default value
    z: Optional[str] = "child"  # Overrides defaulted with new default value
    alpha: float  # New field


@dataclasses.dataclass(frozen=True)
class DCParent:
    x: int
    y: int
    z: Optional[str] = "parent"


@dataclasses.dataclass(frozen=True)
class _DCChild:
    alpha: float  # New field


# Can't do because `non-default argument 'y' follows default argument`
# @dataclasses.dataclass(frozen=True)
# class DCChildX(DCParent, _DCChild):
#     x: int = 2  # Overrides non-defaulted with default value
#     z: Optional[str] = "child"  # Overrides defaulted with new default value


@dataclasses.dataclass(frozen=True)
class DCChildY(DCParent, _DCChild):
    y: int = 2  # Overrides non-defaulted with default value
    z: Optional[str] = "child"  # Overrides defaulted with new default value


def test_defaulting():
    bc_child_x = BCChildX(y=3, alpha=1.5)
    assert bc_child_x.x == 2
    assert bc_child_x.y == 3
    assert bc_child_x.z == "child"
    assert bc_child_x.alpha == 1.5

    bc_child_y = BCChildY(x=3, alpha=1.5)
    assert bc_child_y.x == 3
    assert bc_child_y.y == 2
    assert bc_child_y.z == "child"
    assert bc_child_y.alpha == 1.5

    # Can't do
    # dc_child_x = DCChildX(x=3, alpha=1.5)

    dc_child_y = DCChildY(x=3, alpha=1.5)
    assert dc_child_y.x == 3
    assert dc_child_y.y == 2
    assert dc_child_y.z == "child"
    assert dc_child_y.alpha == 1.5


# Advantage 2: Having defaults depend on other kwargs means more accurate types
# and more consistent usage


class BCKwargs(baseclasses.FrozenBaseClass):
    window: int
    com: int = baseclasses.Field(  # type: ignore
        default_factory=lambda **kwargs: kwargs["window"]
    )


@dataclasses.dataclass(frozen=True)
class DCKwargs:
    window: int
    com: Optional[int] = None  # Not *really* Optional, just defaulted

    @property
    def effective_com(self) -> int:
        return self.window if self.com is None else self.com


def test_kwargs():
    bc_kwargs0 = BCKwargs(window=252)
    assert bc_kwargs0.window == 252
    assert bc_kwargs0.com == 252

    bc_kwargs1 = BCKwargs(window=252, com=181)
    assert bc_kwargs1.window == 252
    assert bc_kwargs1.com == 181

    dc_kwargs0 = DCKwargs(window=252)
    assert dc_kwargs0.window == 252
    # Have to have 2 different com fields:
    assert dc_kwargs0.com is None
    assert dc_kwargs0.effective_com == 252

    dc_kwargs1 = DCKwargs(window=252, com=181)
    assert dc_kwargs1.window == 252
    # Have to have 2 different com fields:
    assert dc_kwargs1.com == 181
    assert dc_kwargs1.effective_com == 181


# Advantage 3: OOP-ish and regular-style python


def test_oop():
    bc_child = BCChildY(x=1, alpha=1.5)
    assert len(bc_child.get_fields()) == 4
    assert isinstance(bc_child, baseclasses.BaseClass)

    dc_child = DCChildY(x=1, y=2, z="child", alpha=1.5)
    assert len(dataclasses.fields(dc_child)) == 4
    assert dataclasses.is_dataclass(dc_child)


# Advantage 4: Can change frozen status per class


class BCFrozenParent(baseclasses.FrozenBaseClass):
    x: int


class BCMutableChild(BCFrozenParent, frozen=False):
    pass


@dataclasses.dataclass(frozen=True)
class DCFrozenParent:
    x: int


# Can't change frozen state:
# @dataclasses.dataclass(frozen=False)
# class DCMutableChild(DCFrozenParent):
#     x: int


def test_change_frozen():
    with pytest.raises(baseclasses.FrozenInstanceError):
        bc_frozen_parent = BCFrozenParent(x=1)
        bc_frozen_parent.x = 2

    bc_mutable_child = BCMutableChild(x=1)
    bc_mutable_child.x = 2
    assert bc_mutable_child.x == 2

    with pytest.raises(dataclasses.FrozenInstanceError):
        dc_frozen_parent = DCFrozenParent(x=1)
        dc_frozen_parent.x = 2  # type: ignore # noqa


# Advantage 5: Arbitrary pre-init logic, while keeping frozen state


class BCPreInit(baseclasses.FrozenBaseClass):
    x: Optional[int] = None
    y: Optional[int] = None
    z: Optional[int] = None

    def __pre_init__(self, kwargs: MutableMapping[str, Any]):
        super().__pre_init__(kwargs)
        if kwargs.get("x", None) is None and kwargs.get("y", None) is None:
            kwargs["z"] = 100


# Can't do with dataclasses


def test_pre_init():
    bc_pre_init0 = BCPreInit(x=1, y=2)
    assert bc_pre_init0.x == 1
    assert bc_pre_init0.y == 2
    assert bc_pre_init0.z is None

    bc_pre_init1 = BCPreInit()
    assert bc_pre_init1.x is None
    assert bc_pre_init1.y is None
    assert bc_pre_init1.z == 100

    with pytest.raises(baseclasses.FrozenInstanceError):
        bc_pre_init1.x = 1
