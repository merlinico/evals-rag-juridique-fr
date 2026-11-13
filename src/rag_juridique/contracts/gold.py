"""Gold-set contracts: typed questions for evaluation."""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class QuestionType(str, Enum):
    """Five gold question types for phase 2."""

    DIRECT = "direct"
    MULTI_HOP = "multi_hop"
    TEMPORAL = "temporal"
    UNANSWERABLE = "unanswerable"
    APPARENT_CONTRADICTION = "apparent_contradiction"


class Question(BaseModel):
    """One gold question.

    `expected_article_ids` are the gold passage ids (LEGIARTI). For temporal
    questions, `as_of` selects the article version in force at that date.
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    question: str
    type: QuestionType = QuestionType.DIRECT
    expected_article_ids: list[str] = Field(default_factory=list)
    expected_article_nums: list[str] = Field(default_factory=list)
    reference_answer: str | None = None
    as_of: date | None = Field(
        default=None,
        description="For temporal questions: date at which the answer must hold",
    )
    unanswerable: bool = False
    validated: bool = False
    topic: str | None = None
    notes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _infer_type_from_legacy(cls, data: object) -> object:
        """MVP gold JSON has `unanswerable` but no `type`; infer defaults."""
        if not isinstance(data, dict):
            return data
        out = dict(data)
        if "type" not in out:
            if out.get("unanswerable"):
                out["type"] = QuestionType.UNANSWERABLE.value
            else:
                out["type"] = QuestionType.DIRECT.value
        if out.get("type") == QuestionType.UNANSWERABLE.value:
            out["unanswerable"] = True
        return out


class GoldSet(BaseModel):
    """Container matching `data/gold/questions.json`."""

    model_config = ConfigDict(extra="ignore")

    version: str = "0.1.0"
    corpus_snapshot: str | None = None
    language: str = "fr"
    validated: bool = False
    notes: str | None = None
    questions: list[Question]
