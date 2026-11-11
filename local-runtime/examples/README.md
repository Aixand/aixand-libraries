# Integration starters

Install this package and its declared dependencies into the consuming environment
first; see the [overview](../README.md). From this package directory run:

```sh
python examples/ipc_roundtrip.py
python examples/shutdown.py
```

The roundtrip prints `hello` and exits. The shutdown example waits for Ctrl+C and prints a shutdown message. Both need a main thread with an asyncio loop; the IPC example removes its temporary endpoint.

For the optional WebSocket adapter, install
`aixand-lib-local-runtime[websocket]`, then run
`python examples/websocket_roundtrip.py`. It prints `hello` and removes temporary
endpoint state.

These scripts are copyable starting points. Applications choose persistent paths,
protocols, deadlines, error reporting, and lifecycle policy. They do not depend on
repository-relative imports. For source development, use `../.venv/bin/python`
only when invoking from inside this examples directory, or `.venv/bin/python`
from the package directory (Windows: `.venv\Scripts\python.exe`).

[Usage guide](../docs/usage.md) · [API reference](../docs/api.md)
