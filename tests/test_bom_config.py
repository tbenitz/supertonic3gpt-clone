"""Regression coverage for Windows/.NET UTF-8 BOM compatibility."""
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'desktop' / 'engine'))
from reader import load_profile


class ProfileEncodingTests(unittest.TestCase):
    def test_plain_utf8_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'profile.json'
            path.write_bytes(b'{"engine":"pocket","lang":"english"}')
            self.assertEqual(load_profile(path)['engine'], 'pocket')

    def test_utf8_bom_json_from_old_exe(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'profile.json'
            path.write_bytes(b'\xef\xbb\xbf{"engine":"pocket","lang":"english"}')
            self.assertEqual(load_profile(path)['lang'], 'english')

    def test_launcher_writes_bom_free_utf8(self):
        source = (ROOT / 'desktop' / 'launcher' / 'Program.cs').read_text(encoding='utf-8')
        self.assertIn('new UTF8Encoding(encoderShouldEmitUTF8Identifier: false)', source)
        self.assertIn('ReaderProfileJsonContext.Default.ReaderProfile), Utf8NoBom)', source)

if __name__ == '__main__':
    unittest.main()
