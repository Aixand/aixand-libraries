"""Core local IPC works with only the two shared packages and the stdlib."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import aixand_filesystem
import aixand_local_runtime


class StandaloneTests(unittest.TestCase):
    def test_core_ipc_without_site_packages(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for package in (aixand_filesystem, aixand_local_runtime):
                shutil.copytree(
                    Path(package.__file__).parent,
                    root / package.__name__,
                    ignore=shutil.ignore_patterns("__pycache__"),
                )
            script = """
import asyncio, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from aixand_filesystem import private_directory
from aixand_local_runtime import start_local_server, open_local_connection

async def run():
    endpoint = private_directory(Path(sys.argv[1]) / 'state') / 'endpoint'
    async def echo(reader, writer):
        writer.write(await reader.readline())
        await writer.drain()
        writer.close()
        await writer.wait_closed()
    server = await start_local_server(echo, endpoint)
    try:
        reader, writer = await open_local_connection(endpoint)
        writer.write(b'core-only IPC\\n')
        await writer.drain()
        assert await reader.readline() == b'core-only IPC\\n'
        writer.close()
        await writer.wait_closed()
    finally:
        server.close()
        await server.wait_closed()
asyncio.run(run())
assert all(name.split('.')[0] in sys.stdlib_module_names |
    {'__main__', 'aixand_filesystem', 'aixand_local_runtime'} for name in sys.modules)
"""
            result = subprocess.run(
                [sys.executable, "-I", "-S", "-c", script, str(root)],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
