"""A business module that commits the upward-import violation on purpose.

arch-coherence/PYTHON.md §1: a business module (anything that is not
`__init__.py` / `__main__.py`) must NOT reach up into the top-level of its
own root package. The line below does exactly that — `from widgets import
VERSION` — so `check_upward_imports.py` flags it. A conforming module would
receive inherited state through its own package's `__init__.py` instead.
"""

from widgets import VERSION  # <- upward import: the intentional violation


def describe() -> str:
    return f"gadget v{VERSION}"
