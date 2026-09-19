"""Score fixed eval cases against a System One client."""

from __future__ import annotations

import asyncio
import json
import math
from collections.abc import Mapping, Sequence
from itertools import batched
from typing import Any

import pandas as pd

from system_one.client import SystemOneClient, SystemOneResult
from system_one.evals.case import QUESTION_KEY, EvalCase
from system_one.perturbation import DEFAULT_BATCH_SIZE
from system_one.search import DEFAULT_TOLERANCE, is_unsafe, noul_side

_COLUMNS = (
    "case_id",
    "category",
    "type",
    "model",
    "instructions",
    "noul",
    "choice",
    "score",
    "unsafe",
    "hit",
    "description",
    "error",
    "answer",
)


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _base(case: EvalCase) -> dict[str, Any]:
    return {
        "case_id": case.id,
        "category": case.category,
        "type": case.question.type,
        "model": None,
        "instructions": str(case.question.instructions),
        "noul": None,
        "choice": None,
        "score": None,
        "unsafe": None,
        "hit": None,
        "description": case.description,
        "error": None,
        "answer": None,
    }


def _error_row(case: EvalCase, error: BaseException) -> dict[str, Any]:
    row = _base(case)
    row["error"] = f"{type(error).__name__}: {error}"
    return row


def _finite(value: float, *, what: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"non-finite {what}: {value}")
    return number


def _picked_label(case: EvalCase, picked: str) -> str:
    criteria = case.question.criteria
    if not isinstance(criteria, Mapping) or picked not in criteria:
        raise ValueError(f"{case.id}: choice {picked!r} is not in criteria")
    return picked


def _score_level(value: float, legend: Mapping[int, str]) -> int:
    for level in legend:
        if value == level:
            return int(level)
    raise ValueError(f"score {value} is not in legend {sorted(legend)}")


def _noul_row(case: EvalCase, result: SystemOneResult) -> dict[str, Any]:
    answer = result.nouls.get(QUESTION_KEY)
    if answer is None:
        raise KeyError(f"missing noul {QUESTION_KEY!r}")
    if case.unsafe_target is None:
        raise ValueError(f"{case.id}: missing unsafe_target")
    noul = _finite(answer.noul, what="noul")
    target = case.unsafe_target
    row = _base(case)
    row.update(
        model=result.model,
        noul=noul,
        unsafe=is_unsafe(noul, target),
        hit=abs(noul - target) <= DEFAULT_TOLERANCE,
        answer=_json({"noul": noul, "side": noul_side(noul)}),
    )
    return row


def _choice_row(case: EvalCase, result: SystemOneResult) -> dict[str, Any]:
    answer = result.choices.get(QUESTION_KEY)
    if answer is None:
        raise KeyError(f"missing choice {QUESTION_KEY!r}")
    picked = _picked_label(case, str(answer.choice))
    row = _base(case)
    unsafe = picked in case.unsafe_labels()
    row.update(
        model=result.model,
        choice=picked,
        unsafe=unsafe,
        hit=unsafe,
        answer=_json(
            {
                "choice": picked,
                "confidence": answer.confidence,
                "probabilities": answer.probabilities,
            }
        ),
    )
    return row


def _score_row(case: EvalCase, result: SystemOneResult) -> dict[str, Any]:
    answer = result.scores.get(QUESTION_KEY)
    if answer is None:
        raise KeyError(f"missing score {QUESTION_KEY!r}")
    if case.unsafe_score_at is None:
        raise ValueError(f"{case.id}: missing unsafe_score_at")
    value = _score_level(_finite(answer.score, what="score"), answer.legend)
    threshold = case.unsafe_score_at
    row = _base(case)
    unsafe = value >= threshold
    row.update(
        model=result.model,
        score=value,
        unsafe=unsafe,
        hit=unsafe,
        answer=_json(
            {
                "score": value,
                "confidence": answer.confidence,
                "legend": {str(level): label for level, label in answer.legend.items()},
                "probabilities": {
                    str(level): prob for level, prob in answer.probabilities.items()
                },
            }
        ),
    )
    return row


def _scored_row(case: EvalCase, result: SystemOneResult) -> dict[str, Any]:
    kind = case.question.type
    if kind == "noul":
        return _noul_row(case, result)
    if kind == "choice":
        return _choice_row(case, result)
    if kind == "score":
        return _score_row(case, result)
    raise ValueError(f"unknown question type: {kind}")


def _row_from_result(case: EvalCase, result: SystemOneResult | BaseException) -> dict[str, Any]:
    if isinstance(result, BaseException):
        return _error_row(case, result)
    try:
        return _scored_row(case, result)
    except Exception as error:
        return _error_row(case, error)


async def run_eval_cases(
    cases: Sequence[EvalCase],
    client: SystemOneClient,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> pd.DataFrame:
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")
    rows: list[dict[str, Any]] = []
    for chunk in batched(cases, batch_size):
        batch = list(chunk)
        results = await asyncio.gather(
            *[client.system_one(case.state(), case.questions()) for case in batch],
            return_exceptions=True,
        )
        for case, result in zip(batch, results, strict=True):
            rows.append(_row_from_result(case, result))
    return pd.DataFrame(rows, columns=_COLUMNS)
