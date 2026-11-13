"""Generation fixture contracts (heavy GPU runs cached outside CI)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GenerationRecord(BaseModel):
    """One cached generation used as a CI fixture.

    Required logical fields: question_id, config_id, model, prompt_hash,
    answer, cited ids, abstained. Legacy MVP fixtures omit config_id /
    prompt_hash / cited_ids — validators fill defaults from existing keys.
    """

    model_config = ConfigDict(extra="ignore")

    question_id: str
    config_id: str = Field(
        default="unknown",
        description="Eval config id, e.g. chunk_500 or hybrid+rerank",
    )
    model: str
    prompt_hash: str = Field(
        default="",
        description="sha256 of the exact prompt; empty for legacy fixtures",
    )
    answer: str
    cited_ids: list[str] = Field(
        default_factory=list,
        description="Cited article numbers (display ids) or LEGIARTI ids",
    )
    abstained: bool = False
    # Optional diagnostics kept for MVP compatibility / debugging
    question: str | None = None
    retrieved_article_ids: list[str] = Field(default_factory=list)
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    chunk_size: int | None = None

    @model_validator(mode="before")
    @classmethod
    def _legacy_aliases(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        if "cited_ids" not in out and "cited_article_nums" in out:
            out["cited_ids"] = list(out.get("cited_article_nums") or [])
        if "config_id" not in out:
            if out.get("chunk_size") is not None:
                out["config_id"] = f"chunk_{out['chunk_size']}"
            elif out.get("config"):
                out["config_id"] = str(out["config"])
        return out

    @property
    def cited_article_nums(self) -> list[str]:
        """Back-compat alias used by the MVP faithfulness path."""
        return self.cited_ids


class GenerationFixture(BaseModel):
    """File envelope for `data/fixtures/generations_*.json`."""

    model_config = ConfigDict(extra="ignore")

    config: str | None = None
    chunk_size: int | None = None
    model: str | None = None
    generations: list[GenerationRecord]
