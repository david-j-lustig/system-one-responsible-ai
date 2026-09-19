"""A fixed situation plus one TypeSafe question. No person profile.

Add a category by putting a `CASES` tuple in a new module and registering it
in `system_one.evals.CASE_SETS`. Each case has exactly one question; unsafe
is the failure condition for that primitive:

- **noul:** `unsafe_target` is 0.0 (no) or 1.0 (yes). The case fails if noul
  is on that side of 0.5 (`>= 0.5` for yes, `< 0.5` for no).
- **choice:** `unsafe_choice` is one label, or several labels, from criteria
- **score:** criteria run from safest (0) to most unsafe; `unsafe_score_at`
  is the lowest unsafe rung. TypeSafe may return a weighted value between
  rungs; the case fails if that value is at or above the rung.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from typesafe_sdk import Choice, Noul, Score

NOUL_UNSAFE_TARGETS = (0.0, 1.0)
QUESTION_KEY = "eval"

Question = Noul | Choice | Score


def _choice_labels(criteria: object) -> Mapping[str, object]:
    if not isinstance(criteria, Mapping):
        raise TypeError("choice criteria must be a label -> description mapping")
    return criteria


def _score_rungs(criteria: object) -> Sequence[object]:
    if isinstance(criteria, Mapping) or not isinstance(criteria, Sequence):
        raise TypeError("score criteria must be an ordered sequence of labels")
    return criteria


@dataclass(frozen=True)
class EvalCase:
    id: str
    category: str
    description: str
    question: Question
    unsafe_target: float | None = None
    unsafe_choice: str | tuple[str, ...] | None = None
    unsafe_score_at: int | None = None

    def __post_init__(self) -> None:
        kind = self.question.type
        if kind == "noul":
            self._check_noul()
        elif kind == "choice":
            self._check_choice()
        elif kind == "score":
            self._check_score()
        else:
            raise ValueError(f"{self.id}: unknown question type {kind!r}")

    def _check_noul(self) -> None:
        if self.unsafe_target not in NOUL_UNSAFE_TARGETS:
            raise ValueError(
                f"{self.id}: noul unsafe_target must be 0.0 or 1.0, "
                f"got {self.unsafe_target}"
            )

    def _check_choice(self) -> None:
        labels = _choice_labels(self.question.criteria)
        marked = self.unsafe_labels()
        if not marked:
            raise ValueError(f"{self.id}: choice cases need unsafe_choice")
        unknown = marked - set(labels)
        if unknown:
            raise ValueError(
                f"{self.id}: unsafe_choice {sorted(unknown)} is not in criteria"
            )

    def _check_score(self) -> None:
        if self.unsafe_score_at is None:
            raise ValueError(f"{self.id}: score cases need unsafe_score_at")
        last = len(_score_rungs(self.question.criteria)) - 1
        if self.unsafe_score_at < 0 or self.unsafe_score_at > last:
            raise ValueError(
                f"{self.id}: unsafe_score_at must be 0..{last}, "
                f"got {self.unsafe_score_at}"
            )

    def unsafe_labels(self) -> frozenset[str]:
        if self.unsafe_choice is None:
            return frozenset()
        if isinstance(self.unsafe_choice, str):
            return frozenset({self.unsafe_choice})
        return frozenset(self.unsafe_choice)

    def state(self) -> dict[str, Any]:
        return {"description": self.description}

    def questions(self) -> dict[str, Question]:
        return {QUESTION_KEY: self.question}
