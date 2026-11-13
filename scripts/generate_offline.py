#!/usr/bin/env python3
"""Offline 7–8B generation → GenerationRecord fixtures (GPU machine, not CI).

Example (WSL + Ollama, ~16 GB VRAM):

    ollama pull qwen2.5:7b-instruct
    uv run python scripts/generate_offline.py \\
        --model qwen2.5:7b-instruct \\
        --config configs/default.yaml \\
        --write-baseline

See RUN_ON_GPU.md for the full Windows + WSL procedure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Allow running as `python scripts/generate_offline.py` without install.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from rag_juridique.contracts.generation import GenerationRecord  # noqa: E402
from rag_juridique.eval.pipeline import (  # noqa: E402
    baseline_payload,
    load_config,
    run_config,
)
from rag_juridique.gold.loader import load_gold  # noqa: E402


def _prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate GenerationRecord fixtures with a local Ollama 7–8B model"
    )
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument(
        "--model",
        default="qwen2.5:7b-instruct",
        help="Ollama model tag (default: qwen2.5:7b-instruct)",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Ollama base URL (default: from config or http://127.0.0.1:11434)",
    )
    parser.add_argument(
        "--chunk-sizes",
        default=None,
        help="Comma-separated chunk sizes (default: config chunking.sizes)",
    )
    parser.add_argument(
        "--fixtures-dir",
        default=None,
        help="Output directory (default: config generation.fixtures_dir)",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Also refresh baseline_metrics.json from this run",
    )
    parser.add_argument(
        "--suffix",
        default="",
        help="Optional filename suffix, e.g. _7b → generations_chunk_500_7b.json",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    config = dict(config)
    gen_cfg = dict(config.get("generation") or {})
    gen_cfg["model"] = args.model
    if args.base_url:
        gen_cfg["base_url"] = args.base_url
    config["generation"] = gen_cfg

    gold = load_gold(config["gold_path"])
    if args.chunk_sizes:
        sizes = [int(x.strip()) for x in args.chunk_sizes.split(",") if x.strip()]
    else:
        sizes = [int(s) for s in config["chunking"]["sizes"]]

    fixtures_dir = Path(args.fixtures_dir or gen_cfg.get("fixtures_dir", "data/fixtures"))
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    from sentence_transformers import SentenceTransformer

    dense_model = SentenceTransformer(config["retrieval"]["embedding_model"])

    all_metrics = []
    for size in sizes:
        name = f"chunk_{size}"
        print(f"=== Generating {name} with {args.model} ===")
        metrics, generations = run_config(
            name=name,
            chunk_size=int(size),
            config=config,
            gold=gold,
            use_fixtures=False,
            fixtures_path=None,
            generate=True,
            dense_model=dense_model,
        )
        # Ensure contract fields are complete for CI consumers.
        enriched = []
        for item in generations:
            record = GenerationRecord.model_validate(item)
            if not record.prompt_hash and item.get("question"):
                # Best-effort hash of question+ids when prompt text is not stored.
                material = (
                    f"{record.model}|{record.question_id}|"
                    f"{','.join(record.retrieved_chunk_ids)}|{record.answer}"
                )
                record = record.model_copy(update={"prompt_hash": _prompt_hash(material)})
            payload = record.model_dump()
            payload["cited_article_nums"] = list(record.cited_ids)
            enriched.append(payload)

        out_name = f"generations_{name}{args.suffix}.json"
        out_path = fixtures_dir / out_name
        envelope = {
            "config": name,
            "chunk_size": size,
            "model": args.model,
            "generations": enriched,
        }
        out_path.write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Wrote {len(enriched)} GenerationRecord fixtures → {out_path}")
        all_metrics.append(metrics)

    if args.write_baseline:
        baseline_path = Path(config["report"]["baseline_path"])
        if args.suffix:
            baseline_path = baseline_path.with_name(
                baseline_path.stem + args.suffix + baseline_path.suffix
            )
        baseline_path.write_text(
            json.dumps(baseline_payload(all_metrics), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Wrote baseline → {baseline_path}")

    print("Done. Commit fixtures when ready; do not run this script in CI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
