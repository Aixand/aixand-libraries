# Local runtime public API

Import core APIs from `aixand_local_runtime`. Python 3.11+ is required.

| API | Result and contract |
| --- | --- |
| `await start_local_server(callback, path=None, *, limit=65536)` | Starts a listener; pass an explicit application-owned path for portable use. Async callback receives `(reader, writer)`. Returns an asyncio server on POSIX or `LocalServer` on Windows. |
| `await open_local_connection(path, *, limit=65536)` | Returns `(StreamReader, StreamWriter)`, authenticating on Windows. Caller closes the writer. |
| `connect_local(path, *, timeout=30)` | Returns a connected synchronous socket; caller closes it. Timeout applies to socket operations. |
| `endpoint_exists(path)` | Boolean discovery check: Unix socket existence on POSIX; validated descriptor on Windows. Races remain possible. |
| `endpoint(path)` | Reads a JSON descriptor (at most 4096 bytes), validates `aixand.local/1`, integer port and 64-character token; returns a mapping. Verifies private access on Windows. Not a POSIX socket reader. |
| `LocalServer` | Windows listener wrapper with `close()`, async `wait_closed()`, `.sockets`, and async context management. Close removes a matching owned descriptor; does not drain application handlers. Normally obtained from a server factory. |
| `process_start(pid)` | Opaque birth token or `None` for exited, invalid, or unidentifiable processes. Compare only for the same PID and host. |
| `install_signals(callback)` | Returns `None`; installs SIGTERM/SIGINT handlers (also SIGBREAK on Windows) on the running asyncio loop. Callback takes no arguments. Call from the main thread. |
| `WINDOWS` | Boolean indicating the platform's Windows transport selection. |

Connection and filesystem failures raise OS exceptions; invalid endpoint descriptors
may raise `ValueError`. Async operations may be cancelled. The Windows raw IPC
server gives authentication five seconds and suppresses authentication/connection
errors handled by its wrapper. Applications remain responsible for callback errors,
framing, deadlines, and connected-client cleanup.

## Optional WebSocket module

Install the `[websocket]` extra and import from `aixand_local_runtime.websocket`:

- `connect(path, **kwargs)` returns a WebSocket client connector used with `async with`.
- `await serve(callback, path, **kwargs)` returns an async-context-managed listener;
  callback receives a WebSocket connection.

Missing optional dependencies raise `ImportError` when used. Connection/protocol
errors also follow the installed WebSocket implementation. Windows reserves its
bearer authentication and proxy settings. See [usage](usage.md#optional-websockets).

[Core exports](../src/aixand_local_runtime/__init__.py) · [Usage](usage.md)
