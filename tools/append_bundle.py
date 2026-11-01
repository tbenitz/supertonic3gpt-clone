"""Append trusted Windows engine ZIP to native launcher; no secrets/profiles in CI."""
from pathlib import Path
import struct
import sys

launcher, zipped, destination = map(Path, sys.argv[1:4])
with destination.open('wb') as out:
    out.write(launcher.read_bytes())
    with zipped.open('rb') as f:
        while chunk := f.read(1024*1024):
            out.write(chunk)
    out.write(b'CVRZIP01')
    out.write(struct.pack('<Q', zipped.stat().st_size))
print(f'Built {destination} ({destination.stat().st_size:,} bytes)')
