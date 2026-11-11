"""Lazy Windows kernel bindings; no ACL, networking, or process APIs."""

import ctypes
from ctypes import wintypes
from functools import cache


@cache
def kernel():
    library = ctypes.WinDLL("kernel32", use_last_error=True)
    library.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    library.CreateFileW.restype = wintypes.HANDLE
    library.GetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    library.GetFileInformationByHandle.restype = wintypes.BOOL
    library.CloseHandle.argtypes = [wintypes.HANDLE]
    library.CloseHandle.restype = wintypes.BOOL
    return library


def native_path(value: str) -> str:
    if value.startswith("\\\\?\\"):
        return value
    if value.startswith("\\\\"):
        return "\\\\?\\UNC\\" + value[2:]
    return "\\\\?\\" + value
