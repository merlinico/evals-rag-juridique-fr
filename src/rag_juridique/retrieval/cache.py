"""On-disk embedding cache for optional heavy-model runs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from rag_juridique.contracts.chunking import Chunk


def default_cache_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "fixtures" / "embeddings"


def _key(model_name: str, chunk_ids: list[str]) -> str:
    payload = model_name + "\n" + "\n".join(chunk_ids)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def cache_paths(
    model_name: str,
    chunks: list[Chunk],
    cache_dir: Path | None = None,
) -> tuple[Path, Path]:
    root = cache_dir or default_cache_dir()
    root.mkdir(parents=True, exist_ok=True)
    stem = _key(model_name, [c.chunk_id for c in chunks])
    return root / f"{stem}.npy", root / f"{stem}.meta.json"


def load_cached_embeddings(
    model_name: str,
    chunks: list[Chunk],
    cache_dir: Path | None = None,
) -> np.ndarray | None:
    npy_path, meta_path = cache_paths(model_name, chunks, cache_dir)
    if not npy_path.is_file() or not meta_path.is_file():
        return None
    meta: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("model_name") != model_name:
        return None
    if meta.get("chunk_ids") != [c.chunk_id for c in chunks]:
        return None
    arr = np.load(npy_path)
    if arr.shape[0] != len(chunks):
        return None
    return np.asarray(arr, dtype=np.float32)


def save_cached_embeddings(
    model_name: str,
    chunks: list[Chunk],
    embeddings: np.ndarray,
    cache_dir: Path | None = None,
) -> Path:
    npy_path, meta_path = cache_paths(model_name, chunks, cache_dir)
    np.save(npy_path, np.asarray(embeddings, dtype=np.float32))
    meta = {
        "model_name": model_name,
        "chunk_ids": [c.chunk_id for c in chunks],
        "shape": list(np.asarray(embeddings).shape),
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return npy_path
