# Use filesystem primitives

Requires Python 3.11+. Install `aixand-lib-filesystem` into the consuming environment:

```sh
python -m pip install aixand-lib-filesystem
python examples/locked_counter.py
```

Run the example from the package directory after installation. It creates a private
temporary directory, increments a counter under a separate lock, prints `1`, and
removes its state. Copy the [starter](../examples/locked_counter.py) into your
application and choose a persistent application-owned directory when needed.

## Coordinate an update

All writers must open the same stable lock file and hold `file_lock(stream)` across
the read, comparison, and publication. Keep the lock file separate from data files
that are replaced. Never unlink or replace a live lock file: another process could
acquire a different inode and enter the same transaction. Locks are advisory,
non-reentrant, and are not a distributed locking protocol.

Use `lock_file(stream, blocking=False)` when the application should handle contention
rather than wait. Catch `BlockingIOError` and decide whether to retry or report busy.
Unexpected OS errors propagate. Closing a stream releases its lock; the context
manager releases the lock on exceptions but leaves the stream open.

The starter uses replacement for publication but does not implement crash durability
or fsync. Applications own recovery, validation, transaction boundaries, and storage
policy. Its paths are safe only within the application-owned temporary directory.

## Protect state

Create an application-owned directory with `private_directory(path)` and protect
open files with `secure_file(stream)`. Verify existing storage with
`verify_private(path)`; it raises `PermissionError` for unacceptable permissions.
Other filesystem failures can raise `OSError`. These helpers do not validate every
ancestor or provide a general safe-write API. POSIX permissions use 0700/0600;
Windows uses current-account DACLs. `is_private(stat_result)` does not verify
Windows ACLs.

## Windows traversal and authentication directories

Use `PinnedPath(root, parts)` as a context manager when reading an existing Windows
path while preventing ancestor replacement. Keep the context open while accessing
`selected.file` or `selected.path`. Reparse points are rejected; file contents may
still change. Entering the context on POSIX raises `OSError(ENOTSUP)`.
See the [overview](../README.md#windows-pinned-paths) for a snippet and
[authentication storage](../README.md#windows-authentication-storage) for the
Windows-only directory commands. Native Windows guarantees require Windows tests.

[API reference](api.md) · [Examples](../examples/README.md)
