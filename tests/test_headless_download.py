"""Regression tests for PyInstaller --windowed without stdout/stderr."""
import os
import sys
import threading
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "desktop" / "engine"))
from reader import configure_headless_runtime, ensure_public_models


class HeadlessDownloads(unittest.TestCase):
    def test_windowed_runtime_has_safe_output_streams(self):
        with mock.patch.object(sys, "stdout", None), mock.patch.object(sys, "stderr", None):
            with mock.patch.dict(os.environ, {"HF_HUB_DISABLE_PROGRESS_BARS": "0"}):
                configure_headless_runtime()
                self.assertEqual(os.environ["HF_HUB_DISABLE_PROGRESS_BARS"], "1")
                self.assertIsNotNone(sys.stdout)
                self.assertIsNotNone(sys.stderr)
                sys.stdout.write("test")
                sys.stderr.write("test")

    def test_model_download_never_creates_console_progress(self):
        hub = types.ModuleType("huggingface_hub")
        utils = types.ModuleType("huggingface_hub.utils")
        disabled = []
        fetched = []

        def disable_progress_bars():
            disabled.append(True)

        def hf_hub_download(*, repo_id, filename, revision, local_dir, token):
            self.assertEqual(os.environ.get("HF_HUB_DISABLE_PROGRESS_BARS"), "1")
            self.assertTrue(disabled)
            fetched.append(filename)
            output = Path(local_dir) / filename
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"model fixture")
            return str(output)

        hub.hf_hub_download = hf_hub_download
        utils.disable_progress_bars = disable_progress_bars

        with TemporaryDirectory() as tmp, mock.patch.dict(
            sys.modules, {"huggingface_hub": hub, "huggingface_hub.utils": utils}
        ):
            with mock.patch.object(sys, "stdout", None), mock.patch.object(sys, "stderr", None):
                with mock.patch.dict(os.environ, {"HF_HUB_DISABLE_PROGRESS_BARS": "0"}):
                    out = ensure_public_models(
                        tmp, "english", lambda _msg: None, threading.Event()
                    )
                    self.assertEqual(out, Path(tmp) / "onnx")
                    self.assertTrue(fetched)
                    self.assertEqual(len(fetched), 8)
                    self.assertIsNotNone(sys.stderr)
                    self.assertTrue(disabled)

    def test_cancellation_prevents_download_and_import(self):
        event = threading.Event()
        event.set()
        with TemporaryDirectory() as tmp:
            self.assertIsNone(
                ensure_public_models(tmp, "english", lambda _msg: None, event)
            )


if __name__ == "__main__":
    unittest.main()
