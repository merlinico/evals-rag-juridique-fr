from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any

import httpx

from rag_juridique.contracts.generation import GenerationFixture, GenerationRecord
from rag_juridique.contracts.retrieval import RetrievedChunk
from rag_juridique.generation.prompt import build_rag_prompt

# Back-compat for prompt / callers still typing RetrievalResult.
RetrievalResult = RetrievedChunk


@dataclass
class GenerationResult:
    question_id: str
    question: str
    answer: str
    cited_article_nums: list[str]
    retrieved_article_ids: list[str]
    retrieved_chunk_ids: list[str]
    model: str
    prompt: str
    abstained: bool


class OllamaGenerator:
    def __init__(
        self,
        model: str = "qwen2.5:3b-instruct",
        base_url: str = "http://127.0.0.1:11434",
        temperature: float = 0.0,
        timeout: float = 180.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.timeout = timeout

    def generate(
        self,
        question_id: str,
        question: str,
        hits: list[RetrievedChunk],
    ) -> GenerationResult:
        prompt = build_rag_prompt(question, hits)
        answer = self._complete(prompt)
        cited = extract_citations(answer)
        abstained = is_abstention(answer)
        return GenerationResult(
            question_id=question_id,
            question=question,
            answer=answer.strip(),
            cited_article_nums=cited,
            retrieved_article_ids=[h.chunk.article_id for h in hits],
            retrieved_chunk_ids=[h.chunk.chunk_id for h in hits],
            model=self.model,
            prompt=prompt,
            abstained=abstained,
        )

    def _complete(self, prompt: str) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": 256,
            },
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
        return str(data.get("response") or "")


def is_abstention(answer: str) -> bool:
    normalized = " ".join(answer.lower().split())
    return "je ne sais pas" in normalized


def extract_citations(answer: str) -> list[str]:
    """Extract article numbers like L. 111-1 / L.111-1 / article L111-1."""
    patterns = [
        r"\b([LRD]\.?\s*\d+(?:-\d+)*(?:-\d+)?)\b",
        r"\barticle\s+([LRD]\.?\s*\d+(?:-\d+)*)\b",
    ]
    found: list[str] = []
    seen: set[str] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, answer, flags=re.IGNORECASE):
            raw = match.group(1)
            norm = _normalize_article_num(raw)
            if norm not in seen:
                seen.add(norm)
                found.append(norm)
    return found


def _normalize_article_num(raw: str) -> str:
    s = raw.strip().upper().replace(" ", "")
    m = re.match(r"^([LRD])\.?(\d.*)$", s, flags=re.IGNORECASE)
    if not m:
        return raw.strip()
    return f"{m.group(1).upper()}. {m.group(2)}"


def generation_to_dict(result: GenerationResult) -> dict[str, Any]:
    return asdict(result)


def load_generation_records(path: str) -> list[GenerationRecord]:
    """Load fixtures as typed GenerationRecord (legacy MVP files supported)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "generations" in data:
        fixture = GenerationFixture.model_validate(data)
        return fixture.generations
    if isinstance(data, list):
        return [GenerationRecord.model_validate(item) for item in data]
    raise ValueError(f"Unexpected fixture format in {path}")


def load_generation_fixture(path: str) -> list[dict[str, Any]]:
    """Back-compat: return plain dicts (cited_article_nums preserved)."""
    records = load_generation_records(path)
    out: list[dict[str, Any]] = []
    for record in records:
        item = record.model_dump()
        item["cited_article_nums"] = list(record.cited_ids)
        out.append(item)
    return out
