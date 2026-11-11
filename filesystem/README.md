# Filesystem primitives

Independently installable Python 3.11+ library: `aixand-lib-filesystem`, import
`aixand_filesystem`. No runtime dependencies, services, network,
process management, or repository-layout assumptions.

It owns shared file locks, private file/directory permissions, and Windows pinned
paths. Applications and other libraries can import its public API directly.

## File locks

```python
from aixand_filesystem import file_lock, lock_file, unlock_file

with open("state.lock", "a+b") as stream:
    with file_lock(stream):  # blocking=True by default
        # Read, compare the observed revision, and publish a guarded update here.
        pass

with open("state.lock", "a+b") as stream:
    lock_file(stream, blocking=False)  # Raises BlockingIOError on contention.
    try:
        pass
    finally:
        unlock_file(stream)
```

`lock_file(stream, blocking=False, shared=False)` acquires an exclusive lock.
`shared=True` uses a shared POSIX lock; Windows retains the exclusive byte-zero
protocol for both modes. Closing the stream
or calling `unlock_file(stream)` releases it. `file_lock(stream, blocking=True)`
releases in `finally` but leaves the caller-owned stream open. Locks are not
reentrant and do not coordinate writes by processes ignoring the protocol.

POSIX uses `fcntl.flock`. Windows initializes an empty file once, seeks to byte
zero, and uses `msvcrt.LK_NBLCK` over one byte. Blocking acquisition retries
contention every 50 ms instead of relying on LK_LOCK's finite retry period.
Unexpected OS errors propagate; contention becomes `BlockingIOError`.

Callers own lock-file placement, safe path opening, stream lifetime, permissions,
store identifiers, and transaction boundaries. During adoption, retain existing
lock files and range conventions: changing the filename or replacing its inode
can allow old and new processes to write concurrently. Windows and POSIX use
different native protocols; this is not a distributed/network-filesystem lock.

## Windows pinned paths

```python
from aixand_filesystem import PinnedPath

with PinnedPath(root, ["references", "guide.md"]) as selected:
    data = selected.file.read()  # Original binary bytes.

with PinnedPath(root, directory=True) as selected:
    directory = selected.path
    # Keep the context open while using the protected directory.
```

`root` is an existing caller-selected path; `parts` contains single relative path
components. Every ancestor and the leaf are opened with OPEN_REPARSE_POINT,
checked for reparse points, and held without FILE_SHARE_DELETE. Linked/junction
paths are rejected and ancestors cannot be renamed/replaced while held. Directory
handles close in reverse order; file descriptors own transferred leaf handles.
Exceptions release retained handles. Drive, UNC, and long-path forms are supported;
device namespace traversal and escaping components are rejected.

This is a Windows read/traversal primitive, not a general secure-write API. It
does not freeze file bytes, enforce private ACLs, or prevent allowed concurrent
content writes. Callers still validate regular files, size limits, containment,
content stability, and publication. Constructing/importing the API is safe on POSIX, where
entering a pinned-path context raises `OSError(ENOTSUP)`.

## Verification

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
python -m pip wheel --no-deps .
```

Tests cover real-process lock contention/release, process termination, exception
cleanup, Windows byte-zero/retry behavior using mocks, isolated import/use with
site packages disabled, and Windows kernel tests for pinning, junction rejection,
and handle cleanup. Real Windows tests are skipped outside Windows; Linux/mocked
checks do not establish full Windows runtime qualification.

## Private files and directories

`private_directory(path)` creates/protects a directory and rejects a linked or
junction leaf. `private_path(path)` protects an existing application-owned file
or directory. POSIX uses modes 0600/0700; Windows uses a protected DACL granting
the current account full access (with inheritance for path-based protection).
`verify_private(path)` verifies private ownership/access, including Windows ACLs.
`is_private(stat_result)` is a POSIX metadata check; on Windows it cannot validate
ACLs and callers needing that guarantee must use `verify_private`.

`secure_file(stream)` protects an already-open file by handle, avoiding a path
reopen race if its parent is renamed. POSIX uses `fchmod(0600)`; Windows reopens
the original OS handle to apply the current-account owner and protected DACL.
These helpers do not provide a general safe path traversal or atomic write API;
callers retain responsibility for path selection and publication.

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

## Windows authentication storage

`current_user_sid()` returns the current Windows account SID. Other systems
raise `OSError(ENOTSUP)`. Import this function from `aixand_filesystem`.

The `aixand_filesystem.auth_directory` module provides `create(path)`,
`check(path)`, and `secure_file(path)` on Windows. Creation verifies existing
directories without changing their permissions. File protection requires a
regular file inside a verified private directory. Pinned paths reject links
and junctions. This module's path function differs from the package's
`secure_file(stream)` function, which protects an open file handle.

After installing the package, run these commands in PowerShell. Replace the
example path with your authentication directory:

```powershell
python -m aixand_filesystem.auth_directory create C:\Users\you\private-auth
python -m aixand_filesystem.auth_directory check C:\Users\you\private-auth
```

`check` exits zero for a private directory. It reports an error for invalid
permissions or links. These commands require Windows. Linux checks do not
establish native Windows qualification.

## Documentation and support

See the [documentation index](docs/README.md) for usage, API reference, and runnable
starter examples. Report ordinary problems through the integrating product's
support channel or issue tracker. External contributions are not currently
accepted due to limited maintainer capacity; see [reporting guidance](../docs/reporting.md).
Report vulnerabilities [privately](../SECURITY.md).
