#!/usr/bin/env python3
"""Refresh a source patch series after reviewing additions/removals/changes."""
import argparse
import hashlib
from pathlib import Path
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("directory", type=Path, help="For example: docker/patches/php-7.4")
args = parser.parse_args()
directory = args.directory
baseline = (directory / "baseline").read_text().strip()
if not re.fullmatch(r"\d+\.\d+\.\d+", baseline):
    parser.error("baseline must contain an exact PHP release, such as 7.4.33")

patches = sorted(directory.glob("*.patch"))
if not patches:
    parser.error("patch directory is empty")
lines = []
for patch in patches:
    if patch.is_symlink() or not patch.is_file() or not re.fullmatch(r"[0-9]+-[A-Za-z0-9.+_-]+\.patch", patch.name):
        parser.error(f"not a plain, numbered patch file: {patch}")
    lines.append(f"{hashlib.sha256(patch.read_bytes()).hexdigest()}  {patch.name}\n")
manifest = directory / "series.sha256"
manifest.write_text("".join(lines))
print(f"Recorded {len(patches)} patches for PHP {baseline}: {manifest}")
