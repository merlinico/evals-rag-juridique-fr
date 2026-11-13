from __future__ import annotations

import json
from pathlib import Path

from rag_juridique.contracts.gold import GoldSet, Question


def load_gold_set(path: Path | str) -> GoldSet:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return GoldSet.model_validate(raw)


def load_gold(path: Path | str) -> list[Question]:
    """Return typed questions (replaces bare dict list in the MVP pipeline)."""
    return load_gold_set(path).questions
