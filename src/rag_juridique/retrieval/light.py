"""CPU-light stand-in encoders for CI / unit tests (no model download)."""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np


class HashEncoder:
    """Deterministic bag-of-hashes encoder mimicking SentenceTransformer.encode.

    Used when ``RAG_HEAVY`` is unset so dense / hybrid paths stay offline and
    CPU-light. Not a substitute for real recall numbers on bge-m3.
    """

    def __init__(self, dim: int = 384, model_name: str = "hash-encoder") -> None:
        self.dim = dim
        self.model_name = model_name

    def encode(
        self,
        texts: list[str] | str,
        *,
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
        **_: Any,
    ) -> np.ndarray:
        del show_progress_bar
        if isinstance(texts, str):
            texts = [texts]
        vectors = np.stack([self._embed_one(t) for t in texts], axis=0)
        if normalize_embeddings:
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            norms = np.maximum(norms, 1e-12)
            vectors = vectors / norms
        return vectors.astype(np.float32)

    def _embed_one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = text.lower().split()
        if not tokens:
            tokens = [""]
        for tok in tokens:
            digest = hashlib.sha256(tok.encode("utf-8")).digest()
            # Two hash slots per token (signed).
            for offset in (0, 8):
                idx = int.from_bytes(digest[offset : offset + 4], "little") % self.dim
                sign = 1.0 if digest[offset + 4] % 2 == 0 else -1.0
                vec[idx] += sign
        return vec


def is_heavy_enabled() -> bool:
    """Return True when optional heavy-model path is requested."""
    import os

    return os.environ.get("RAG_HEAVY", "").strip().lower() in {"1", "true", "yes", "on"}
