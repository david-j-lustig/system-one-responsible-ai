"""Run a one-field perturbation study against a System One client."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from itertools import batched
from pathlib import Path
from typing import Any

import pandas as pd

from system_one.cases import Case
from system_one.client import SystemOneClient, SystemOneResult
from system_one.profile import PersonProfile

DEFAULT_BATCH_SIZE = 10
DEFAULT_REPEATS = 1
OMITTED_VALUE = "omitted"

_COLUMNS = (
    "case_id",
    "field",
    "value",
    "repeat",
    "model",
    "question",
    "type",
    "noul",
    "answer",
    "error",
)


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _base(case_id: str, field: str, value: Any, repeat: int = 0) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "field": field,
        "value": OMITTED_VALUE if value is None else value,
        "repeat": repeat,
        "model": None,
        "question": None,
        "type": None,
        "noul": None,
        "answer": None,
        "error": None,
    }


def _rows(
    case_id: str, field: str, value: Any, result: SystemOneResult, *, repeat: int = 0
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, answer in result.nouls.items():
        row = _base(case_id, field, value, repeat)
        row.update(model=result.model, question=name, type="noul", noul=answer.noul)
        rows.append(row)
    for name, answer in result.choices.items():
        row = _base(case_id, field, value, repeat)
        row.update(
            model=result.model,
            question=name,
            type="choice",
            answer=_json(
                {
                    "choice": answer.choice,
                    "confidence": answer.confidence,
                    "probabilities": answer.probabilities,
                }
            ),
        )
        rows.append(row)
    for name, answer in result.scores.items():
        row = _base(case_id, field, value, repeat)
        row.update(
            model=result.model,
            question=name,
            type="score",
            answer=_json(
                {
                    "confidence": answer.confidence,
                    "legend": {str(level): label for level, label in answer.legend.items()},
                    "probabilities": {
                        str(level): prob for level, prob in answer.probabilities.items()
                    },
                    "score": answer.score,
                }
            ),
        )
        rows.append(row)
    return rows


def _error_row(
    case_id: str, field: str, value: Any, error: BaseException, *, repeat: int = 0
) -> dict[str, Any]:
    row = _base(case_id, field, value, repeat)
    row["error"] = f"{type(error).__name__}: {error}"
    return row


def _jobs(
    cases: Sequence[Case],
    field: str,
    values: Sequence[Any],
    *,
    repeats: int = DEFAULT_REPEATS,
) -> list[tuple[Case, str, Any, int, dict[str, Any]]]:
    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    jobs: list[tuple[Case, str, Any, int, dict[str, Any]]] = []
    for case in cases:
        for value in values:
            person: PersonProfile = case.person.model_copy(update={field: value})
            state = case.state_for(person)
            for repeat in range(repeats):
                jobs.append((case, field, value, repeat, state))
    return jobs


async def _run_jobs(
    jobs: Sequence[tuple[Case, str, Any, int, dict[str, Any]]],
    client: SystemOneClient,
    batch_size: int,
) -> pd.DataFrame:
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")

    rows: list[dict[str, Any]] = []
    for chunk in batched(jobs, batch_size):
        batch = list(chunk)
        results = await asyncio.gather(
            *[
                client.system_one(state, case.questions)
                for case, _field, _value, _repeat, state in batch
            ],
            return_exceptions=True,
        )
        for (case, field, value, repeat, _state), result in zip(batch, results, strict=True):
            if isinstance(result, BaseException):
                rows.append(_error_row(case.id, field, value, result, repeat=repeat))
            else:
                rows.extend(_rows(case.id, field, value, result, repeat=repeat))
    return pd.DataFrame(rows, columns=_COLUMNS)


async def run_perturbation(
    case: Case,
    field: str,
    values: Sequence[Any],
    client: SystemOneClient,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    repeats: int = DEFAULT_REPEATS,
) -> pd.DataFrame:
    return await _run_jobs(_jobs((case,), field, values, repeats=repeats), client, batch_size)


def write_results_csv(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


async def run_cases(
    cases: Sequence[Case],
    field: str,
    values: Sequence[Any],
    client: SystemOneClient,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    repeats: int = DEFAULT_REPEATS,
) -> pd.DataFrame:
    return await _run_jobs(_jobs(cases, field, values, repeats=repeats), client, batch_size)
