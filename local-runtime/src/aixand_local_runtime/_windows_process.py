"""Windows process-birth identities; no filesystem policy."""

import ctypes as c
from ctypes import wintypes as w

kernel = c.WinDLL("kernel32", use_last_error=True)
kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
kernel.OpenProcess.restype = w.HANDLE
kernel.CloseHandle.argtypes = [w.HANDLE]
kernel.GetProcessTimes.argtypes = [w.HANDLE, *([c.POINTER(w.FILETIME)] * 4)]
kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]


def _check(result):
    if not result:
        raise c.WinError(c.get_last_error())
    return result


def process_start(pid):
    handle = kernel.OpenProcess(0x100000 | 0x1000, False, int(pid))
    if not handle:
        return None
    try:
        if kernel.WaitForSingleObject(handle, 0) != 258:
            return None
        values = [w.FILETIME() for _ in range(4)]
        _check(kernel.GetProcessTimes(handle, *[c.byref(value) for value in values]))
        return str(values[0].dwLowDateTime | values[0].dwHighDateTime << 32)
    finally:
        kernel.CloseHandle(handle)
