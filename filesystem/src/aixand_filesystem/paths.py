"""Pinned Windows traversal, extracted from aixand-platform's project-path reader."""

import ctypes
import errno
import os
from collections.abc import Sequence
from ctypes import wintypes
from os import PathLike
from pathlib import Path
from typing import BinaryIO

from ._windows import kernel, native_path


class PinnedPath:
    """Open an existing Windows path while preventing ancestor replacement.

    Every ancestor and the leaf are opened without FILE_SHARE_DELETE, with
    OPEN_REPARSE_POINT, and checked before traversal. Linked/reparse paths are
    rejected. ``parts`` contains single relative components within ``root``.
    This is read access, not a general-purpose secure-write API or ACL helper.
    It is not reentrant; the context must remain open while paths are used.
    """

    def __init__(
        self,
        root: str | PathLike,
        parts: Sequence[str] = (),
        *,
        directory: bool = False,
    ):
        if isinstance(parts, (str, bytes)):
            raise PermissionError("Expected relative path components")
        parts = tuple(parts)
        if any(
            not isinstance(part, str)
            or not part
            or part in (".", "..")
            or any(c in part for c in ("/", "\\", ":", "\0"))
            or part.rstrip(" .") != part
            for part in parts
        ):
            raise PermissionError("Expected relative path components")
        self.path = Path(root).absolute().joinpath(*parts)
        self.directory = directory
        self.file: BinaryIO | None = None
        self.handles = []
        self._active = False
        self._kernel = None

    def __enter__(self):
        if os.name != "nt":
            raise OSError(errno.ENOTSUP, "PinnedPath requires Windows")
        if self._active:
            raise RuntimeError("PinnedPath is not reentrant")
        import msvcrt

        self._kernel = kernel()
        self._active = True
        self.file = None
        parts = self.path.parts
        try:
            value = str(self.path)
            extended = value[4:] if value.startswith("\\\\?\\") else None
            ordinary_extended = (
                extended is None
                or extended.startswith("UNC\\")
                or (
                    len(extended) >= 3
                    and extended[0].isascii()
                    and extended[0].isalpha()
                    and extended[1:3] == ":\\"
                )
            )
            if value.startswith("\\\\.\\") or not ordinary_extended:
                raise PermissionError("Device paths cannot be opened")
            for index in range(len(parts)):
                current = Path(*parts[: index + 1])
                if index and (
                    ":" in parts[index]
                    or parts[index] in (".", "..")
                    or parts[index].rstrip(" .") != parts[index]
                ):
                    raise PermissionError("Invalid Windows path")
                handle = self._kernel.CreateFileW(
                    native_path(str(current)),
                    0x80000000,
                    3,
                    None,
                    3,
                    0x02000000 | 0x00200000,
                    None,
                )
                if handle == wintypes.HANDLE(-1).value:
                    raise ctypes.WinError(ctypes.get_last_error())
                self.handles.append(handle)
                info = ctypes.create_string_buffer(52)
                if not self._kernel.GetFileInformationByHandle(handle, info):
                    raise ctypes.WinError(ctypes.get_last_error())
                attributes = ctypes.cast(info, ctypes.POINTER(wintypes.DWORD))[0]
                if attributes & 0x400:
                    raise PermissionError("Linked paths cannot be opened")
                if index < len(parts) - 1 or self.directory:
                    if not attributes & 0x10:
                        raise NotADirectoryError(str(current))
            if not self.directory:
                handle = self.handles[-1]
                descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
                self.handles.pop()  # The descriptor now owns the native handle.
                try:
                    self.file = os.fdopen(descriptor, "rb")
                except BaseException:
                    os.close(descriptor)
                    raise
            return self
        except BaseException:
            self.__exit__()
            raise

    def __exit__(self, *_):
        try:
            if self.file is not None:
                self.file.close()
        finally:
            for handle in reversed(self.handles):
                self._kernel.CloseHandle(handle)
            self.handles.clear()
            self._active = False
