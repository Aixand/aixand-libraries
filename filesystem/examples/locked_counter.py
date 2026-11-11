"""Run in an installed environment; all state is temporary."""
from pathlib import Path
from tempfile import TemporaryDirectory
from aixand_filesystem import file_lock, private_directory, secure_file


def main():
    with TemporaryDirectory(prefix="aixand-files-") as temporary:
        state = private_directory(Path(temporary) / "state")
        # Keep the lock inode stable and separate from the replaceable data file.
        with (state / "counter.lock").open("a+b") as lock:
            secure_file(lock)
            with file_lock(lock):
                target = state / "counter.txt"
                count = int(target.read_text()) if target.exists() else 0
                staged = state / "counter.next"
                with staged.open("w") as output:
                    secure_file(output)
                    output.write(str(count + 1))
                staged.replace(target)
                print(target.read_text())


if __name__ == "__main__":
    main()
