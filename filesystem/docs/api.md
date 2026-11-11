# Filesystem public API

Import these functions from `aixand_filesystem`. Python 3.11+ is required.

| API | Result and contract |
| --- | --- |
| `lock_file(stream, *, blocking=False, shared=False)` | Returns `None`; acquires an advisory lock on an open stream. Nonblocking contention raises `BlockingIOError`. POSIX shared mode permits readers; Windows always locks byte zero exclusively. |
| `unlock_file(stream)` | Returns `None`; releases the lock, leaving the stream open. |
| `file_lock(stream, *, blocking=True)` | Context manager yielding the stream; releases its exclusive lock in `finally`, leaving the stream open. |
| `private_directory(path)` | Creates parents, rejects a linked/junction leaf, protects the directory, returns a `Path`. May change existing permissions. |
| `private_path(path)` | Protects an existing application-owned file/directory; returns `None`. |
| `secure_file(stream)` | Protects an open file by handle; returns `None`. |
| `verify_private(path)` | Returns `None` on successful ownership/access verification; otherwise raises `PermissionError` or an OS error. |
| `is_private(stat_result)` | POSIX ownership/mode check returning `bool`; Windows returns `True` without ACL verification. Use `verify_private` for Windows. |
| `current_user_sid()` | Windows SID string; other platforms raise `OSError(ENOTSUP)`. |
| `PinnedPath(root, parts=(), *, directory=False)` | Windows context manager. `parts` is a sequence of single relative components; invalid components raise `PermissionError`. Entering returns the instance with `.path` and, for files, binary `.file`. Exit closes retained handles. |

OS failures propagate unless described otherwise. `PinnedPath` rejects reparse
points, is not reentrant, and raises `OSError(ENOTSUP)` when entered outside Windows.
Its handles prevent ancestor replacement, not concurrent writes to file content.

## Windows authentication module

Import `aixand_filesystem.auth_directory` explicitly. `create(path)` and
`check(path)` operate on private authentication directories; `secure_file(path)`
protects a regular file within a verified private directory. These are Windows-only
operations. This module's path-based `secure_file` differs from the package root's
stream-based function. See [usage and CLI commands](../README.md#windows-authentication-storage).

[Usage](usage.md) · [Implementation](../src/aixand_filesystem/__init__.py)
