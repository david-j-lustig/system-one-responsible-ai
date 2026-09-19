"""Shared case type and yes/no Choice criteria."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from typesafe_sdk import Choice, Noul, Score

from system_one.profile import PersonProfile

YES_NO = {
    "yes": "The answer is yes.",
    "no": "The answer is no.",
}


@dataclass(frozen=True)
class Case:
    id: str
    description: str
    person: PersonProfile
    questions: Mapping[str, Noul | Choice | Score]

    def state_for(self, person: PersonProfile | None = None) -> dict[str, Any]:
        profile = self.person if person is None else person
        return {
            "case_id": self.id,
            "description": self.description,
            "person": profile.dumped(),
        }
