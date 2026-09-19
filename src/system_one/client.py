"""Async TypeSafe System One client and a deterministic fake for tests."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from typesafe_sdk import Choice, Noul, Score


@dataclass(frozen=True)
class NoulResult:
    noul: float


@dataclass(frozen=True)
class ChoiceResult:
    choice: str
    probabilities: dict[str, float]
    confidence: float


@dataclass(frozen=True)
class ScoreResult:
    score: float
    confidence: float


@dataclass(frozen=True)
class SystemOneResult:
    model: str
    nouls: dict[str, NoulResult] = field(default_factory=dict)
    choices: dict[str, ChoiceResult] = field(default_factory=dict)
    scores: dict[str, ScoreResult] = field(default_factory=dict)


class SystemOneClient(Protocol):
    async def system_one(
        self,
        state: Any,
        questions: Mapping[str, Any],
    ) -> SystemOneResult: ...


def result_from_sdk(response: Any) -> SystemOneResult:
    nouls = {
        name: NoulResult(noul=float(answer.noul))
        for name, answer in dict(getattr(response, "nouls", None) or {}).items()
    }
    choices = {
        name: ChoiceResult(
            choice=str(answer.choice),
            probabilities=dict(getattr(answer, "probabilities", None) or {}),
            confidence=float(answer.confidence),
        )
        for name, answer in dict(getattr(response, "choices", None) or {}).items()
    }
    scores = {
        name: ScoreResult(
            score=float(answer.score),
            confidence=float(answer.confidence),
        )
        for name, answer in dict(getattr(response, "scores", None) or {}).items()
    }
    return SystemOneResult(model=str(response.model), nouls=nouls, choices=choices, scores=scores)


class TypesafeClient:
    """Thin async wrapper around `AsyncTypeSafeClient`."""

    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key
        self._model = model
        self._client: Any = None

    async def __aenter__(self) -> TypesafeClient:
        from typesafe_sdk import AsyncTypeSafeClient

        kwargs: dict[str, Any] = {}
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._model:
            kwargs["model"] = self._model
        self._client = AsyncTypeSafeClient(**kwargs)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client is not None:
            await self._client.__aexit__(*exc)
        self._client = None

    async def system_one(self, state: Any, questions: Mapping[str, Any]) -> SystemOneResult:
        if self._client is None:
            raise RuntimeError("TypesafeClient must be used as an async context manager")
        response = await self._client.system_one(state=state, questions=questions)
        return result_from_sdk(response)


def _question_type(question: Any) -> str:
    if isinstance(question, dict):
        return str(question["type"])
    return str(question.type)


def _choice_criteria(question: Any) -> Mapping[str, Any]:
    if isinstance(question, dict):
        return question["criteria"]
    return question.criteria


def _score_criteria(question: Any) -> list[Any]:
    if isinstance(question, dict):
        return list(question["criteria"])
    return list(question.criteria)


def _noul_for_race(race: object) -> float:
    if race is None:
        return 0.50
    lookup = {
        "unknown": 0.48,
        "White": 0.40,
        "Black or African American": 0.70,
        "Asian": 0.45,
        "Hispanic or Latino": 0.55,
        "American Indian or Alaska Native": 0.52,
        "Native Hawaiian or Other Pacific Islander": 0.47,
    }
    if isinstance(race, str) and race in lookup:
        return lookup[race]
    return 0.50


class FakeTypeSafeClient:
    """Deterministic client keyed by `state['person']['race']`. No network."""

    def __init__(self, *, delay: float = 0.0) -> None:
        self.delay = delay
        self.calls: list[tuple[Any, Mapping[str, Any]]] = []
        self.in_flight = 0
        self.max_in_flight = 0

    async def __aenter__(self) -> FakeTypeSafeClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def system_one(self, state: Any, questions: Mapping[str, Any]) -> SystemOneResult:
        self.calls.append((state, questions))
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        if self.delay:
            await asyncio.sleep(self.delay)
        else:
            await asyncio.sleep(0)
        self.in_flight -= 1

        person = state.get("person") if isinstance(state, dict) else {}
        race = person.get("race") if isinstance(person, dict) else None
        noul = _noul_for_race(race)
        p_yes = noul
        p_no = 1.0 - noul
        choice = "yes" if noul >= 0.5 else "no"
        confidence = abs(noul - 0.5) * 2

        nouls: dict[str, NoulResult] = {}
        choices: dict[str, ChoiceResult] = {}
        scores: dict[str, ScoreResult] = {}
        for name, question in questions.items():
            kind = _question_type(question)
            if kind == "noul" or isinstance(question, Noul):
                nouls[name] = NoulResult(noul=noul)
            elif kind == "choice" or isinstance(question, Choice):
                probabilities = {str(label): 0.0 for label in _choice_criteria(question)}
                probabilities["yes"] = p_yes
                probabilities["no"] = p_no
                choices[name] = ChoiceResult(
                    choice=choice,
                    probabilities=probabilities,
                    confidence=confidence,
                )
            elif kind == "score" or isinstance(question, Score):
                levels = max(len(_score_criteria(question)) - 1, 0)
                scores[name] = ScoreResult(score=noul * levels, confidence=confidence)
            else:
                raise ValueError(f"Unknown question type: {kind}")
        return SystemOneResult(model="fake", nouls=nouls, choices=choices, scores=scores)
