"""Merge processed dataset manifests (IDRiD, DDR, Optos UWF sources)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def merge_manifests(manifest_paths: list[Path], output_path: Path) -> int:
    merged: list[dict] = []
    seen: set[str] = set()
    for path in manifest_paths:
        if not path.exists():
            print(f"Skipping missing manifest: {path}")
            continue
        for rec in json.loads(path.read_text()):
            key = f"{rec.get('source')}:{rec.get('image_id')}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(rec)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(merged, indent=2))
    print(f"Merged {len(merged)} records → {output_path}")
    return len(merged)


def main():
    parser = argparse.ArgumentParser(description="Merge dataset manifest.json files")
    parser.add_argument("manifests", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/processed/combined/manifest.json"))
    args = parser.parse_args()
    merge_manifests(args.manifests, args.output)


if __name__ == "__main__":
    main()
