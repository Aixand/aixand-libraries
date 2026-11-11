"""macOS process-birth identities using the native libproc interface."""

import ctypes
from functools import cache


class _ProcessInfo(ctypes.Structure):
    # Public proc_bsdinfo ABI, including the microsecond process start time:
    # https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/proc_info.h
    _fields_ = (
        [
            (name, ctypes.c_uint32)
            for name in (
                "flags",
                "status",
                "exit_status",
                "pid",
                "parent_pid",
                "uid",
                "gid",
                "real_uid",
                "real_gid",
                "saved_uid",
                "saved_gid",
                "reserved",
            )
        ]
        + [
            ("command", ctypes.c_char * 16),
            ("name", ctypes.c_char * 32),
        ]
        + [
            (name, ctypes.c_uint32)
            for name in ("files", "group", "job_count", "terminal", "terminal_group")
        ]
        + [
            ("nice", ctypes.c_int32),
            ("start_seconds", ctypes.c_uint64),
            ("start_microseconds", ctypes.c_uint64),
        ]
    )


@cache
def _query():
    library = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
    query = library.proc_pidinfo
    query.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint64,
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    query.restype = ctypes.c_int
    return query


def process_start(pid):
    info = _ProcessInfo()
    try:
        size = _query()(pid, 3, 0, ctypes.byref(info), ctypes.sizeof(info))
    except OSError:
        return None
    if size != ctypes.sizeof(info) or info.pid != pid or info.status == 5:
        return None
    return f"{info.start_seconds}:{info.start_microseconds}"
