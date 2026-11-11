# Develop Local runtime utilities

Run these commands from this package directory. The local helper needs Python
3.11+ and uv (development version: 0.12.7). It creates this package's `.venv`;
you do not need to activate it or prepare another application environment.

## Work inside the library checkout

```sh
./dev.sh doctor
./dev.sh develop --local
./dev.sh check
./dev.sh test
./dev.sh build
```

`--local` explicitly selects the source dependencies listed in
[development.toml](../development.toml). It installs only this package and its
configured development dependencies. Shared source changes are editable. Check
exits zero after dependency and static checks; test runs this package's unittest
suite. Optional native/runtime tests can skip when their prerequisites are absent.
Build writes a wheel and source archive to `dist/` from fresh source copies.

On Windows, use `.\dev.ps1` with the same arguments. PowerShell/native Windows
execution is not established by Linux checks. `AIXAND_DEV_PYTHON` selects the
helper interpreter; `UV_PYTHON` selects the development/build interpreter when
creating a new environment. The default is recorded in `.python-version`.

## Work without sibling source directories

Obtain compatible dependency wheels first if they are not available from your
configured index. This development branch does not establish index publication.

```sh
./dev.sh develop --wheelhouse /path/to/dependency-wheels
./dev.sh check
./dev.sh test
```

Without `--local`, the helper uses versioned dependencies from the index or supplied
wheel directory. It does not follow sibling source paths. The wheel directory must
contain the first-party versions pinned in `requirements-dev.lock`; third-party
packages can also come from the configured index/cache. Neither source mode requires a running application service.

## Change development dependencies

Edit `development.toml`, `development-constraints.txt`, or the package metadata,
then intentionally regenerate:

```sh
./dev.sh lock --local
./dev.sh develop --local
```

For an extracted checkout, use `lock --wheelhouse /path/to/dependency-wheels`.
The lock pins the selected Python 3.11+ dependency graph. Registry distributions
include hashes; editable first-party inputs become versioned entries so the lock
contains no machine-specific source paths. Review lock changes before committing.
The selected development extras are not added to the package's base dependencies.

## Build and consume independently

```sh
./dev.sh build --output /path/to/build-output
```

Build needs only uv and a compatible Python.
Install the resulting wheel with pip/uv in your consumer environment, supplying
its declared dependencies. Use a new environment and `aixand_local_runtime` imports to check
consumption. Source archives include local helpers, configuration, tests, and docs.
Development environments and build outputs remain outside version control.

## Installation and publication

Install libraries into the consuming Python environment with pip or uv.
The development helper builds distributions locally. Repository releases publish
all libraries together through one repository version tag; see the [PyPI release guide](../../docs/releases.md).

[Package overview](../README.md) · [Developer command implementation](../dev.py)
