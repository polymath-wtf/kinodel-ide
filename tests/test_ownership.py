import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from backend.ownership import own_data_root


CHILD = """
import sys
from pathlib import Path
from backend.ownership import own_data_root
with own_data_root(Path(sys.argv[1])):
    print('owned', flush=True)
    if sys.argv[2] == 'hold':
        sys.stdin.readline()
"""


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kinodel ownership ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "данные"
        self.lock = self.root / ".kinodel.lock"

    def contender(self, root=None):
        return subprocess.run(
            [sys.executable, "-c", CHILD, str(root or self.root), "once"],
            capture_output=True, text=True, timeout=10,
            cwd=Path(__file__).resolve().parents[1],
        )

    def test_process_exclusion_and_release_after_exit_or_death(self):
        for kill in (False, True):
            with self.subTest(kill=kill):
                with subprocess.Popen(
                    [sys.executable, "-c", CHILD, str(self.root), "hold"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, text=True,
                    cwd=Path(__file__).resolve().parents[1],
                ) as owner:
                    try:
                        assert owner.stdout is not None and owner.stdin is not None
                        stdout = owner.stdout
                        ready = queue.Queue()
                        threading.Thread(
                            target=lambda: ready.put(stdout.readline()), daemon=True,
                        ).start()
                        self.assertEqual(ready.get(timeout=10), "owned\n")
                        refused = self.contender()
                        self.assertNotEqual(refused.returncode, 0, refused.stderr)
                        self.assertNotIn("owned", refused.stdout)
                        if kill:
                            owner.kill()
                        else:
                            owner.stdin.write("exit\n")
                            owner.stdin.flush()
                        owner.wait(timeout=10)
                        if not kill:
                            self.assertEqual(owner.returncode, 0)
                    finally:
                        if owner.poll() is None:
                            owner.kill()
                        owner.wait(timeout=10)
                acquired = self.contender()
                self.assertEqual(acquired.returncode, 0, acquired.stderr)
                self.assertTrue(self.lock.is_file())

    def test_preserves_data_and_lock_identity_and_closes_descriptor(self):
        self.root.mkdir()
        payload = b"existing lock contents\x00\xff"
        self.lock.write_bytes(payload)
        data = self.root / "existing.data"
        data.write_bytes(b"keep me")
        before = self.lock.stat()
        with self.assertRaisesRegex(RuntimeError, "body failure"):
            with own_data_root(self.root) as root:
                self.assertEqual(root, self.root.resolve())
                raise RuntimeError("body failure")
        self.assertEqual(self.lock.read_bytes(), payload)
        self.assertEqual((self.lock.stat().st_dev, self.lock.stat().st_ino),
                         (before.st_dev, before.st_ino))
        self.assertEqual(data.read_bytes(), b"keep me")
        self.assertEqual(set(self.root.iterdir()), {self.lock, data})
        acquired = self.contender()
        self.assertEqual(acquired.returncode, 0, acquired.stderr)

    def test_descriptor_is_noninheritable_and_closed(self):
        descriptors = []
        real_open = os.open

        def capture(*args, **kwargs):
            descriptor = real_open(*args, **kwargs)
            descriptors.append(descriptor)
            return descriptor

        with patch("backend.ownership.os.open", side_effect=capture):
            with own_data_root(self.root):
                self.assertTrue(descriptors)
                self.assertTrue(all(not os.get_inheritable(fd) for fd in descriptors))
        for descriptor in descriptors:
            with self.assertRaises(OSError):
                os.fstat(descriptor)

    def test_empty_lock_is_not_written(self):
        with own_data_root(self.root):
            pass
        self.assertEqual(self.lock.read_bytes(), b"")

    def test_invalid_root_and_directory_lock_are_rejected(self):
        self.root.write_bytes(b"root is a file")
        with self.assertRaises((OSError, ValueError)):
            with own_data_root(self.root):
                self.fail("invalid root accepted")
        self.assertEqual(self.root.read_bytes(), b"root is a file")
        self.root.unlink()
        self.root.mkdir()
        self.lock.mkdir()
        with self.assertRaises((OSError, ValueError)):
            with own_data_root(self.root):
                self.fail("directory lock accepted")

    def test_hardlink_lock_is_rejected(self):
        self.root.mkdir()
        target = self.root.parent / "target"
        target.write_bytes(b"untouched")
        os.link(target, self.lock)
        with self.assertRaises((OSError, ValueError)):
            with own_data_root(self.root):
                self.fail("hardlink accepted")
        self.assertEqual(target.read_bytes(), b"untouched")

    def test_symlink_lock_is_rejected(self):
        self.root.mkdir()
        target = self.root.parent / "target"
        target.write_bytes(b"untouched")
        try:
            self.lock.symlink_to(target)
        except OSError as error:
            if os.name == "nt" and error.winerror == 1314:
                self.skipTest("Windows symlink privilege unavailable")
            raise
        with self.assertRaises((OSError, ValueError)):
            with own_data_root(self.root):
                self.fail("symlink accepted")
        self.assertEqual(target.read_bytes(), b"untouched")

    def test_open_error_never_enters_body(self):
        with patch("backend.ownership.os.open", side_effect=PermissionError("denied")):
            with self.assertRaises(PermissionError):
                with own_data_root(self.root):
                    self.fail("unlocked fallback")
