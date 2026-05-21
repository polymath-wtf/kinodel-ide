import importlib.util
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


if __name__ == "__main__":
    unittest.main()
