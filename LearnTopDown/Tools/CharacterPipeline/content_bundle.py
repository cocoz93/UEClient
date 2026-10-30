"""Restore a private derived-content bundle without deleting or overwriting different files."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


def restore(bundle: Path, destination: Path, expected_sha256: str) -> dict:
    with bundle.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != expected_sha256:
            raise ValueError('Bundle checksum mismatch')
    destination = destination.resolve()
    pending = []
    unchanged = 0
    allowed_roots = ('Content/TopDown/', 'Content/__ExternalActors__/TopDown/',
                     'Content/__ExternalObjects__/TopDown/', 'Config/')
    with zipfile.ZipFile(bundle) as archive:
        # Validate every path and conflict before the first filesystem write.
        for entry in archive.infolist():
            relative = PurePosixPath(entry.filename)
            if entry.is_dir() or relative.is_absolute() or '..' in relative.parts or '\\' in entry.filename:
                raise ValueError('Unexpected archive entry: ' + entry.filename)
            if not entry.filename.startswith(allowed_roots):
                raise ValueError('Archive contains a file outside the declared installation scope')
            target = (destination / entry.filename).resolve()
            if not target.is_relative_to(destination):
                raise ValueError('Archive path escapes destination')
            content = archive.read(entry)
            if target.exists():
                if not target.is_file() or target.read_bytes() != content:
                    raise FileExistsError('Different existing file preserved: ' + str(target))
                unchanged += 1
            else:
                pending.append((target, content))
    for target, content in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(content)
    return {'passed': True, 'created': len(pending), 'unchanged': unchanged, 'overwritten': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('bundle', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(restore(args.bundle, args.destination, args.sha256)))
