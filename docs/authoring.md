# Maintain library documentation

Published distribution names must use `aixand-lib-<product-name>`. Document the
distribution name separately from its Python import name; the two need not match.

Every library has the same entry points:

- `README.md`: purpose, installation, smallest working example, supported Python
  and platforms, dependencies, ownership boundaries, and links into `docs/`.
- `docs/README.md`: navigation to usage, API, examples, and maintainer setup.
- `docs/usage.md`: common integration tasks, error handling, cleanup, platform
  differences, and application responsibilities.
- `docs/api.md`: public signatures, parameters, return values, exceptions, and
  contracts. Keep signatures aligned with exported implementations.
- `examples/`: complete scripts that import the installed package, with a README
  recording commands, expected output, prerequisites, side effects, and cleanup.
- `docs/development.md`: package-local setup, checks, tests, builds, and release links.

When an API changes, update its reference and affected starters together. Keep
examples small and bounded. Use temporary state for local demonstrations and mark
network or interactive prerequisites explicitly. Run local examples after changes;
check network starters offline with help/fixtures and verify real acquisition only
when appropriate. Native platform guarantees require native platform checks.

Source distributions include examples through `MANIFEST.in`; wheels contain runtime
packages. Check relative documentation links and keep the repository docs index
current. The [new-library scaffold](../templates/README.md) establishes this layout.

All documentation must preserve the [reporting policy](reporting.md): ordinary
reports go to the integrator, external contributions are not currently accepted,
and vulnerabilities are reported privately.
