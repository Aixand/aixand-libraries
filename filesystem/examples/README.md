# Integration starters

Install this package and its declared dependencies into the consuming environment
first; see the [overview](../README.md). From this package directory run:

```sh
python examples/locked_counter.py
```

Prints `1`; temporary lock and counter files are removed. Adapt the state path and recovery policy for persistent use.

These scripts are copyable starting points. Applications choose persistent paths,
protocols, deadlines, error reporting, and lifecycle policy. They do not depend on
repository-relative imports. For source development, use `../.venv/bin/python`
only when invoking from inside this examples directory, or `.venv/bin/python`
from the package directory (Windows: `.venv\Scripts\python.exe`).

[Usage guide](../docs/usage.md) · [API reference](../docs/api.md)
