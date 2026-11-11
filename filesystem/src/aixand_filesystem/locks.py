"""Advisory file locks. Callers own paths, streams, and store policy."""

import errno
import os
import time
from contextlib import contextmanager
from typing import IO


def lock_file(stream: IO, *, blocking: bool = False, shared: bool = False) -> None:
    """Lock the open stream until unlock_file() or close.

    Windows participants lock byte zero; POSIX participants use flock. Existing
    lock files and the historical aixand-platform protocol remain compatible.
    Shared locks coexist on POSIX; Windows retains exclusive locking in both modes.
    """
    if os.name != "nt":
        import fcntl

        fcntl.flock(
            stream,
            (fcntl.LOCK_SH if shared else fcntl.LOCK_EX)
            | (0 if blocking else fcntl.LOCK_NB),
        )
        return
    import msvcrt

    stream.seek(0, 2)
    if not stream.tell():
        stream.write(b"\0" if "b" in stream.mode else "\0")
        stream.flush()
    stream.seek(0)
    while True:
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            return
        except OSError as error:
            if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                raise
            if not blocking:
                raise BlockingIOError(
                    errno.EAGAIN, "Local state is already owned"
                ) from error
            time.sleep(0.05)


def unlock_file(stream: IO) -> None:
    """Release a lock without closing the caller-owned stream."""
    if os.name == "nt":
        import msvcrt

        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(stream, fcntl.LOCK_UN)


@contextmanager
def file_lock(stream: IO, *, blocking: bool = True):
    """Acquire and release an exclusive lock; leave the stream open."""
    lock_file(stream, blocking=blocking)
    try:
        yield stream
    finally:
        unlock_file(stream)
