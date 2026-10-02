"""Built shell is public on the existing loopback origin, not a source-file server."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api import create_app


class StaticUITests(unittest.TestCase):
    def test_build_boundary_and_missing_build(self):
        with tempfile.TemporaryDirectory(prefix="kinodel static ") as directory:
            root = Path(directory)
            dist = root / "dist"
            with patch("backend.api.DIST_ROOT", dist):
                with TestClient(create_app(root / "data"), base_url="http://127.0.0.1:8765",
                                client=("127.0.0.1", 50000)) as client:
                    self.assertIn("сборка", client.get("/").text.lower())
                    self.assertEqual(client.get("/api/session").status_code, 200)
                    self.assertEqual(client.get("/api/not-a-route").status_code, 404)
                    self.assertNotIn("<html", client.get("/api/not-a-route").text.lower())
                    self.assertEqual(client.get("/docs").status_code, 200)
                    self.assertEqual(client.get("/anything").status_code, 404)
                    (dist / "assets").mkdir(parents=True)
                    (dist / "index.html").write_text("<html>shell</html>", encoding="utf-8")
                    (dist / "assets" / "app.js").write_text("/* built */", encoding="utf-8")
                    (dist / ".secret").write_text("secret", encoding="utf-8")
                    self.assertEqual(client.get("/").text, "<html>shell</html>")
                    self.assertEqual(client.get("/index.html").status_code, 200)
                    self.assertEqual(client.get("/assets/app.js").text, "/* built */")
                    for path in ("/assets/.secret", "/.secret", "/src/App.tsx", "/prototype/index.html",
                                 "/assets/%252e%252e%252findex.html", "/assets/sub/index.html", "/assets/no.js"):
                        self.assertEqual(client.get(path).status_code, 404, path)
                    try:
                        (dist / "assets" / "leak.js").symlink_to(dist / ".secret")
                    except OSError:
                        pass  # Windows developer-mode/symlink privilege is not universal.
                    else:
                        self.assertEqual(client.get("/assets/leak.js").status_code, 404)
                    self.assertEqual(client.get("/", headers={"Host": "evil.example"}).status_code, 403)
                    self.assertEqual(client.get("/assets/app.js", headers={"Origin": "https://evil.example"}).status_code, 403)
