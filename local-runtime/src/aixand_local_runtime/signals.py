"""Install shutdown callbacks on the current asyncio event loop."""

import asyncio
import os

WINDOWS = os.name == "nt"


def install_signals(callback):
    import signal

    loop = asyncio.get_running_loop()
    numbers = (
        (signal.SIGTERM, signal.SIGINT, signal.SIGBREAK)
        if WINDOWS
        else (signal.SIGTERM, signal.SIGINT)
    )
    for number in numbers:
        if WINDOWS:
            signal.signal(number, lambda *_: loop.call_soon_threadsafe(callback))
        else:
            loop.add_signal_handler(number, callback)
