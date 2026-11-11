"""Local communication and process lifecycle utilities."""

from .ipc import (
    WINDOWS,
    LocalServer,
    connect_local,
    endpoint,
    endpoint_exists,
    open_local_connection,
    start_local_server,
)
from .processes import process_start
from .signals import install_signals

__all__ = [
    "WINDOWS",
    "LocalServer",
    "connect_local",
    "endpoint",
    "endpoint_exists",
    "open_local_connection",
    "start_local_server",
    "process_start",
    "install_signals",
]
