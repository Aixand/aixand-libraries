# Local runtime utilities

Independently installable Python 3.11+ package: `aixand-lib-local-runtime`, import
`aixand_local_runtime`. It depends on `aixand-lib-filesystem`, with no application service or external repository requirements. The optional `[websocket]` extra
installs `websockets>=15,<18`; core IPC uses only the standard library and OS APIs.

- `ipc`: synchronous and asynchronous local connections and servers, endpoint
  discovery, and Windows endpoint authentication.
- `websocket`: local WebSocket client/server adapters.
- `processes`: opaque process-birth identities for checking the same PID on the
  same host; exited/unidentifiable processes return `None`.
- `signals`: shutdown callbacks for the current asyncio loop.

The package root exports the IPC, process identity, and signal APIs. Filesystem
operations are imported directly from `aixand_filesystem`; they are not duplicated
or re-exported here. Product configuration and provider behavior belong to callers.

POSIX uses Unix sockets. Windows uses loopback and protected endpoint descriptors
with the `aixand.local/1` schema and a fresh per-endpoint capability.
Applications own endpoint placement and lifecycle policy.

From this directory:

```sh
python -m pip install -e ../filesystem -e '.[websocket]'
python -m unittest discover -s tests -v
python -m pip wheel --no-deps .
```

Native Windows and macOS behavior requires verification on those platforms.

## Local developer commands

Inside the aixand-libraries source checkout, run from this directory with
Python 3.11+ and uv:

```sh
./dev.sh develop --local
./dev.sh check
./dev.sh test
./dev.sh build
```

Use `.\dev.ps1` on Windows. Each package owns its development environment and
helper. Commands run within this package. See the
[development guide](docs/development.md) for wheel-based setup without sibling
sources, lock updates, and build outputs.

## Documentation and support

See the [documentation index](docs/README.md) for usage, API reference, and runnable
starter examples. Report ordinary problems through the integrating product's
support channel or issue tracker. External contributions are not currently
accepted due to limited maintainer capacity; see [reporting guidance](../docs/reporting.md).
Report vulnerabilities [privately](../SECURITY.md).
