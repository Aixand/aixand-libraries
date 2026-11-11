"""Select library releases and verify installed distributions without source imports."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {
    "filesystem": "aixand_filesystem",
    "local-runtime": "aixand_local_runtime",
    "github-source": "github_source",
}


def manifest(root=ROOT):
    projects = {}
    for slug in PACKAGES:
        project = tomllib.loads((root / slug / "pyproject.toml").read_text())["project"]
        if project["name"] != f"aixand-lib-{slug}":
            raise ValueError(f"Unexpected distribution name in {slug}")
        if not isinstance(project.get("version"), str) or not project["version"]:
            raise ValueError(f"Missing release version in {slug}")
        projects[slug] = {"name": project["name"], "version": project["version"]}
    return projects


def select(tag, root=ROOT):
    projects = manifest(root)
    if tag and not re.fullmatch(r"release-[A-Za-z0-9][A-Za-z0-9._-]*", tag):
        raise ValueError("Batch release tags must use release-<identifier>")
    return list(projects)


def run(command, **kwargs):
    subprocess.run(list(map(str, command)), check=True, **kwargs)


def smoke(slug, output, wheelhouse=None):
    output = output.resolve()
    wheels = list(output.glob("*.whl"))
    archives = list(output.glob("*.tar.gz"))
    if len(wheels) != 1 or len(archives) != 1:
        raise ValueError("Expected exactly one wheel and one source distribution")
    project = tomllib.loads((ROOT / slug / "pyproject.toml").read_text())["project"]
    with tempfile.TemporaryDirectory(prefix="library-release-") as directory:
        temporary = Path(directory)
        environment = temporary / "venv"
        run(["uv", "venv", environment, "--python", sys.executable])
        python = environment / (
            "Scripts/python.exe" if os.name == "nt" else "bin/python"
        )
        install = [
            "uv",
            "pip",
            "install",
            "--python",
            python,
            "--index-url",
            "https://pypi.org/simple",
        ]
        dependencies = []
        if wheelhouse:
            install += ["--find-links", wheelhouse.resolve()]
            dependencies = list(wheelhouse.resolve().glob("*.whl"))
            if len(dependencies) != 1:
                raise ValueError("Expected exactly one dependency wheel")
        run([*install, *dependencies, wheels[0]])
        # Base import must work before optional WebSocket dependencies are installed.
        check = """
import importlib, importlib.metadata, pathlib, sysconfig, sys
module = importlib.import_module(sys.argv[1])
assert pathlib.Path(module.__file__).resolve().is_relative_to(pathlib.Path(sysconfig.get_path('purelib')).resolve())
assert importlib.metadata.version(sys.argv[2]) == sys.argv[3]
"""
        verify = [
            python,
            "-I",
            "-c",
            check,
            PACKAGES[slug],
            project["name"],
            project["version"],
        ]
        run(verify, cwd=temporary)
        if slug == "local-runtime":
            run([*install, "websockets==16.0"])
        tests = temporary / "tests"
        shutil.copytree(
            ROOT / slug / "tests", tests, ignore=shutil.ignore_patterns("__pycache__")
        )
        run(
            [python, "-I", "-m", "unittest", "discover", "-s", tests, "-v"],
            cwd=temporary,
        )
        source = temporary / "source"
        source.mkdir()
        with tarfile.open(archives[0]) as archive:
            archive.extractall(source, filter="data")
        extracted = list(source.iterdir())
        if len(extracted) != 1 or not extracted[0].is_dir():
            raise ValueError("Expected one source distribution root")
        rebuilt = temporary / "rebuilt"
        run(
            [
                "uv",
                "build",
                "--no-sources",
                "--wheel",
                extracted[0],
                "--out-dir",
                rebuilt,
                "--python",
                python,
            ]
        )
        (rebuilt_wheel,) = rebuilt.glob("*.whl")
        run([*install, "--reinstall", "--no-deps", rebuilt_wheel])
        run(verify, cwd=temporary)
        run(
            [python, "-I", "-m", "unittest", "discover", "-s", tests, "-v"],
            cwd=temporary,
        )
        run(["uv", "pip", "check", "--python", python])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("select")
    check = commands.add_parser("smoke")
    check.add_argument("package", choices=PACKAGES)
    check.add_argument("output", type=Path)
    check.add_argument("--wheelhouse", type=Path)
    args = parser.parse_args()
    if args.command == "select":
        packages = select(os.environ.get("RELEASE_TAG", ""))
        value = json.dumps(packages)
        print(value)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
                stream.write(f"packages={value}\n")
                requirements = [
                    f"{p['name']}=={p['version']}" for p in manifest().values()
                ]
                stream.write(f"requirements={json.dumps(requirements)}\n")
    else:
        smoke(args.package, args.output, args.wheelhouse)


if __name__ == "__main__":
    main()
