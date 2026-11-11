"""Local-only IPC: Unix sockets or authenticated Windows loopback.

Endpoint descriptors retain the aixand.local/1 wire format.
"""

import asyncio
import contextlib
import json
import os
from pathlib import Path
import secrets
import socket
import uuid

from aixand_filesystem import private_directory, private_path, verify_private

WINDOWS = os.name == "nt"


def endpoint_exists(path):
    path = Path(path)
    if not WINDOWS:
        return path.is_socket()
    try:
        endpoint(path)
        return True
    except (OSError, ValueError):
        return False


def endpoint(path):
    path = Path(path)
    if WINDOWS:
        verify_private(path)
    with path.open("rb") as stream:
        data = stream.read(4097)
    if len(data) > 4096:
        raise ValueError("Local endpoint descriptor is too large")
    value = json.loads(data)
    if (
        value.get("schema") != "aixand.local/1"
        or type(value.get("port")) is not int
        or not 1024 <= value["port"] <= 65535
        or not isinstance(value.get("token"), str)
        or len(value["token"]) != 64
    ):
        raise ValueError("Invalid local endpoint descriptor")
    return value


class LocalServer:
    def __init__(self, server, path, token):
        self.server, self.path, self.token = server, Path(path), token

    def close(self):
        self.server.close()
        try:
            if endpoint(self.path)["token"] == self.token:
                self.path.unlink()
        except (OSError, ValueError):
            pass

    async def wait_closed(self):
        await self.server.wait_closed()

    @property
    def sockets(self):
        return self.server.sockets

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        self.close()
        await self.wait_closed()


async def start_local_server(callback, path=None, *, limit=65536):
    if not WINDOWS:
        return await asyncio.start_unix_server(callback, path=str(path), limit=limit)
    path = Path(path)
    private_directory(path.parent)
    token = secrets.token_hex(32)

    async def authenticate(reader, writer):
        try:
            async with asyncio.timeout(5):
                raw = await reader.readuntil(b"\n")
                if len(raw) > 256:
                    raise ValueError("Invalid local authentication")
                auth = json.loads(raw)
                if not secrets.compare_digest(str(auth.get("token", "")), token):
                    raise ValueError("Invalid local authentication")
            await callback(reader, writer)
        except (
            OSError,
            ValueError,
            TimeoutError,
            asyncio.IncompleteReadError,
            asyncio.LimitOverrunError,
        ):
            pass
        finally:
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()

    server = await asyncio.start_server(authenticate, "127.0.0.1", 0, limit=limit)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex)
    try:
        temporary.write_text(
            json.dumps(
                {
                    "schema": "aixand.local/1",
                    "port": server.sockets[0].getsockname()[1],
                    "token": token,
                }
            )
        )
        private_path(temporary)
        os.replace(temporary, path)
    except BaseException:
        server.close()
        await server.wait_closed()
        temporary.unlink(missing_ok=True)
        raise
    return LocalServer(server, path, token)


async def open_local_connection(path, *, limit=65536):
    if not WINDOWS:
        return await asyncio.open_unix_connection(str(path), limit=limit)
    value = endpoint(path)
    reader, writer = await asyncio.open_connection(
        "127.0.0.1", value["port"], limit=limit
    )
    writer.write(json.dumps({"token": value["token"]}).encode() + b"\n")
    await writer.drain()
    return reader, writer


def connect_local(path, *, timeout=30):
    if not WINDOWS:
        channel = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            channel.settimeout(timeout)
            channel.connect(str(path))
            return channel
        except BaseException:
            channel.close()
            raise
    value = endpoint(path)
    channel = socket.create_connection(("127.0.0.1", value["port"]), timeout)
    try:
        channel.sendall(json.dumps({"token": value["token"]}).encode() + b"\n")
        return channel
    except BaseException:
        channel.close()
        raise
