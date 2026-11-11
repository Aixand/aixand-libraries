"""One-process client/server starter; prints hello and cleans up."""
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from aixand_filesystem import private_directory
from aixand_local_runtime import open_local_connection, start_local_server


async def main():
    finished = asyncio.Event()

    async def echo(reader, writer):
        try:
            async with asyncio.timeout(5):
                message = await reader.readline()
                writer.write(message)
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()
            finished.set()

    with TemporaryDirectory(prefix="ax-ipc-") as temporary:
        path = private_directory(Path(temporary) / "run") / "echo"
        server = await start_local_server(echo, path)
        try:
            async with server:
                async with asyncio.timeout(5):
                    reader, writer = await open_local_connection(path)
                    try:
                        writer.write(b"hello\n")
                        await writer.drain()
                        print((await reader.readline()).decode().strip())
                    finally:
                        writer.close()
                        await writer.wait_closed()
                    await finished.wait()
        finally:
            # POSIX socket cleanup belongs to this application-owned directory.
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
