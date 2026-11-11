# Aixand libraries

These Python libraries provide common functions for applications. Each package
has its own metadata, tests, development commands, and wheel build.
Packages can be installed independently of this repository layout.

| Package | Purpose | Runtime dependencies |
| --- | --- | --- |
| [aixand-lib-filesystem](filesystem/README.md) | File locks, private permissions, Windows pinned paths | None |
| [aixand-lib-local-runtime](local-runtime/README.md) | Local IPC, process identity, shutdown signals | aixand-lib-filesystem; optional WebSockets |
| [aixand-lib-github-source](github-source/README.md) | Public GitHub source resolution and comparison | None |

Run `./dev.sh develop --local`, `./dev.sh check`, `./dev.sh test`, and
`./dev.sh build` from a package directory. Windows uses `dev.ps1`.
See each package's `docs/development.md` for wheel-based setup.

## Use the libraries

Published distribution names follow `aixand-lib-<product-name>`, using the
hyphenated product name. Python import names are separate and remain stable.

Install compatible wheels with pip or uv into the consuming Python environment.
For source development, `--local` selects only the dependency paths explicitly
listed in each package's `development.toml`. Without `--local`, dependencies come
from the configured package index or a supplied wheel directory.

Use `aixand-lib-filesystem` for file locks, private permissions, pinned Windows
paths, and Windows authentication directories. Use `aixand-lib-local-runtime`
for local IPC, process identity, signals, and optional WebSocket adapters.
Applications that use WebSockets select `aixand-lib-local-runtime[websocket]`.
Use `aixand-lib-github-source` for public GitHub source resolution and comparison.

Build wheels and source archives with `./dev.sh build`. Push one repository
batch tag, such as `release-1`, to publish through the [PyPI release workflow](docs/releases.md).
One tag processes all libraries using their individual package versions.
Existing PyPI versions are skipped; Python imports stay unchanged.

## Documentation and templates

Start with the [documentation index](docs/README.md) for each library's usage guide,
API reference, and runnable integration examples. Maintainers can use the
[new-library template](templates/README.md) to establish a consistent package layout.

## Support and reporting

Report bugs, documentation issues, feature requests, and usage questions through
the integrating product's support channel or issue tracker. Ordinary reports do
not belong in this repository. External contributions, including documentation
changes and cleanup, are not currently accepted because maintainer review and
support capacity is limited. See [reporting guidance](docs/reporting.md).
Report suspected vulnerabilities directly and [privately](SECURITY.md).
