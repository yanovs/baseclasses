import inspect
import operator
import types
from typing import (
    Any,
    Callable,
    Dict,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Tuple,
    Type,
)


# From dataclasses:
# A sentinel object to detect if a parameter is supplied or not. Use
# a class to give it a better repr.
class MissingType:
    pass


MISSING = MissingType()


# From dataclasses:
# Since most per-field metadata will be unused, create an empty
# read-only proxy that can be shared among all fields.
_EMPTY_METADATA = types.MappingProxyType({})


class Field:

    __slots__ = (
        "name",
        "type",
        "default",
        "default_factory",
        "repr",
        "hash",
        "metadata",
    )

    def __init__(
        self,
        default: Any = MISSING,
        default_factory: Callable[..., Any] = MISSING,
        repr: bool = True,
        hash: Optional[bool] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ):
        if default is not MISSING and default_factory is not MISSING:
            raise ValueError("Cannot set both default and default_factory")
        self.name = None
        self.type = None
        self.default = default
        self.default_factory = default_factory
        self.repr = repr
        self.hash = hash
        self.metadata = (
            _EMPTY_METADATA
            if metadata is None
            else types.MappingProxyType(metadata)
        )

    def __repr__(self):
        return (
            f"Field("
            f"name={self.name!r},"
            f"type={self.type!r},"
            f"default={self.default!r},"
            f"default_factory={self.default_factory!r},"
            f"repr={self.repr!r},"
            f"hash={self.hash!r},"
            f"metadata={self.metadata!r}"
        )


class FrozenInstanceError(Exception):
    pass


class BaseMetaClass(type):
    def __new__(
        mcs,
        name: str,
        bases: Tuple[Type, ...],
        namespace: Dict[str, Any],
        **kwargs,
    ):
        if name == "BaseClass" and namespace["__module__"] == Field.__module__:
            return type.__new__(mcs, name, bases, namespace)

        all_annotations = {}
        all_defaults = {}
        frozen = False
        for base in bases:
            if hasattr(base, "__all_annotations__"):
                base_annotations = getattr(base, "__all_annotations__")
            else:
                base_annotations = getattr(base, "__annotations__", {})

            if hasattr(base, "__all_defaults__"):
                base_defaults = getattr(base, "__all_defaults__")
            else:
                base_defaults = {}
                for field_name in base_annotations:
                    if hasattr(base, field_name):
                        base_defaults[field_name] = getattr(base, field_name)

            all_annotations.update(base_annotations)
            all_defaults.update(base_defaults)
            frozen = getattr(base, "__frozen__", frozen)

        all_annotations.update(namespace.get("__annotations__", {}))
        for field_name in all_annotations:
            if field_name not in namespace:
                continue

            all_defaults[field_name] = namespace[field_name]

        namespace["__all_annotations__"] = all_annotations
        namespace["__all_defaults__"] = all_defaults

        fields = []
        for field_name, type_ in all_annotations.items():
            if field_name in all_defaults:
                default = all_defaults[field_name]
                if isinstance(default, Field):
                    field = default
                else:
                    field = Field(default=default)
            else:
                field = Field()

            field.name = field_name
            field.type = type_
            fields.append(field)
        namespace["__fields__"] = fields

        namespace["__frozen__"] = kwargs.get("frozen", frozen)

        return type.__new__(mcs, name, bases, namespace)


class BaseClass(metaclass=BaseMetaClass):
    def __init__(self, **kwargs):
        self.__pre_init__(kwargs)

        for field in self.__class__.__fields__:  # type: Field
            if field.name in kwargs:
                self.__dict__[field.name] = kwargs[field.name]
            elif field.default_factory is not MISSING:
                # TODO: Find a better way of doing this
                # TODO: Also, this only passes in non-default kwargs
                if (
                    inspect.isfunction(field.default_factory)
                    and field.default_factory.__name__ == "<lambda>"
                ):
                    self.__dict__[field.name] = field.default_factory(**kwargs)
                else:
                    self.__dict__[field.name] = field.default_factory()
            elif field.default is not MISSING:
                self.__dict__[field.name] = field.default
            else:
                raise TypeError(
                    f"{self.__class__.__name__}.__init__() "
                    f"missing required argument: {field.name!r}"
                )

        unexpected_kwargs = set(kwargs.keys()) - set(self.__dict__.keys())
        if unexpected_kwargs:
            raise TypeError(f"Unexpected arguments: {unexpected_kwargs}")

        self.__post_init__()

    def __pre_init__(self, kwargs: MutableMapping[str, Any]):
        pass

    def __post_init__(self):
        pass

    def __setattr__(self, key: str, value: Any):
        if self.__class__.__frozen__:
            raise FrozenInstanceError(f"Cannot assign to field {key!r}")

        super().__setattr__(key, value)

    def __hash__(self):
        if not self.__class__.__frozen__:
            return NotImplemented

        as_tuple = tuple(
            getattr(self, field.name)
            for field in self.get_fields()
            if field.hash is None or field.hash
        )
        return hash(as_tuple)

    def _compare(self, other: Any, op: Callable[[Any, Any], bool]) -> bool:
        if other.__class__ is self.__class__:
            return op(self.as_tuple(), other.as_tuple())

        return NotImplemented

    def __eq__(self, other: Any) -> bool:
        return self._compare(other, operator.eq)

    def __lt__(self, other: Any) -> bool:
        return self._compare(other, operator.lt)

    def __le__(self, other: Any) -> bool:
        return self._compare(other, operator.le)

    def __gt__(self, other: Any) -> bool:
        return self._compare(other, operator.gt)

    def __ge__(self, other: Any) -> bool:
        return self._compare(other, operator.ge)

    def __repr__(self) -> str:
        inner = ", ".join(
            [
                f"{field.name}={repr(getattr(self, field.name))}"
                for field in self.get_fields()
                if field.repr
            ]
        )
        return f"{self.__class__.__qualname__}({inner})"

    def as_tuple(self) -> Tuple[Any, ...]:
        return tuple(getattr(self, field.name) for field in self.get_fields())

    def as_dict(self) -> Dict[str, Any]:
        return {
            field.name: getattr(self, field.name) for field in self.get_field()
        }

    def get_fields(self) -> Sequence[Field]:
        return self.__class__.__fields__


class FrozenBaseClass(BaseClass, frozen=True):
    pass
