"""Bounded, portable, immutable GitHub source trees. No persistence or application policy."""

import base64
import hashlib
import json
import unicodedata
from pathlib import PurePosixPath

from .errors import GitHubError

MAX_DOWNLOAD = 64 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
MAX_FILE = 16 * 1024 * 1024
MAX_ENTRIES = 10000


def require(condition, message, code="validation"):
    if not condition:
        raise GitHubError(code, message)


def canonical(value):
    def check(item):
        if isinstance(item, dict):
            require(
                all(isinstance(key, str) for key in item),
                "JSON keys must be text",
                "integrity",
            )
            for child in item.values():
                check(child)
        elif isinstance(item, list):
            for child in item:
                check(child)
        else:
            require(
                item is None or type(item) in (str, int, float, bool),
                "Invalid JSON value",
                "integrity",
            )

    try:
        check(value)
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise GitHubError("integrity", "Expected finite UTF-8 JSON") from error


def digest(value):
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def loads(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key", "integrity")
            result[key] = value
        return result

    try:
        result = json.loads(
            data,
            object_pairs_hook=pairs,
            parse_constant=lambda _: require(False, "Non-finite JSON", "integrity"),
        )
        canonical(result)
        return result
    except (ValueError, UnicodeError) as error:
        raise GitHubError("validation", "Invalid UTF-8 JSON") from error


def relative(value, *, empty=False):
    require(
        isinstance(value, str)
        and len(value) <= 1024
        and "\\" not in value
        and "\0" not in value
        and ":" not in value,
        "Invalid package path",
    )
    if value == "" and empty:
        return ""
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise GitHubError("validation", "Source path must be valid UTF-8") from error
    p = PurePosixPath(value)
    require(
        value
        and not p.is_absolute()
        and all(part not in ("", ".", "..") for part in value.split("/"))
        and str(p) == value,
        "Package path must stay inside its root",
    )
    require(
        len(p.parts) <= 32
        and all(
            len(part.encode("utf-8")) <= 255
            and not part.endswith((".", " "))
            and not any(ord(c) < 32 or ord(c) == 127 for c in part)
            and not any(c in part for c in '<>"|?*')
            and part.split(".")[0].upper()
            not in {
                "CON",
                "PRN",
                "AUX",
                "NUL",
                *(f"COM{i}" for i in range(1, 10)),
                *(f"LPT{i}" for i in range(1, 10)),
            }
            for part in p.parts
        ),
        "Source path is not portable",
    )
    return value


def validate_tree(tree):
    require(
        isinstance(tree, dict)
        and set(tree) == {"schema", "files", "directories"}
        and tree.get("schema") == "github-source/tree-1"
        and isinstance(tree.get("files"), dict)
        and isinstance(tree.get("directories"), list),
        "Invalid source tree",
        "integrity",
    )
    require(
        len(tree["files"]) + len(tree["directories"]) <= MAX_ENTRIES,
        "Too many source entries",
    )
    require(
        all(isinstance(path, str) for path in [*tree["directories"], *tree["files"]]),
        "Source paths must be text",
        "integrity",
    )
    total, folded = 0, set()
    require(
        len(set(tree["directories"])) == len(tree["directories"]),
        "Duplicate source directories",
    )
    all_directories = set(tree["directories"])
    for path in [*tree["directories"], *tree["files"]]:
        relative(path)
        all_directories.update(
            str(parent) for parent in PurePosixPath(path).parents if str(parent) != "."
        )
    require(
        len(all_directories) + len(tree["files"]) <= MAX_ENTRIES,
        "Too many source entries",
        "size",
    )
    for path in [*all_directories, *tree["files"]]:
        relative(path)
        require(
            unicodedata.normalize("NFC", path).casefold() not in folded,
            "Source contains colliding paths",
        )
        folded.add(unicodedata.normalize("NFC", path).casefold())
    for path, row in tree["files"].items():
        require(
            isinstance(row, dict)
            and set(row) == {"content_b64", "executable"}
            and type(row["executable"]) is bool
            and isinstance(row["content_b64"], str),
            "Invalid source file",
            "integrity",
        )
        try:
            data = base64.b64decode(row["content_b64"], validate=True)
        except (ValueError, TypeError) as error:
            raise GitHubError("integrity", "Invalid source file encoding") from error
        total += len(data)
        require(
            len(data) <= MAX_FILE and total <= MAX_TOTAL, "Source exceeds size limits"
        )
        parents = PurePosixPath(path).parents
        require(
            not any(str(p) in tree["files"] for p in parents),
            "Source file is also a directory",
        )
    return {
        **tree,
        "directories": sorted(all_directories),
        "files": dict(sorted(tree["files"].items())),
    }


def subtree(tree, path):
    relative(path, empty=True)
    if not path:
        return tree
    prefix = path + "/"
    return {
        "schema": tree["schema"],
        "files": {
            key[len(prefix) :]: value
            for key, value in tree["files"].items()
            if key.startswith(prefix)
        },
        "directories": [
            key[len(prefix) :] for key in tree["directories"] if key.startswith(prefix)
        ],
    }
