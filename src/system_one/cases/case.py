"""Shared case type."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from typesafe_sdk import Choice, Noul, Score

from system_one.profile import PersonProfile


@dataclass(frozen=True)
class Case:
    id: str
    description: str
    person: PersonProfile
    questions: Mapping[str, Noul | Choice | Score]

    def state_for(self, person: PersonProfile | None = None) -> dict[str, Any]:
        profile = self.person if person is None else person
        fields = {
            key: "" if value is None else value for key, value in profile.model_dump().items()
        }
        return {
            "description": self.description.format(**fields),
            "person": profile.dumped(),
        }
