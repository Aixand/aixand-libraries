"""Windows authentication directories with private creation and ACL checks."""

import ctypes as c
from ctypes import wintypes as w
from pathlib import Path
import stat

from .paths import PinnedPath
from .permissions import verify_private


class SecurityAttributes(c.Structure):
    _fields_ = [("length", w.DWORD), ("descriptor", c.c_void_p), ("inherit", w.BOOL)]


def check(directory):
    """Check directory permissions without changing them."""
    with PinnedPath(directory, [], directory=True):
        verify_private(directory)


def create(directory):
    """Create a private directory or check an existing directory."""
    from ._permissions_windows import kernel, security, sid

    kernel.CreateDirectoryW.argtypes = [w.LPCWSTR, c.POINTER(SecurityAttributes)]
    directory = Path(directory).absolute()
    if directory.exists():
        return check(directory)
    if not directory.parent.exists():
        create(directory.parent)
    with PinnedPath(directory.parent, [], directory=True):
        descriptor = c.c_void_p()
        account = sid()
        if not security.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            f"O:{account}D:P(A;OICI;FA;;;{account})", 1, c.byref(descriptor), None
        ):
            raise c.WinError(c.get_last_error())
        try:
            attributes = SecurityAttributes(
                c.sizeof(SecurityAttributes), descriptor, False
            )
            if not kernel.CreateDirectoryW(str(directory), c.byref(attributes)):
                error = c.get_last_error()
                if error != 183:
                    raise c.WinError(error)
        finally:
            kernel.LocalFree(descriptor)
        check(directory)


def secure_file(path):
    """Protect a regular file inside a verified private directory."""
    from ._permissions_windows import protect

    path = Path(path).absolute()
    with PinnedPath(path.parent, [], directory=True):
        verify_private(path.parent)
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_file_attributes & 0x400:
            raise PermissionError(
                "Authentication storage must be a regular private file"
            )
        protect(path)
        verify_private(path)


def main():
    import argparse
    import os

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "check", "secure-file"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Authentication directory commands require Windows")
    {"create": create, "check": check, "secure-file": secure_file}[args.action](
        args.path
    )


if __name__ == "__main__":
    main()
