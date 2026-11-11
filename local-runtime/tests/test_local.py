import asyncio
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

if os.environ.get("AIXAND_PLATFORM_REQUIRE_WEBSOCKET") == "1":
    import websockets  # noqa: F401

from aixand_local_runtime import (
    WINDOWS,
    connect_local,
    endpoint,
    open_local_connection,
    start_local_server,
)
from aixand_filesystem import lock_file, private_directory


class LocalTransport(unittest.IsolatedAsyncioTestCase):
    @unittest.skipUnless(
        importlib.util.find_spec("websockets"),
        "Optional WebSocket transport dependency",
    )
    async def test_authenticated_websocket_and_endpoint_cleanup(self):
        from aixand_local_runtime.websocket import connect, serve

        with tempfile.TemporaryDirectory(prefix="aixand-ws-") as temporary:
            path = Path(temporary) / "endpoint.sock"

            async def echo(channel):
                async for value in channel:
                    await channel.send(value)

            server = await serve(echo, path, compression=None)
            try:
                if WINDOWS:
                    from websockets.asyncio.client import connect as tcp_connect
                    from websockets.exceptions import InvalidStatus

                    value = endpoint(path)
                    with self.assertRaises(InvalidStatus) as rejected:
                        async with tcp_connect(
                            f"ws://127.0.0.1:{value['port']}", proxy=None
                        ):
                            pass
                    self.assertEqual(rejected.exception.response.status_code, 401)
                async with connect(path, compression=None) as channel:
                    await channel.send("authenticated ✓")
                    self.assertEqual(await channel.recv(), "authenticated ✓")
            finally:
                server.close()
                await server.wait_closed()
            if WINDOWS:
                self.assertFalse(path.exists())

    async def test_multiple_clients_authentication_and_bounded_frames(self):
        with tempfile.TemporaryDirectory(prefix="aixand-local-test-") as temporary:
            path = Path(temporary) / "endpoint.sock"
            received = []

            async def echo(reader, writer):
                value = json.loads(await reader.readline())
                received.append(value)
                writer.write(json.dumps(value).encode() + b"\n")
                await writer.drain()
                writer.close()
                await writer.wait_closed()

            server = await start_local_server(echo, path=path)
            try:
                if WINDOWS:
                    value = endpoint(path)
                    reader, writer = await asyncio.open_connection(
                        "127.0.0.1", value["port"]
                    )
                    writer.write(b'{"token":"wrong"}\n{"private":"untrusted"}\n')
                    await writer.drain()
                    self.assertEqual(await asyncio.wait_for(reader.read(), 3), b"")
                    writer.close()
                    await writer.wait_closed()
                    self.assertEqual(received, [])
                for value in [{"message": "first ✓"}, {"message": "second"}]:
                    reader, writer = await open_local_connection(path)
                    writer.write(json.dumps(value).encode() + b"\n")
                    await writer.drain()
                    self.assertEqual(
                        json.loads(await asyncio.wait_for(reader.readline(), 3)), value
                    )
                    writer.close()
                    await writer.wait_closed()

                def sync_request():
                    with connect_local(path) as channel:
                        channel.sendall(b'{"sync":true}\n')
                        return json.loads(channel.makefile("rb").readline())

                self.assertEqual(await asyncio.to_thread(sync_request), {"sync": True})
                self.assertEqual(len(received), 3)
            finally:
                server.close()
                await server.wait_closed()


class Ownership(unittest.TestCase):
    def test_exclusive_lock_and_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "owner.lock"
            with path.open("a+") as first, path.open("a+") as second:
                lock_file(first)
                with self.assertRaises(BlockingIOError):
                    lock_file(second)
                first.close()
                lock_file(second)

    @unittest.skipUnless(WINDOWS, "Windows ACLs and handles")
    def test_windows_private_descriptor_and_process_identity(self):
        from aixand_filesystem import private_path
        from aixand_local_runtime import process_start
        from aixand_filesystem import verify_private

        with tempfile.TemporaryDirectory() as temporary:
            directory = private_directory(Path(temporary) / "private")
            path = directory / "endpoint.json"
            path.write_text("{}")
            private_path(path)
            verify_private(path)
            self.assertIsNotNone(process_start(os.getpid()))
            self.assertIsNone(process_start(4294967295))

    @unittest.skipUnless(WINDOWS, "Windows pinned project files")
    def test_windows_pinned_project_file(self):
        from aixand_filesystem import PinnedPath

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            (path / "nested").mkdir()
            (path / "nested/file.txt").write_text("pinned")
            with PinnedPath(path, ["nested", "file.txt"]) as selected:
                self.assertEqual(selected.file.read(), b"pinned")
                with self.assertRaises(OSError):
                    (path / "nested").rename(path / "moved")


if __name__ == "__main__":
    unittest.main()
