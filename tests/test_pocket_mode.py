"""Regression tests for the Pocket-only website and Windows export."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class LocalPocketTests(unittest.TestCase):
    def test_root_is_pocket_only(self):
        html = (ROOT / "web/index.html").read_text(encoding="utf-8")
        self.assertIn("pocket/", html)
        self.assertIn("tbenitz", html)
        self.assertNotIn("Supertonic", html)

    def test_sample_preview_before_export(self):
        js = (ROOT / "web/pocket-export.js").read_text(encoding="utf-8")
        self.assertIn("app.lastClonedPCM", js)
        self.assertIn("app.finalizePlayback", js)
        self.assertIn("auditionedSerial === clonedSerial", js)
        self.assertIn("button.disabled = !eligible()", js)
        self.assertIn("consent.checked", js)
        self.assertIn("CVRCFG01", js)
        self.assertIn("voice_wav_b64", js)

    def test_branding_and_theme(self):
        py = (ROOT / "tools/customize_pocket.py").read_text(encoding="utf-8")
        css = (ROOT / "web/pocket-theme.css").read_text(encoding="utf-8")
        self.assertIn('name="author" content="tbenitz"', py)
        self.assertIn("github.com/tbenitz", py)
        self.assertIn("pocket-export.js", py)
        self.assertIn("#62d6f6", css)

    def test_native_reader_uses_pocket_only(self):
        reader = (ROOT / "desktop/engine/reader.py").read_text(encoding="utf-8")
        launcher = (ROOT / "desktop/launcher/Program.cs").read_text(encoding="utf-8")
        self.assertIn("from pocket_tts_onnx import PocketTTSOnnx", reader)
        self.assertIn("tts.stream(segment, voice=voice_embeddings)", reader)
        self.assertIn("speaker.stop()", reader)
        self.assertIn("messagebox.showerror", reader)
        self.assertNotIn("from supertonic", reader)
        self.assertIn("voice_wav_b64", launcher)

    def test_deployment_is_integrated(self):
        workflow = (ROOT / ".github/workflows/build-deploy.yml").read_text(encoding="utf-8")
        self.assertIn("tools/customize_pocket.py", workflow)
        self.assertIn("web/pocket-theme.css", workflow)
        self.assertIn("web/pocket-export.js", workflow)
        self.assertIn("KevinAHM/pocket-tts-onnx", workflow)

if __name__ == "__main__":
    unittest.main()
