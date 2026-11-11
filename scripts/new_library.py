"""Create a maintainer scaffold using the repository's existing tooling."""
import argparse
from pathlib import Path
import re
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("--import-name", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", args.slug):
        parser.error("slug must be lowercase words separated by hyphens")
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", args.import_name):
        parser.error("import name must be lowercase words separated by underscores")
    import keyword
    if keyword.iskeyword(args.import_name):
        parser.error("import name cannot be a Python keyword")
    root = Path(__file__).resolve().parents[1]
    destination = args.destination or root / args.slug
    if destination.exists():
        parser.error(f"destination already exists: {destination}")
    # Check all inputs before creating the destination.
    baseline = root / "filesystem"
    copied = ["dev.py", "dev.sh", "dev.ps1", "development-constraints.txt",
              ".python-version", "LICENSE", "MANIFEST.in"]
    for name in copied + ["requirements-dev.lock"]:
        if not (baseline / name).is_file():
            parser.error(f"missing baseline file: {name}")
    import json
    values = {
        "SLUG": args.slug,
        "IMPORT": args.import_name,
        "DISTRIBUTION": "aixand-lib-" + args.slug,
        "DESCRIPTION_JSON": json.dumps(args.description),
    }
    rendered = {}
    for source in (root / "templates" / "library").rglob("*.tmpl"):
        relative = str(source.relative_to(root / "templates" / "library"))[:-5]
        content = source.read_text()
        for key, value in values.items():
            relative = relative.replace("__" + key + "__", value)
            content = content.replace("__" + key + "__", value)
        rendered[relative] = content
    destination.mkdir(parents=True)
    for name in copied:
        shutil.copy2(baseline / name, destination / name)
    shutil.copy2(baseline / "requirements-dev.lock", destination / "requirements-dev.lock")
    for name, content in rendered.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    print(destination)


if __name__ == "__main__":
    main()
