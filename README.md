# baseclasses

Simple dataclasses alternative (beta)

[![PyPI version](https://badge.fury.io/py/baseclasses.svg)](https://badge.fury.io/py/baseclasses)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/baseclasses.svg)](https://pypi.python.org/pypi/baseclasses/)
[![GitHub Actions (Tests)](https://github.com/yanovs/baseclasses/workflows/Test/badge.svg)](https://github.com/yanovs/baseclasses)

## Installation

`baseclasses` is available on [PyPI](https://pypi.org/project/baseclasses/):

```bash
pip install baseclasses
```

## Quick Start

`baseclasses` is an alternative to [`dataclasses`](https://docs.python.org/3/library/dataclasses.html).

There are many such alternatives, and there are a lot of reasons 
to use them (including the built-in
`dataclasses`), but if you want a library with:

- No monkey-patched methods generated from strings
- No special decorators, just regular inheritance
- Ability to order fields in subclasses as desired
- Auto-inheritance of parent properties, with ability to change per subclass
- Emphasis on keyword args over positional args
- Optional `__pre_init__` ability to mutate kwargs
- Optional ability to reference other kwargs in `default_factory` func
- A shorthand helper to specify `InternalStateField`
- Ability to differentiate between `str` and `repr`

you can give `baseclasses` a try. E.g.:

```python
from typing import Dict, Optional

import baseclasses


# No decorator
class Foo(baseclasses.FrozenBaseClass):
    a: int
    b: int
    c: Optional[str] = baseclasses.Field(default="hello", hash=False)
    _d: Dict = baseclasses.InternalStateField(default_factory=dict)


# Auto-inherits FrozenBaseClass properties
class ChildFoo(Foo):
    # No problems with child class field ordering
    x: float

    # Dynamic defaults
    y: int = baseclasses.Field(
        default_factory=lambda **kwargs: kwargs["a"] * 2.0
    )


# Override frozen state per child class
class MutableChildFoo(ChildFoo, frozen=False):
    pass
```

## Comparisons to Alternatives

See [`tests/test_compare.py`](https://github.com/yanovs/baseclasses/blob/main/baseclasses/tests/test_compare.py).

Like [dataclasses](https://docs.python.org/3/library/dataclasses.html), but:
- No issues with adding new optional fields because you're forced to 
use `kwargs` in all but the simplest cases
- Uses `metaclass` and simple inheritance over monkey-patched generated code
- Child classes automatically inherit state from parent, 
so no need to re-declare
- But you can also change `frozen` status per child class
- You can use `default_factory(lambda **kwargs: ...)` to access init fields
- Or you can mutate kwargs with an optional `__pre_init__`
- More consistent with traditional OOP style 
(e.g., `obj.get_fields()` instead of `dataclasses.get_fields(obj)`)

Like [dataclassy](https://github.com/biqqles/dataclassy) but:
- Uses `metaclass` and simple inheritance over monkey-patched generated code

There are others:
- [attrs](https://github.com/python-attrs/attrs)
- [pydantic](https://github.com/samuelcolvin/pydantic)
- [traitlets](https://github.com/ipython/traitlets)
- [param](https://param.holoviz.org/)

Note: there are [perfectly valid reasons](https://peps.python.org/pep-0557/#rationale) 
for why the Python community
decided to use generated code over simple inheritance.
`baseclasses` is just an alternative that implements things differently.

## TODO

- [ ] Add `init` property to field (to mirror `dataclasses`)
- [ ] Expose `obj.replace(**kwargs)` (to mirror `dataclasses`)
- [ ] Consider `serialize` property to field
- [ ] Take advantage of [PEP 681 included in Python 3.11](https://docs.python.org/3/whatsnew/3.11.html#whatsnew311-pep681)
