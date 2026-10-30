"""Capture or verify the local character baseline without changing project assets."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


PROJECT = Path(__file__).resolve().parents[2]


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def capture(destination: Path) -> dict:
    destination.mkdir(parents=True, exist_ok=False)
    files = [PROJECT / "LearnTopDown.uproject"]
    for relative in ("Content", "Config"):
        files.extend(path for path in (PROJECT / relative).rglob("*") if path.is_file())
    hashes = {path.relative_to(PROJECT).as_posix(): digest(path) for path in sorted(files)}
    for relative in ("Source", "Config"):
        shutil.copytree(PROJECT / relative, destination / "before" / relative)
    shutil.copy2(PROJECT / "LearnTopDown.uproject", destination / "before")
    bundle = destination / "character-project-content.zip"
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in ("Content/TopDown", "Content/__ExternalActors__/TopDown",
                         "Content/__ExternalObjects__/TopDown", "Config"):
            for path in sorted((PROJECT / relative).rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(PROJECT).as_posix())
    report = {"schema_version": 1, "project": str(PROJECT), "protected_hashes": hashes,
              "private_bundle": str(bundle), "bundle_sha256": digest(bundle),
              "external_topdown_map_files_in_bundle": True,
              "original_paragon_assets_in_bundle": False}
    (destination / "baseline.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"baseline": str(destination / "baseline.json"), "protected_files": len(hashes),
            "private_bundle_bytes": bundle.stat().st_size}


def verify(baseline: Path, project: Path = PROJECT) -> dict:
    data = json.loads(baseline.read_text(encoding="utf-8"))
    mismatches = [relative for relative, expected in data["protected_hashes"].items()
                  if not (project / relative).is_file() or digest(project / relative) != expected]
    return {"passed": not mismatches, "protected_files": len(data["protected_hashes"]),
            "mismatches": mismatches}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("capture", "verify"))
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args()
    result = capture(arguments.path) if arguments.action == "capture" else verify(arguments.path)
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result.get("passed", True) else 1)
