"""Top-level package for the demo's deliberately-broken sample project.

A real project's root `__init__.py` is the one place allowed to expose
inherited state to its sub-packages (the environment-layer channel). The
business module `gadget.py` reaches back UP into this package — the
violation `make demo` demonstrates.
"""

VERSION = "0.1.0"
