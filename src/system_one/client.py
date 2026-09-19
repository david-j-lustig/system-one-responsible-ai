"""Async TypeSafe System One client and a deterministic fake for tests."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from typesafe_sdk import AsyncTypeSafeClient


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
    legend: dict[int, str]
    probabilities: dict[int, float]


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
        for name, answer in dict(response.nouls).items()
    }
    choices = {
        name: ChoiceResult(
            choice=str(answer.choice),
            probabilities=dict(answer.probabilities),
            confidence=float(answer.confidence),
        )
        for name, answer in dict(response.choices).items()
    }
    scores = {
        name: ScoreResult(
            score=float(answer.score),
            confidence=float(answer.confidence),
            legend={int(level): str(label) for level, label in dict(answer.legend).items()},
            probabilities={
                int(level): float(prob) for level, prob in dict(answer.probabilities).items()
            },
        )
        for name, answer in dict(response.scores).items()
    }
    return SystemOneResult(model=str(response.model), nouls=nouls, choices=choices, scores=scores)


class TypesafeClient:
    """Thin async wrapper around `AsyncTypeSafeClient`."""

    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key
        self._model = model
        self._client: AsyncTypeSafeClient | None = None

    async def __aenter__(self) -> TypesafeClient:
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


class FakeTypeSafeClient:
    """Deterministic in-memory client. No network."""

    def __init__(
        self,
        *,
        delay: float = 0.0,
        fail_when: Callable[[Any], bool] | None = None,
    ) -> None:
        self.delay = delay
        self.fail_when = fail_when
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
        self.in_flight -= 1
        if self.fail_when is not None and self.fail_when(state):
            raise RuntimeError("fake client failure")

        nouls: dict[str, NoulResult] = {}
        choices: dict[str, ChoiceResult] = {}
        scores: dict[str, ScoreResult] = {}
        for name, question in questions.items():
            kind = question.type
            if kind == "noul":
                nouls[name] = NoulResult(noul=0.5)
            elif kind == "choice":
                labels = [str(label) for label in question.criteria]
                probabilities = dict.fromkeys(labels, 0.0)
                pick = labels[0] if labels else "yes"
                probabilities[pick] = 1.0
                choices[name] = ChoiceResult(
                    choice=pick,
                    probabilities=probabilities,
                    confidence=1.0,
                )
            elif kind == "score":
                legend = {index: str(label) for index, label in enumerate(question.criteria)}
                n = len(legend) or 1
                probabilities = {index: 1.0 / n for index in legend}
                scores[name] = ScoreResult(
                    score=1.0,
                    confidence=0.5,
                    legend=legend,
                    probabilities=probabilities,
                )
            else:
                raise ValueError(f"Unknown question type: {kind}")
        return SystemOneResult(model="fake", nouls=nouls, choices=choices, scores=scores)
