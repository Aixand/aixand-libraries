#!/bin/sh
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
interpreter=${AIXAND_DEV_PYTHON:-python3}
if ! command -v "$interpreter" >/dev/null 2>&1 || ! "$interpreter" -B -c 'import sys; sys.exit(sys.version_info < (3, 11))' >/dev/null 2>&1; then
    printf '%s\n' 'This developer helper requires Python 3.11+. Set AIXAND_DEV_PYTHON to its executable.' >&2
    case ${1:-help} in help|--help|-h) printf '%s\n' 'Commands: help doctor develop lock check test build'; exit 0;; esac
    exit 2
fi
exec "$interpreter" -B "$project_root/dev.py" "$@"
