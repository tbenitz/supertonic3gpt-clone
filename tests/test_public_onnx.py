"""Regression coverage for the public ONNX clipboard speech path."""
import sys
import unittest
from pathlib import Path
from threading import Event
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "desktop" / "engine"))
from reader import (
    MODEL_REPO, MODEL_REVISION, MODEL_FILES,
    ensure_public_models, language_folder, model_file_names,
    split_text
)


class PublicOnnxTests(unittest.TestCase):
    def test_uses_public_onnx_weights_not_gated_native_cli(self):
        self.assertEqual(MODEL_REPO, "KevinAHM/pocket-tts-onnx")
        self.assertEqual(len(MODEL_REVISION), 40)
        self.assertIn("mimi_encoder.onnx", MODEL_FILES)
        self.assertIn("flow_lm_main_int8.onnx", MODEL_FILES)
        self.assertNotIn("kyutai/pocket-tts", MODEL_REPO)

    def test_six_languages(self):
        self.assertEqual(language_folder("english"), "english_2026-04")
        self.assertEqual(language_folder("german"), "german")
        self.assertIn("onnx/spanish/mimi_encoder.onnx",
                      model_file_names("spanish"))
        with self.assertRaises(ValueError):
            language_folder("japanese")

    def test_chunking_does_not_drop_text(self):
        paragraph = "Hello there. " * 55
        self.assertEqual("".join(split_text(paragraph)).replace(" ", ""),
                         paragraph.replace(" ", ""))

    def test_cancellation_skips_download(self):
        with TemporaryDirectory() as tmp:
            event = Event()
            event.set()
            self.assertIsNone(ensure_public_models(tmp, "english", lambda *_: None, event))

    def test_never_hangs_stop_on_error(self):
        source = (ROOT / "desktop" / "engine" / "reader.py").read_text()
        self.assertIn('messagebox.showerror("Pocket TTS could not speak"', source)
        self.assertIn('"error", message', source)
        self.assertIn('finally:\n                    halt()', source)
        self.assertIn("speaker.stop()", source)
        self.assertIn("speaker.abort()", source)


if __name__ == "__main__":
    unittest.main()
