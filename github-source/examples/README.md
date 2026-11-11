# Integration starters

Install this package and its declared dependencies into the consuming environment
first; see the [overview](../README.md). From this package directory run:

```sh
python examples/fetch_snapshot.py --help
python examples/fetch_snapshot.py https://github.com/Aixand/undercurrent --ref main --path README.md
```

The fetch command uses the network and prints snapshot metadata without writing downloaded files. Anonymous GitHub rate limits apply; `--help` works offline.

These scripts are copyable starting points. Applications choose persistent paths,
protocols, deadlines, error reporting, and lifecycle policy. They do not depend on
repository-relative imports. For source development, use `../.venv/bin/python`
only when invoking from inside this examples directory, or `.venv/bin/python`
from the package directory (Windows: `.venv\Scripts\python.exe`).

[Usage guide](../docs/usage.md) · [API reference](../docs/api.md)
