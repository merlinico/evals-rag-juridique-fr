"""Export Pydantic models to JSON Schema files under ``schemas/``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rag_juridique.contracts.chunking import Chunk
from rag_juridique.contracts.corpus import Article, ArticleVersion, CrossRef
from rag_juridique.contracts.generation import GenerationFixture, GenerationRecord
from rag_juridique.contracts.gold import GoldSet, Question
from rag_juridique.contracts.metrics import MetricReport, MetricResult, PerConfigMetrics
from rag_juridique.contracts.retrieval import RetrievedChunk

# Logical name -> model (also documents the frozen surface).
SCHEMA_MODELS: dict[str, type[Any]] = {
    "Article": Article,
    "ArticleVersion": ArticleVersion,
    "CrossRef": CrossRef,
    "Question": Question,
    "GoldSet": GoldSet,
    "Chunk": Chunk,
    "RetrievedChunk": RetrievedChunk,
    "GenerationRecord": GenerationRecord,
    "GenerationFixture": GenerationFixture,
    "MetricResult": MetricResult,
    "PerConfigMetrics": PerConfigMetrics,
    "MetricReport": MetricReport,
}


def default_schemas_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "schemas"


def export_schemas(out_dir: Path | str | None = None) -> list[Path]:
    """Write one JSON Schema file per contract model. Returns written paths."""
    target = Path(out_dir) if out_dir else default_schemas_dir()
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, model in SCHEMA_MODELS.items():
        path = target / f"{name}.json"
        schema = model.model_json_schema()
        path.write_text(
            json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return written


def main() -> None:
    paths = export_schemas()
    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
