"""Baseclasses.

Like dataclasses but:
  - No issues reordering and setting defaults on fields
  - No redundant decorators (and no ability to make
    child class not a baseclass)
  - No magic str generation
  - Can change frozen state per child class
  - Can set `str` in addition to `repr`

See also https://github.com/biqqles/dataclassy.
"""
import inspect
import operator
import types
from typing import (
    Any,
    Callable,
    Dict,
    List,
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
_EMPTY_METADATA: Mapping[str, Any] = types.MappingProxyType({})


# TODO: Field.hash should return True if that's the default,
#  instead of being None
class Field:
    __slots__ = (
        "name",
        "type",
        "default",
        "default_factory",
        "repr",
        "str",
        "hash",
        "compare",
        "metadata",
    )

    def __init__(
        self,
        default: Any = MISSING,
        default_factory: Callable[..., Any] = MISSING,  # type: ignore
        repr: bool = True,  # noqa
        str: bool = True,  # noqa
        hash: Optional[bool] = None,  # noqa
        compare: Optional[bool] = None,  # noqa
        metadata: Optional[Mapping[str, Any]] = None,  # pyright: ignore
    ):
        if default is not MISSING and default_factory is not MISSING:
            raise ValueError("Cannot set both default and default_factory")
        self.name = None  # Will be set later
        self.type = None  # Will be set later
        self.default = default
        self.default_factory = default_factory
        self.repr = repr
        self.str = str
        self.hash = hash
        self.compare = compare
        self.metadata = (
            _EMPTY_METADATA
            if metadata is None
            else types.MappingProxyType(metadata)
        )

    def __repr__(self):
        return (
            "Field("
            f"name={self.name!r},"
            f"type={self.type!r},"
            f"default={self.default!r},"
            f"default_factory={self.default_factory!r},"
            f"repr={self.repr!r},"
            f"str={self.str!r},"
            f"hash={self.hash!r},"
            f"compare={self.compare!r},"
            f"metadata={self.metadata!r},"
            ")"
        )


class InternalStateField(Field):
    def __init__(
        self,
        default: Any = MISSING,
        default_factory: Callable[..., Any] = MISSING,  # type: ignore
        metadata: Optional[Mapping[str, Any]] = None,
    ):
        # TODO: init=False
        # TODO: serialize=False?
        super().__init__(
            default=default,
            default_factory=default_factory,
            repr=False,
            str=False,
            hash=False,
            compare=False,
            metadata=metadata,
        )


class FrozenInstanceError(Exception):
    pass


class BaseMetaClass(type):
    def __new__(  # noqa: C901
        mcs,  # pyright: ignore
        name: str,
        bases: Tuple[Type, ...],
        namespace: Dict[str, Any],
        **kwargs,
    ):
        # Short-circuit oneself
        if name == "BaseClass" and namespace["__module__"] == Field.__module__:
            return type.__new__(mcs, name, bases, namespace)

        # Gather all annotations and defaults
        # across this class and its base classes
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

        # Construct fields from all annotations
        fields = []
        for field_name, type_ in all_annotations.items():
            if field_name in all_defaults:
                # noinspection PyUnresolvedReferences
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

        # Class state
        namespace["__frozen__"] = kwargs.get("frozen", frozen)

        # Signature for ipy help
        signature_parameters: List[inspect.Parameter] = []
        for field in fields:
            parameter_kwargs = {}
            if field.default is not MISSING:
                parameter_kwargs["default"] = field.default
            if field.type is not None:
                parameter_kwargs["annotation"] = field.type

            assert field.name is not None  # For mypy
            parameter = inspect.Parameter(
                field.name, inspect.Parameter.KEYWORD_ONLY, **parameter_kwargs
            )
            signature_parameters.append(parameter)
        namespace["__signature__"] = inspect.Signature(
            parameters=signature_parameters, return_annotation=None
        )

        return type.__new__(mcs, name, bases, namespace)


class BaseClass(metaclass=BaseMetaClass):
    def __init__(self, *args, **kwargs):  # noqa: C901
        if args:
            if set(self.__class__.__bases__) - {BaseClass, FrozenBaseClass}:
                raise TypeError(
                    f"Cannot use positional args when "
                    f"using inheritance: {self.__class__.__name__}"
                )

            kwargs_from_args = {}
            for arg, arg_field in zip(
                args, self.__class__.__fields__  # type: ignore
            ):
                if arg_field.name in kwargs:
                    raise TypeError(
                        f"Cannot use both positional and "
                        f"keyword args for {arg_field.name!r}: "
                        f"{self.__class__.__name__}"
                    )

                kwargs_from_args[arg_field.name] = arg

            kwargs_from_args.update(kwargs)
            kwargs = kwargs_from_args

        self.__pre_init__(kwargs)

        for field in self.__class__.__fields__:  # type: ignore
            if field.name in kwargs:
                self.__dict__[field.name] = kwargs[field.name]
            elif field.default_factory is not MISSING:
                if (
                    inspect.isfunction(field.default_factory)
                    and field.default_factory.__name__ == "<lambda>"
                    and inspect.getfullargspec(field.default_factory).varkw
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
            raise TypeError(
                f"{self.__class__.__name__}.__init__() "
                f"unexpected arguments: {unexpected_kwargs}"
            )

        self.__post_init__()

    def __pre_init__(self, kwargs: MutableMapping[str, Any]):
        pass

    def __post_init__(self):
        pass

    def __setattr__(self, key: str, value: Any):
        # noinspection PyUnresolvedReferences
        if self.__class__.__frozen__:  # type: ignore
            raise FrozenInstanceError(f"Cannot assign to field {key!r}")

        super().__setattr__(key, value)

    def __hash__(self) -> int:
        if not self.__class__.__frozen__:  # type: ignore
            return NotImplemented

        return hash(self._as_hash_tuple())

    def _compare(self, other: Any, op: Callable[[Any, Any], bool]) -> bool:
        if other.__class__ is self.__class__:
            # noinspection PyProtectedMember
            return op(self._as_compare_tuple(), other._as_compare_tuple())

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
                f"{field.name}={repr(getattr(self, field.name))}"  # type: ignore  # noqa
                for field in self.get_fields()
                if field.repr
            ]
        )
        return f"{self.__class__.__qualname__}({inner})"

    def __str__(self) -> str:
        # We need to this complicated logic because str(list) in python
        # actually calls repr() on each element
        # (see https://stackoverflow.com/a/12448200).
        # NB: The logic below wouldn't work with
        # recursive structures (e.g., list of list).
        inner_parts = []
        for field in self.get_fields():
            if not field.str:
                continue

            field_value = getattr(self, field.name)  # type: ignore
            # Explicitly call str() on elements of collection
            # (instead of repr())
            if isinstance(field_value, tuple):
                field_value = (
                    "(" + ", ".join(str(elem) for elem in field_value) + ")"
                )
            elif isinstance(field_value, list):
                field_value = (
                    "[" + ", ".join(str(elem) for elem in field_value) + "]"
                )
            elif isinstance(field_value, dict):
                field_value = (
                    "{"
                    + ", ".join(
                        f"{key!r}: {str(value)}"
                        for key, value in field_value.items()
                    )
                    + "}"
                )
            # Don't recurse down other baseclasses
            elif isinstance(field_value, BaseClass):
                field_value = f"{field_value.__class__.__name__}(...)"
            else:
                field_value = str(field_value)

            inner_parts.append(f"{field.name}={field_value}")

        return f"{self.__class__.__qualname__}({', '.join(inner_parts)})"

    # For prettier IPython output
    def _repr_pretty_(
        self, printer, cycle: bool  # IPython.lib.pretty.PrettyPrinter
    ):
        """Route pretty repr printing to str instead of repr.

        Adapted from https://stackoverflow.com/a/41454816.
        """
        printer.text(str(self) if not cycle else "...")

    def _as_hash_tuple(self) -> Tuple[Any, ...]:
        return tuple(
            getattr(self, field.name)  # type: ignore
            for field in self.get_fields()
            if field.hash is None or field.hash
        )

    def _as_compare_tuple(self) -> Tuple[Any, ...]:
        return tuple(
            getattr(self, field.name)  # type: ignore
            for field in self.get_fields()
            if field.compare is None or field.compare
        )

    def as_tuple(self) -> Tuple[Any, ...]:
        return tuple(
            getattr(self, field.name)  # type: ignore
            for field in self.get_fields()
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            field.name: getattr(self, field.name)  # type: ignore
            for field in self.get_fields()
        }

    def get_fields(self) -> Sequence[Field]:
        return self.__class__.__fields__  # type: ignore


class FrozenBaseClass(BaseClass, frozen=True):
    pass


def get_combined_metaclass(cls: Type, frozen: bool = False) -> Type:
    base_cls = FrozenBaseClass if frozen else BaseClass

    class CombinedMetaClass(type(base_cls), type(cls)):  # type: ignore
        pass

    return CombinedMetaClass


def get_fields(cls: Type[BaseClass]) -> Sequence[Field]:
    return cls.__fields__  # type: ignore
