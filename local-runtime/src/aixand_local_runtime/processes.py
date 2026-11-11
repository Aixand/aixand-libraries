"""Opaque process-birth identities on the current host."""

import os
import sys
from pathlib import Path

WINDOWS = os.name == "nt"


def process_start(pid):
    """Return an opaque process-birth identity, or None when not identifiable.

    Compare tokens only for the same PID on the same host. A zombie or exited
    process has no live identity. Never use a PID alone to authorize a signal.
    """
    try:
        pid = int(pid)
    except (TypeError, ValueError, OverflowError):
        return None
    if not 0 < pid <= 2147483647:
        return None
    if WINDOWS:
        from ._windows_process import process_start as query

        return query(pid)
    if sys.platform == "darwin":
        from ._macos_process import process_start as query

        return query(pid)
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return None if fields[0] == "Z" else fields[19]
    except (OSError, IndexError):
        return None
