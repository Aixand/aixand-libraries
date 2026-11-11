"""Private files and directories. Callers own paths and publication policy."""

import os
from pathlib import Path


def private_path(path):
    """Protect a new application-owned file/directory, including on Windows."""
    path = Path(path)
    if os.name != "nt":
        path.chmod(0o700 if path.is_dir() else 0o600)
        return
    from ._permissions_windows import protect

    protect(path)


def private_directory(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400:
        raise PermissionError("A private state directory cannot be a link or junction")
    private_path(path)
    return path


def is_private(info):
    # Windows permissions are represented by DACLs, not st_mode's POSIX bits.
    return os.name == "nt" or not (info.st_mode & 0o077 or info.st_uid != os.getuid())


def verify_private(path):
    """Verify current-account ownership and private access, including Windows ACLs."""
    if os.name == "nt":
        from ._permissions_windows import verify_private as verify

        verify(path)
    elif not is_private(Path(path).stat()):
        raise PermissionError("Path must belong to the current account and be private")


def secure_file(stream):
    """Protect an open file by handle, even if its parent path is renamed."""
    if os.name == "nt":
        from ._permissions_windows import secure_file as protect

        protect(stream)
    else:
        os.fchmod(stream.fileno(), 0o600)


def current_user_sid():
    """Return the current Windows account SID; other systems are unsupported."""
    if os.name != "nt":
        import errno

        raise OSError(errno.ENOTSUP, "Windows account identity requires Windows")
    from ._permissions_windows import sid

    return sid()
