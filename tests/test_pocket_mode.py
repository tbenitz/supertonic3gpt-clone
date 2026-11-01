"""Static checks for the local Pocket TTS workflow."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class LocalPocketTests(unittest.TestCase):
    def test_browser_local_audio_and_export(self):
        page = (ROOT / "web/index.html").read_text(encoding="utf-8")
        for marker in ('data-tab="pocket"', 'getUserMedia', 'encodePocketReference',
                       'profile.voice_wav_b64=await encodePocketReference(pocketClip)',
                       'href="./pocket/"'):
            self.assertIn(marker, page)
    def test_native_launcher_extracts_voice(self):
        source = (ROOT / "desktop/launcher/Program.cs").read_text(encoding="utf-8")
        self.assertIn('voice_wav_b64', source)
        self.assertIn('VoicePath = pocketVoicePath', source)
    def test_reader_uses_blocking_audio_and_stop(self):
        source = (ROOT / "desktop/engine/reader.py").read_text(encoding="utf-8")
        self.assertIn("config.get('engine') == 'pocket'", source)
        self.assertIn("'--output-path', str(wav_path)", source)
        self.assertIn('p.kill()', source)
        self.assertIn('blocking=True', source)
    def test_pocket_assets_are_deployed(self):
        workflow = (ROOT / ".github/workflows/build-deploy.yml").read_text(encoding="utf-8")
        self.assertIn('a4496c429f1dcd6ea8faef55a21dc4b7d45636a9', workflow)
        self.assertIn('pocket-tts-3.3.0-x86_64-pc-windows-msvc.zip', workflow)

if __name__ == "__main__":
    unittest.main()
