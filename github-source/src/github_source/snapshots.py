"""Safe, bounded in-memory repository archive capture."""

import base64
import gzip
import io
import tarfile
import zlib

from .contracts import (
    MAX_DOWNLOAD,
    MAX_ENTRIES,
    MAX_FILE,
    MAX_TOTAL,
    relative,
    require,
    validate_tree,
)
from .errors import GitHubError


class ExpandedLimit:
    """Also bound tar metadata/PAX expansion before tarfile allocates it."""

    def __init__(self, stream):
        self.stream, self.count = stream, 0

    def read(self, size=-1):
        remaining = MAX_TOTAL + MAX_ENTRIES * 4096 - self.count
        value = self.stream.read(
            min(size, remaining + 1) if size >= 0 else remaining + 1
        )
        self.count += len(value)
        require(
            len(value) <= remaining, "Expanded archive metadata exceeds limits", "size"
        )
        return value


def archive_tree(data, *, check=None):
    files, directories, total, seen, prefix = {}, set(), 0, set(), None
    require(len(data) <= MAX_DOWNLOAD, "Archive exceeds size limit")
    expanded = gzip.GzipFile(fileobj=io.BytesIO(data))
    try:
        with tarfile.open(fileobj=ExpandedLimit(expanded), mode="r|") as archive:
            count = 0
            for entry in archive:
                if check is not None:
                    check()
                count += 1
                require(
                    count <= MAX_ENTRIES + 1, "Archive has too many entries", "size"
                )
                name = entry.name.rstrip("/")
                relative(name)
                parts = name.split("/", 1)
                prefix = prefix or parts[0]
                require(parts[0] == prefix, "Archive contains several roots")
                if len(parts) == 1:
                    require(entry.isdir(), "Archive root must be a directory")
                    continue
                path = relative(parts[1])
                require(path.casefold() not in seen, "Archive contains duplicate paths")
                seen.add(path.casefold())
                require(
                    entry.isdir() or entry.isfile(),
                    "Archive contains a link or special file",
                )
                if entry.isdir():
                    directories.add(path)
                else:
                    require(
                        0 <= entry.size <= MAX_FILE,
                        "Archive file exceeds size limit",
                        "size",
                    )
                    total += entry.size
                    require(
                        total <= MAX_TOTAL,
                        "Expanded archive exceeds size limit",
                        "size",
                    )
                    stream = archive.extractfile(entry)
                    require(stream is not None, "Archive file unavailable", "integrity")
                    content = stream.read(entry.size + 1)
                    require(
                        len(content) == entry.size, "Truncated archive", "integrity"
                    )
                    require(
                        not content.startswith(
                            b"version https://git-lfs.github.com/spec/v1\n"
                        ),
                        "Git LFS assets require a complete local checkout; import that local package",
                        "unsupported",
                    )
                    files[path] = {
                        "content_b64": base64.b64encode(content).decode("ascii"),
                        "executable": bool(entry.mode & 0o111),
                    }
                    parent = path.rpartition("/")[0]
                    while parent:
                        directories.add(parent)
                        parent = parent.rpartition("/")[0]
    except (tarfile.TarError, EOFError, gzip.BadGzipFile, zlib.error) as error:
        raise GitHubError("integrity", "Invalid repository archive") from error
    finally:
        expanded.close()
    return validate_tree(
        {
            "schema": "github-source/tree-1",
            "files": files,
            "directories": sorted(directories),
        }
    )
