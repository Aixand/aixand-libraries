# New-library template

Published distribution names must follow `aixand-lib-<product-name>`. The
scaffold uses its hyphenated product slug as `<product-name>`; `--import-name`
selects the separate Python import name.

For maintainers creating another independently installable Python library. From
the repository root:

```sh
python scripts/new_library.py sample-tools --import-name aixand_sample_tools --description "Shared sample utilities"
```

This creates `sample-tools/` with distribution name `aixand-lib-sample-tools`, a
`src/` package, metadata, documentation, an example, and a tests directory. Existing
destinations are refused. To preview outside the checkout, add
`--destination /path/to/new/sample-tools`. Names must be lowercase; directory names
use hyphens and import names use underscores. No application services are required.

The scaffold copies the existing filesystem package's maintainer helpers,
constraints, Python version, license, and tool-only development lock. Shared
tool versions therefore start from the repository's existing baseline. It
reuses `dev.py`, `dev.sh`, and `dev.ps1` rather than defining another command system.

After generation:

1. Implement a focused public API and replace the version-only example with a real
   integration starter. Document parameters, return values, exceptions, ownership,
   cleanup, and platform behavior.
2. Add meaningful behavioral tests under `tests/`. The scaffold contains no runtime
   functionality or behavioral tests and is not ready for release.
3. Declare runtime dependencies in `pyproject.toml` and explicit local development
   sources in `development.toml`. Regenerate with `./dev.sh lock --local` after
   dependency changes; never retain accidental filesystem dependencies.
4. Run `./dev.sh develop --local`, `./dev.sh check`, `./dev.sh test`, and
   `./dev.sh build`; verify installation from the wheel in a fresh environment.
5. Add the library to the root README and docs index. Review `scripts/release.py`
   and the release workflow: generation does not register a package for publication.

Package docs follow the [authoring guide](../docs/authoring.md). Reporting policy
belongs to the repository and integrating products; generation adds no contribution
or DCO process. Repository-relative policy links assume the normal package layout.
