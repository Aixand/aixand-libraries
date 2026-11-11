# Publish all libraries to PyPI

Push one repository tag, such as `release-1`, to test, build, and publish all three
libraries at their individual package versions. The [publish workflow](../.github/workflows/publish.yml) runs native
tests on Linux, macOS, and Windows with Python 3.11 and 3.14.
Branch pushes to `main`, pull requests, and manual runs check all libraries
without publishing.

## Configure the repository

The workflow expects `Aixand/aixand-libraries`, with `filesystem/`,
`local-runtime/`, and `github-source/` at the repository root. Commit and push
this folder to that repository before GitHub can run CI.

Create one GitHub environment named `pypi`. Configure release tag and environment
rules to restrict publishing to release maintainers.
Register a [PyPI Trusted Publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
for each package below. Use a pending publisher for new projects.

All three publishers use the same settings: owner `Aixand`, repository
`aixand-libraries`, workflow filename `publish.yml`, and environment `pypi`.
Each PyPI project needs its own publisher registration.

| PyPI package | Python import |
| --- | --- |
| `aixand-lib-filesystem` | `aixand_filesystem` |
| `aixand-lib-local-runtime` | `aixand_local_runtime` |
| `aixand-lib-github-source` | `github_source` |

Publishing uses OpenID Connect; no PyPI API tokens are needed. Only the publish
job receives `id-token: write`. Distribution names do not change Python imports.

## Release all libraries with one push

Each package's `pyproject.toml` owns its version. The repository tag identifies
the batch; it does not supply or override package versions. For example, one
`release-1` batch can contain:

| Package | Version |
| --- | --- |
| `aixand-lib-filesystem` | `0.1.0` |
| `aixand-lib-local-runtime` | `0.3.0` |
| `aixand-lib-github-source` | `0.2.1` |

Bump the version of each changed library. Unchanged libraries can keep their
versions; their existing PyPI files are skipped. Update dependent version
constraints when needed, then regenerate affected development locks with
`./dev.sh lock --local` from the package directory. Local-runtime's declared
filesystem constraint must allow the filesystem version in this batch.

Commit the reviewed changes and wait for branch checks to pass. From the
repository root, create and push a unique `release-<identifier>` tag:

```sh
git tag release-1
git push origin release-1
```

That single tag push processes `aixand-lib-filesystem`, `aixand-lib-github-source`,
and `aixand-lib-local-runtime`. A GitHub Release and individual package tags are
not required. The next batch can use `release-2`, independently of package versions.

## Understand the checks and publication order

All libraries must pass native tests and distribution validation before publishing
starts. CI installs built wheels outside the checkout, runs copied package tests,
rebuilds wheels from source archives, and tests those installed wheels too.
Base imports are checked before optional WebSocket support is installed. Twine
checks package metadata and README rendering.

Local-runtime is tested with the filesystem wheel built from the same checkout.
This allows the first repository release to pass its checks before filesystem
exists on PyPI. No earlier manual library publication is needed.

The publish job uploads filesystem first, GitHub-source second, and local-runtime
last. Local-runtime's filesystem dependency is therefore uploaded before it.
A final job reads each package version from the selected commit and installs
those exact versions from PyPI without local wheels or
source overrides, checks imports and dependencies, and retries briefly while
PyPI's index updates.

## Recover a partial publication

PyPI uploads are separate operations, so a repository release is not atomic.
If an upload fails, some packages may already be public. Inspect PyPI and rerun
the failed jobs for the same tag. Uploads skip files that already exist so the
remaining uploads can finish.

Do not move a published tag or modify artifacts under an existing version.
To correct released content, bump the affected package versions and push a new
batch tag. Changing source without bumping its package version leaves the
existing PyPI version in place; the upload does not replace it.
For authentication failures, check each project's publisher settings, especially
workflow filename and environment. An installation failure after upload requires
checking the dependency constraints and PyPI index availability.

Workflow files alone do not establish a successful remote run or enable required
checks in repository settings. Verify the final job before releasing consumers
such as Carrier.
