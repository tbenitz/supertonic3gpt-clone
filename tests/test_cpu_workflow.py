import importlib.util
import tempfile
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'tools' / 'prepare_cpu_clone.py'
spec = importlib.util.spec_from_file_location('prepare_cpu_clone', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class CpuWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'samples').mkdir()
        mod.ROOT = self.root

    def test_sample_example_without_private_recording(self):
        self.assertEqual(mod.prepare('upstream-example', 'samples/none.wav', '300'), 'example')
        self.assertEqual((self.root / 'training-steps.txt').read_text(), '300')
        self.assertFalse((self.root / 'sample-input.wav').exists())

    def test_reject_path_traversal(self):
        (self.root / 'private.wav').write_bytes(b'test')
        with self.assertRaises(ValueError):
            mod.prepare('repo-wav', '../private.wav', '300')

    def test_repo_audio_must_be_explicit(self):
        (self.root / 'samples' / 'my.wav').write_bytes(b'RIFFfakewav')
        mod.prepare('repo-wav', 'samples/my.wav', '600')
        self.assertEqual((self.root / 'sample-input.wav').read_bytes(), b'RIFFfakewav')

    def test_steps_bounded(self):
        for n in ['0', '3001', '-100', 'not-number']:
            with self.assertRaises(ValueError):
                mod.prepare('upstream-example', '', n)


if __name__ == '__main__':
    unittest.main()
