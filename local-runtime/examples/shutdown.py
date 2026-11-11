"""Run interactively; press Ctrl+C to request a graceful shutdown."""
import asyncio
import os
from aixand_local_runtime import install_signals, process_start


async def main():
    stopped = asyncio.Event()
    install_signals(stopped.set)
    print(f"PID {os.getpid()}, birth identity {process_start(os.getpid())}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    await stopped.wait()
    print("Shutdown requested; close application resources here.")


if __name__ == "__main__":
    asyncio.run(main())
