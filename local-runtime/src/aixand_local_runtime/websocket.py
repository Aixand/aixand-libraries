"""Authenticated local WebSockets, retaining the Unix socket API on POSIX."""

import json
import os
from pathlib import Path
import secrets
import uuid
from .ipc import WINDOWS, LocalServer, endpoint
from aixand_filesystem import private_directory, private_path


def connect(path, **kwargs):
    if not WINDOWS:
        from websockets.asyncio.client import unix_connect

        return unix_connect(str(path), **kwargs)
    from websockets.asyncio.client import connect as tcp_connect

    value = endpoint(path)
    return tcp_connect(
        f"ws://127.0.0.1:{value['port']}",
        additional_headers={"Authorization": "Bearer " + value["token"]},
        proxy=None,
        **kwargs,
    )


async def serve(callback, path, **kwargs):
    if not WINDOWS:
        from websockets.asyncio.server import unix_serve

        return await unix_serve(callback, str(path), **kwargs)
    from websockets.asyncio.server import serve as tcp_serve
    from http import HTTPStatus

    token = secrets.token_hex(32)

    def authenticate(connection, request):
        if not secrets.compare_digest(
            request.headers.get("Authorization", ""), "Bearer " + token
        ):
            return connection.respond(
                HTTPStatus.UNAUTHORIZED, "Local authentication required\n"
            )

    server = await tcp_serve(
        callback, "127.0.0.1", 0, process_request=authenticate, **kwargs
    )
    path = Path(path)
    private_directory(path.parent)
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
