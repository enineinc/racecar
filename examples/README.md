# examples/: the racecar demo project

This directory is a tiny, **deliberately broken** sample project. It exists for
one purpose: `make demo` runs a racecar check against it and shows the check
catching a real architectural violation: the "see the value in one command"
moment.

**The breakage is intentional. Do not fix it.** If the violation disappears,
the demo no longer demonstrates anything.

## What's here

A minimal Shape `src` project named `widgets`:

```
examples/
  pyproject.toml          # declares [tool.importlinter].root_package = "widgets"
  src/widgets/
    __init__.py           # the root package (allowed to hold inherited state)
    gadget.py             # a business module that commits the violation
```

## The intentional violation

`src/widgets/gadget.py` contains:

```python
from widgets import VERSION
```

That is an **upward import**: a business module reaching back up into the
top-level of its own root package. The rule (arch-coherence/PYTHON.md §1) is
that only `__init__.py` / `__main__.py` may do this: the environment-layer
channel. A conforming business module receives inherited state through its own
package's `__init__.py`, never by importing the root directly.

`scripts/check_upward_imports.py` detects exactly this pattern and exits
non-zero. `make demo` runs it, captures that non-zero exit, and reports it as a
success: the check did its job.

## Run it

From the repo root:

```
make demo
```
