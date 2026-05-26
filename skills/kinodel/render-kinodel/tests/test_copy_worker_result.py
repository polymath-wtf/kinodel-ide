import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "copy_worker_result.py"
spec = importlib.util.spec_from_file_location("copy_worker_result", MODULE_PATH)
copy_worker_result = importlib.util.module_from_spec(spec)
spec.loader.exec_module(copy_worker_result)


class CopyWorkerResultTests(unittest.TestCase):
    def test_normalize_selected_outputs_accepts_fal_native_summary_outputs(self):
        worker_result = {
            "summary": {
                "event_type": "render_batch_terminal",
                "status": "done",
                "outputs": [
                    {
                        "job_id": "shot_01_1",
                        "kind": "i2i",
                        "output_path": "/tmp/project/outputs/shot_01.png",
                        "output_url": "https://fal.media/files/shot_01.png",
                    }
                ],
            },
            "jobs": [
                {
                    "job_id": "shot_01_1",
                    "shot_id": "shot_01",
                    "kind": "i2i",
                    "status": "done",
                    "output_path": "/tmp/project/outputs/shot_01.png",
                    "output_url": "https://fal.media/files/shot_01.png",
                }
            ],
        }

        selected = copy_worker_result.normalize_selected_outputs(worker_result)

        self.assertEqual(
            selected,
            [
                {
                    "shot_id": "shot_01",
                    "kind": "i2i",
                    "path": "/tmp/project/outputs/shot_01.png",
                    "url": "https://fal.media/files/shot_01.png",
                }
            ],
        )


    def test_sync_canonical_outputs_copies_selected_story_attempt_to_shot_name(self):
        root = Path(tempfile.mkdtemp(prefix="copy-worker-canonical-")) / "v1"
        (root / "outputs").mkdir(parents=True)
        raw = root / "outputs" / "api_00039_.png"
        raw.write_bytes(b"attempt-one-shot-one")

        selected = [{
            "shot_id": "shot_01",
            "kind": "image",
            "path": str(raw),
            "url": "https://example.com/api_00039_.png",
        }]

        synced = copy_worker_result.sync_canonical_outputs(root, "story_frames", selected)

        canonical = root / "outputs" / "shot_01.png"
        self.assertTrue(canonical.exists())
        self.assertEqual(canonical.read_bytes(), raw.read_bytes())
        self.assertEqual(synced[0]["path"], "outputs/shot_01.png")
        self.assertEqual(synced[0]["source_path"], "outputs/api_00039_.png")
        self.assertEqual(synced[0]["sha256"], copy_worker_result.file_sha256(canonical))

    def test_snapshot_request_skips_current_request_when_worker_sha_is_historical(self):
        root = Path(tempfile.mkdtemp(prefix="copy-worker-snapshot-")) / "v1"
        root.mkdir(parents=True)
        request = root / "storyboard_requests.json"
        request.write_text(json.dumps({"schema": "kinodel.render_requests.v1", "jobs": []}), encoding="utf-8")

        snapshot = copy_worker_result.snapshot_request(root, "storyboard_requests.json", "0" * 64)

        self.assertIsNone(snapshot)
        self.assertFalse((root / "request_snapshots").exists())


if __name__ == "__main__":
    unittest.main()
