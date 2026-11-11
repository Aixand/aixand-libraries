# Use local runtime utilities

Install into a Python 3.11+ environment:

```sh
python -m pip install aixand-lib-local-runtime
python examples/ipc_roundtrip.py
python examples/shutdown.py
```

Run from the package directory. The IPC starter prints `hello` and exits. The
shutdown starter waits until you press Ctrl+C. See [examples](../examples/README.md).

## Connect a client and server

The [roundtrip starter](../examples/ipc_roundtrip.py) runs both sides in one process
so it is easy to execute. For separate processes, give both the same application-owned
endpoint path. Create a private parent directory before starting the server.
`start_local_server(callback, path)` calls an async callback with a stream reader
and writer. `open_local_connection(path)` returns that pair to the client.
The application defines framing; the starter uses one newline-terminated message.
Set read limits and deadlines appropriate to your protocol and close each writer
with `close()` followed by `await wait_closed()`.

The server is an async context manager; leaving it closes the listener. Existing
connections and handler tasks remain the application's responsibility. The starter
waits for its handler before exiting. POSIX uses a Unix socket; the application
owns cleanup of its socket path. Remove only an endpoint owned by this server,
not an arbitrary stale-looking endpoint another process might be using.
Windows uses authenticated loopback with a private descriptor; `LocalServer.close()`
removes the descriptor only if its token still matches.

Handle `OSError` for missing endpoints, permissions, or connection failures;
Windows descriptor validation may raise `ValueError`. Apply application deadlines
with `asyncio.timeout`. Discovery with `endpoint_exists` is only a point-in-time
observation, not a connection or identity guarantee.

## Shutdown and process identity

Call `install_signals(stopped.set)` from the main thread inside the running asyncio
loop. Wait on the event, then close listeners and drain application work. The helper
installs handlers and provides no restoration API; applications own signal policy.
`process_start(pid)` returns an opaque birth identity or `None`. Compare identities
only for the same PID on the same host; unavailable identity must not be treated
as proof that a process is still the original process. A PID alone is insufficient
authorization to signal a process.

## Optional WebSockets

Install `aixand-lib-local-runtime[websocket]` and import
`connect` and `serve` from `aixand_local_runtime.websocket`:

```sh
python examples/websocket_roundtrip.py
```

The [WebSocket starter](../examples/websocket_roundtrip.py) prints `hello` and
cleans up its temporary endpoint. Its server callback echoes one message and exits.

POSIX uses Unix WebSockets; Windows uses a descriptor and bearer-authenticated
loopback. Windows adapters own authentication headers, proxy selection, and the
server's request authentication hook; do not override those keyword arguments.
Other keyword arguments pass through to the WebSocket implementation. Listener,
connection, and endpoint lifecycle still belong to the application. Native Windows
and macOS behavior requires verification on those platforms.

[API reference](api.md)
