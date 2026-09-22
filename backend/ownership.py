"""OS-backed ownership only; no database or storage-volume preflight."""

from collections.abc import Iterator
from contextlib import contextmanager
import os
from pathlib import Path
import stat
import sys


@contextmanager
def own_data_root(root: Path) -> Iterator[Path]:
    """Hold exclusive ownership until exit; callers must stop writers first.

    The permanent lock is never written or removed. The root must be trusted:
    metadata checks cannot prevent another actor replacing paths after checking.
    """
    if sys.platform not in ("win32", "linux"):
        raise OSError("Data-root ownership requires Windows or Linux")
    if not root.is_absolute():
        raise ValueError("Data root must be absolute")
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise ValueError("Data root must be a directory")
    lock = root / ".kinodel.lock"
    try:
        before = lock.lstat()
    except FileNotFoundError:
        before = None
    if before is not None and (
        not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
        or getattr(before, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    ):
        raise ValueError("Lock must be a regular, unredirected, single-link file")

    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOINHERIT", 0)
    descriptor = os.open(lock, flags, 0o600)
    try:
        os.set_inheritable(descriptor, False)
        opened = os.fstat(descriptor)
        current = lock.lstat()
        if (
            not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
            or not stat.S_ISREG(current.st_mode) or current.st_nlink != 1
            or getattr(current, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
            or not os.path.samestat(opened, current)
            or (before is not None and not os.path.samestat(before, opened))
        ):
            raise ValueError("Lock path was redirected or replaced")
        if sys.platform == "win32":
            import msvcrt

            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield root
    finally:
        # Closing releases the OS lock, including when the context body raises.
        os.close(descriptor)
