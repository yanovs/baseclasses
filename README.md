# baseclasses

Dataclasses alternative (beta)

[![PyPI version](https://badge.fury.io/py/baseclasses.svg)](https://badge.fury.io/py/baseclasses)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/baseclasses.svg)](https://pypi.python.org/pypi/baseclasses/)
[![GitHub Actions (Tests)](https://github.com/yanovs/baseclasses/workflows/Test/badge.svg)](https://github.com/yanovs/baseclasses)

## Quick Start

There are a lot of reasons to use alternatives (including the built-in
`dataclasses`), but if you want some no monkey-patched methods
and some extra features (more coming soon!), you can give `baseclasses` a try.

```python
from typing import Dict, Optional

import baseclasses


# No decorator
class Foo(baseclasses.FrozenBaseClass):
    a: int
    b: int
    c: Optional[str] = "hello"
    _d: Dict = baseclasses.Field(default_factory=dict, repr=False, hash=False)


# Auto-inherits FrozenBaseClass properties
class ChildFoo(Foo):
    # No problems with child class field ordering
    x: float
    # Dynamic defaults
    y: int = baseclasses.Field(default_factory=lambda **kwargs: kwargs["a"] * 2.0)


# Override frozen state per child class
class MutableChildFoo(ChildFoo, frozen=False):
    pass
```

## Comparison to Alternatives

See `tests/test_compare.py`.

Like [dataclasses](https://docs.python.org/3/library/dataclasses.html), but:
- No issues with adding new optional fields because you're forced to use `kwargs` in all but the simplest cases
- Uses `metaclass` and simple inheritance over monkey-patched generated code
- Child classes automatically inherit state from parent, so no need to re-declare
- But you can also change `frozen` status per child class
- You can use `default_factory(lambda **kwargs: ...)` to access init fields
- Or you can mutate kwargs with an optional `__pre_init__`
- More consistent with traditional OOP style (e.g., `obj.get_fields()` instead of `dataclasses.get_fields(obj)`)

Like [dataclassy](https://github.com/biqqles/dataclassy) but:
- Uses `metaclass` and simple inheritance over monkey-patched generated code

Simpler than [attrs](https://github.com/python-attrs/attrs) and [pydantic](https://github.com/samuelcolvin/pydantic).

Note: there are [perfectly valid reasons](https://peps.python.org/pep-0557/#rationale) for why the Python community
decided to use generated code over simple inheritance--`baseclasses` is just an alternative that 
implements things differently.

## TODO

- [ ] Add `str` property to field (which `dataclasses` doesn't have)
- [ ] Add `compare` property to field (to mirror `dataclasses`)
- [ ] Add `init` property to field (to mirror `dataclasses`)
- [ ] Expose `obj.replace(**kwargs)` (to mirror `dataclasses`)
- [ ] Consider `serialize` property to field
- [ ] Integrate better with `ipython`
- [ ] Add `InternalStateField` with better defaults for internals
- [ ] Take advantage of [PEP 681 included in Python 3.11](https://docs.python.org/3/whatsnew/3.11.html#whatsnew311-pep681)
