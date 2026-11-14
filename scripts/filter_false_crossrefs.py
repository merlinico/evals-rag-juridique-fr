#!/usr/bin/env python3
"""Drop CrossRef edges that mis-resolve foreign-code citations.

Rewrites ``data/corpus/crossrefs.json.gz`` and updates ``manifest.json``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_juridique.corpus.loader import (  # noqa: E402
    _write_json,
    load_corpus,
)
from rag_juridique.corpus.refs import is_false_cross_code_ref  # noqa: E402


def main() -> int:
    corpus = load_corpus()
    by_id = corpus.by_id()
    kept = []
    removed = []
    for ref in corpus.crossrefs:
        src = by_id.get(ref.source_article_id)
        tgt = by_id.get(ref.target_article_id)
        if src is None or tgt is None:
            removed.append(ref)
            continue
        if is_false_cross_code_ref(
            ref,
            source_text=src.text,
            source_code=src.code,
            target_code=tgt.code,
        ):
            removed.append(ref)
            continue
        kept.append(ref)

    out_path = ROOT / "data" / "corpus" / "crossrefs.json.gz"
    _write_json(
        out_path,
        {
            "source": {
                "snapshot_id": corpus.snapshot_id,
                "n_crossrefs": len(kept),
                "filtered_false_cross_code": len(removed),
            },
            "crossrefs": [r.model_dump(mode="json") for r in kept],
        },
    )

    manifest_path = ROOT / "data" / "corpus" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_code: dict[str, int] = {}
    for ref in kept:
        art = by_id.get(ref.source_article_id)
        key = (art.code if art else None) or "unknown"
        by_code[key] = by_code.get(key, 0) + 1
    manifest["n_crossrefs"] = len(kept)
    manifest["crossrefs_by_code"] = by_code
    manifest["crossrefs_filtered_false_cross_code"] = len(removed)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"before={len(corpus.crossrefs)} kept={len(kept)} removed={len(removed)}")
    print(f"wrote {out_path}")
    # Spot-check the famous false edge
    false_left = [
        r
        for r in kept
        if r.source_article_id == "LEGIARTI000044224603"
        and r.target_num == "L. 762-2"
    ]
    print("L.121-22→L.762-2 remaining:", len(false_left))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
