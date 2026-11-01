import struct
import subprocess
import tempfile
from pathlib import Path
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'desktop' / 'engine'))
from reader import split_text

class StarterTests(unittest.TestCase):
    def test_chunking_long(self):
        text = 'A short sentence. ' * 500
        chunks = split_text(text)
        self.assertTrue(chunks)
        self.assertTrue(all(len(x) <= 320 for x in chunks))

    def test_overlay_format(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            stub = p / 'stub.exe'
            stub.write_bytes(b'MZ' + b'hello' * 100)
            blob = p / 'engine.zip'
            with zipfile.ZipFile(blob, 'w') as f:
                f.writestr('reader.exe', b'test')
            dst = p / 'base.exe'
            subprocess.run([sys.executable, str(ROOT / 'tools' / 'append_bundle.py'), str(stub), str(blob), str(dst)], check=True)
            contents = dst.read_bytes()
            self.assertEqual(contents[-16:-8], b'CVRZIP01')
            self.assertEqual(struct.unpack('<Q', contents[-8:])[0], len(blob.read_bytes()))
            cfg = b'{"voice":"M1"}'
            personalised = contents + cfg + b'CVRCFG01' + struct.pack('<Q',len(cfg))
            self.assertEqual(personalised[-16:-8], b'CVRCFG01')
            cfg_len = struct.unpack('<Q',personalised[-8:])[0]
            self.assertEqual(personalised[-16-cfg_len:-16], cfg)

if __name__ == '__main__':
    unittest.main()
