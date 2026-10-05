from contextlib import chdir
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from backend.config import resolve_data_root


class DataRootTests(unittest.TestCase):
    def test_default_uses_installation_stuff_without_filesystem_mutation(self):
        with tempfile.TemporaryDirectory(prefix="kinodel config ") as directory:
            base = Path(directory).resolve()
            installation = base / "installation"
            (installation / "backend").mkdir(parents=True)
            shell = base / "shell"
            shell.mkdir()
            expected = installation / "stuff"
            for existing in (False, True):
                if existing:
                    expected.mkdir()
                    (expected / "user-file").write_bytes(b"preserve me")
                before = sorted(base.rglob("*"))
                for platform in ("win32", "linux", "darwin"):
                    for cwd in (installation, shell):
                        with self.subTest(existing=existing, platform=platform, cwd=cwd):
                            with patch.dict(os.environ, {}, clear=True), \
                                    patch("sys.platform", platform), chdir(cwd), \
                                    patch("backend.config.__file__", str(installation / "backend" / "config.py")):
                                self.assertEqual(resolve_data_root(), expected)
                                self.assertEqual(expected.exists(), existing)
                                self.assertEqual(sorted(base.rglob("*")), before)
                                if existing:
                                    self.assertEqual((expected / "user-file").read_bytes(), b"preserve me")

    def test_default_ignores_os_data_locations(self):
        expected = Path(__file__).resolve().parents[1] / "stuff"
        for platform in ("win32", "linux", "darwin"):
            with self.subTest(platform=platform), \
                    patch.dict(os.environ, {"LOCALAPPDATA": "relative", "XDG_DATA_HOME": "relative"}, clear=True), \
                    patch("sys.platform", platform), \
                    patch("pathlib.Path.home", side_effect=AssertionError("Home must not be consulted")):
                self.assertEqual(resolve_data_root(), expected)

    def test_data_root_selection_and_validation(self):
        with tempfile.TemporaryDirectory(prefix="kinodel config ") as directory, \
                patch.dict(os.environ, {}, clear=True):
            base = Path(directory).resolve()
            installation = base / "installation"
            stuff = installation / "stuff"
            venv = stuff / "venv"
            with patch("backend.config.__file__", str(installation / "backend" / "config.py")), \
                    patch("sys.prefix", str(venv)):
                self._check_overrides(base, installation, stuff, venv)

    def _check_overrides(self, base, installation, stuff, venv):
            cases = [
                base / "данные проекта", stuff, stuff / "isolated",
            ]
            if os.name == "nt":
                cases.extend((base / "long", stuff / "long"))
            for expected in cases:
                raw = str(expected)
                if os.name == "nt" and expected.name == "long":
                    raw = "\\\\?\\" + raw
                with self.subTest(override=raw):
                    with patch.dict(os.environ, {"KINODEL_DATA_ROOT": raw}, clear=True):
                        self.assertEqual(resolve_data_root(), expected)
                        self.assertFalse(expected.exists())

            stuff.mkdir(parents=True)
            (stuff / "file").touch()
            (base / "file").touch()
            for invalid in ("", "relative/data", str(installation / "data"),
                            str(installation), str(installation / "backend"),
                            str(installation / "stuff-source"), str(stuff / ".." / "backend"),
                            str(venv), str(venv / "nested"), str(base / "file"), str(stuff / "file"),
                            "\\\\server\\share\\kinodel", "\\\\?\\UNC\\server\\share\\kinodel",
                            "//server/share/kinodel", "\\\\.\\C:\\kinodel", "\\\\?\\" + str(installation)):
                with self.subTest(invalid=invalid):
                    with patch.dict(os.environ, {"KINODEL_DATA_ROOT": invalid}, clear=True):
                        with self.assertRaises(ValueError):
                            resolve_data_root()


class DataRootStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_start_and_restart_under_checkout_stuff(self):
        from uuid import uuid4

        from backend.api import fixture_story
        from backend.story_control import open_story_runtime
        from backend.story_store import read_story

        stuff = Path(__file__).resolve().parents[1] / "stuff"
        existed = stuff.exists()
        stuff.mkdir(exist_ok=True)
        if not existed:
            self.addCleanup(stuff.rmdir)
        with tempfile.TemporaryDirectory(prefix="config-startup-", dir=stuff) as directory:
            root = Path(directory) / "data"
            with patch.dict(os.environ, {"KINODEL_DATA_ROOT": str(root)}, clear=True):
                async with open_story_runtime(resolve_data_root(), fixture_story) as runtime:
                    receipt = await runtime.start(str(uuid4()), "start", "A fox", ["s1"])
                    self.assertEqual(await runtime.run(), 1)
                    saved = read_story(runtime.db, receipt.execution_id)
                for name in ("application.sqlite3", "checkpoints.sqlite3", ".kinodel.lock"):
                    self.assertTrue((root / name).is_file(), name)
                ref = saved[0]
                body = root / "projects" / ref.project_id / "artifacts" / f"{ref.artifact_id}.{ref.digest[7:]}.json"
                self.assertTrue(body.is_file())
                async with open_story_runtime(resolve_data_root(), fixture_story) as runtime:
                    self.assertEqual(await runtime.run(), 0)
                    self.assertEqual(read_story(runtime.db, receipt.execution_id), saved)
