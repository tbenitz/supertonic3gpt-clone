"""Validate manual GitHub Actions cloning inputs without shell interpolation.

No API upload endpoint is exposed by this workflow. In a PUBLIC repository,
committing samples/reference.wav permanently exposes the voice sample.
"""
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(source: str, path: str, steps: str):
    try:
        n = int(steps)
    except ValueError as e:
        raise ValueError('training_steps must be an integer') from e
    if not 100 <= n <= 3000:
        raise ValueError('training_steps must be 100..3000')
    (ROOT / 'training-steps.txt').write_text(str(n))
    if source == 'upstream-example':
        return 'example'
    if source != 'repo-wav':
        raise ValueError('source must be upstream-example or repo-wav')
    samples = (ROOT / 'samples').resolve()
    target = (ROOT / path).resolve()
    if not target.is_relative_to(samples) or target.suffix.lower() != '.wav':
        raise ValueError('Input must be a WAV file under samples/')
    if not target.is_file() or target.stat().st_size > 25 * 1024 * 1024:
        raise ValueError('Missing or oversized WAV file (25 MB max)')
    shutil.copyfile(target, ROOT / 'sample-input.wav')
    return str(target)


if __name__ == '__main__':
    print(prepare(os.environ['TRAIN_SOURCE'], os.environ['SAMPLE_PATH'], os.environ['TRAIN_STEPS']))
