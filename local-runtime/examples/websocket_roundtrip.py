"""Requires the websocket extra; echoes one message with temporary state."""
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from aixand_filesystem import private_directory
from aixand_local_runtime.websocket import connect, serve


async def main():
    finished = asyncio.Event()

    async def echo(connection):
        try:
            await connection.send(await connection.recv())
        finally:
            finished.set()

    with TemporaryDirectory(prefix="ax-ws-") as temporary:
        path = private_directory(Path(temporary) / "run") / "echo"
        server = await serve(echo, path)
        try:
            async with server:
                async with asyncio.timeout(5):
                    async with connect(path) as connection:
                        await connection.send("hello")
                        print(await connection.recv())
                    await finished.wait()
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
