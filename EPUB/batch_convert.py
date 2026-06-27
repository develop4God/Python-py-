#!/usr/bin/env python3
"""
batch_convert.py — Convert every Encounter JSON for one language into EPUBs.

Expects the standard repo layout, sparse-cloned locally:
  <devocionales-json>/encounters/<lang>/*.json
  <devocionales-assets>/images/encounters/<encounter_id>_001/*.{avif,png}

Usage:
  python batch_convert.py <lang> <devocionales-json_path> <devocionales-assets_path> <output_dir>

Example:
  python batch_convert.py es /tmp/devocionales-json /tmp/Devocionales-assets /tmp/epubs
"""

import sys
import json
from pathlib import Path

from encounters_to_epub import convert


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)

    lang, json_repo, assets_repo, out_dir = sys.argv[1:5]
    json_dir = Path(json_repo) / 'encounters' / lang
    assets_root = Path(assets_repo) / 'images' / 'encounters'
    index_path = Path(json_repo) / 'encounters' / 'index.json'
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not json_dir.exists():
        print(f"No encounters found for language '{lang}' at {json_dir}")
        sys.exit(1)
    if not index_path.exists():
        print(f"⚠️  No index.json found at {index_path} — covers will fall back to "
              f"meta.character instead of the authored titles/subtitles.")
        index_path = None

    results = []
    for json_file in sorted(json_dir.glob('*.json')):
        with open(json_file, encoding='utf-8') as f:
            data = json.load(f)
        encounter_id = data.get('id', json_file.stem)
        # encounter_id is like "bartimaeus_001" already, or "bartimaeus" without suffix
        candidates = [encounter_id, f'{encounter_id}_001']
        assets_dir = None
        for c in candidates:
            p = assets_root / c
            if p.exists():
                assets_dir = p
                break
        if assets_dir is None:
            print(f"⚠️  Skipping {json_file.name}: no asset folder found (tried {candidates})")
            continue

        out_path = out_dir / f'{json_file.stem}.epub'
        try:
            n_chapters, n_images = convert(str(json_file), str(assets_dir), str(out_path), index_path=str(index_path) if index_path else None)
            print(f"✅  {out_path.name}  ({n_chapters} chapters, {n_images} images)")
            results.append(out_path)
        except Exception as e:
            print(f"❌  {json_file.name}: {e}")

    print(f"\nDone. {len(results)} EPUB(s) written to {out_dir}")


if __name__ == '__main__':
    main()
