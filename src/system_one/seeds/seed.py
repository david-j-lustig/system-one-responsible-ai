"""A Noul question plus an ordered ladder of situation frames."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from typesafe_sdk import Noul

UNSAFE_TARGETS = (0.0, 1.0)


@dataclass(frozen=True)
class Frame:
    id: str
    description: str
    question: str | None = None


@dataclass(frozen=True)
class Seed:
    id: str
    category: str
    question: str
    questions: Mapping[str, Noul]
    unsafe_target: float
    frames: tuple[Frame, ...]

    def __post_init__(self) -> None:
        if self.unsafe_target not in UNSAFE_TARGETS:
            raise ValueError(f"unsafe_target must be 0.0 or 1.0, got {self.unsafe_target}")
        if self.question not in self.questions:
            raise ValueError(f"question {self.question!r} is not in questions")
        if not self.frames:
            raise ValueError("frames must be nonempty")

    def state_for(self, frame: Frame) -> dict[str, Any]:
        return {"description": frame.description}

    def questions_for(self, frame: Frame | None = None) -> dict[str, Noul]:
        questions = dict(self.questions)
        if frame is None or not frame.question:
            return questions
        base = self.questions[self.question]
        questions[self.question] = Noul(
            instructions=frame.question,
            criteria=base.criteria,
        )
        return questions
