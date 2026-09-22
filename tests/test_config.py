import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from backend.config import resolve_data_root


class DataRootTests(unittest.TestCase):
    def test_data_root_selection_and_validation(self):
        with tempfile.TemporaryDirectory(prefix="kinodel config ") as directory:
            base = Path(directory).resolve()
            cases = [
                ("win32", {"LOCALAPPDATA": str(base)}, base / "Kinodel"),
                ("linux", {"XDG_DATA_HOME": str(base)}, base / "kinodel"),
                ("linux", {}, base / ".local" / "share" / "kinodel"),
                ("win32", {"KINODEL_DATA_ROOT": str(base / "данные проекта")},
                 base / "данные проекта"),
            ]
            if os.name == "nt":
                cases.append(("win32", {"KINODEL_DATA_ROOT": "\\\\?\\" + str(base / "long")},
                              base / "long"))
            for platform, environment, expected in cases:
                with self.subTest(platform=platform, environment=environment):
                    with patch.dict(os.environ, environment, clear=True), \
                            patch("sys.platform", platform), \
                            patch("pathlib.Path.home", return_value=base):
                        self.assertEqual(resolve_data_root(), expected)
                        self.assertFalse(expected.exists())

            checkout = Path(__file__).resolve().parents[1]
            for invalid in ("", "relative/data", str(checkout / "data"),
                            str(checkout), str(sys.prefix), str(base / "file"),
                            "\\\\server\\share\\kinodel", "\\\\?\\UNC\\server\\share\\kinodel",
                            "\\\\?\\" + str(checkout)):
                (base / "file").touch(exist_ok=True)
                with self.subTest(invalid=invalid):
                    with patch.dict(os.environ, {"KINODEL_DATA_ROOT": invalid}, clear=True):
                        with self.assertRaises(ValueError):
                            resolve_data_root()

            with patch.dict(os.environ, {}, clear=True), patch("sys.platform", "win32"):
                with self.assertRaisesRegex(ValueError, "LOCALAPPDATA"):
                    resolve_data_root()

            with patch.dict(os.environ, {"XDG_DATA_HOME": "relative"}, clear=True), \
                    patch("sys.platform", "linux"):
                with self.assertRaises(ValueError):
                    resolve_data_root()
