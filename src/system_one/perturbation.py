"""Run a one-field perturbation study against a System One client."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from itertools import batched
from pathlib import Path
from typing import Any

import pandas as pd

from system_one.cases import Case
from system_one.client import SystemOneClient, SystemOneResult
from system_one.profile import PersonProfile

DEFAULT_BATCH_SIZE = 10
OMITTED_VALUE = "omitted"


def _row(case_id: str, field: str, value: Any, result: SystemOneResult) -> dict[str, Any]:
    row: dict[str, Any] = {
        "case_id": case_id,
        "field": field,
        "value": OMITTED_VALUE if value is None else value,
        "model": result.model,
    }
    for name, answer in result.nouls.items():
        row[f"{name}_noul"] = answer.noul
    for name, answer in result.choices.items():
        row[f"{name}_choice"] = answer.choice
        row[f"{name}_p_yes"] = answer.probabilities.get("yes")
    for name, answer in result.scores.items():
        row[f"{name}_score"] = answer.score
        row[f"{name}_confidence"] = answer.confidence
    return row


def _jobs(
    cases: Sequence[Case],
    field: str,
    values: Sequence[Any],
) -> list[tuple[Case, str, Any, dict[str, Any]]]:
    jobs: list[tuple[Case, str, Any, dict[str, Any]]] = []
    for case in cases:
        for value in values:
            person: PersonProfile = case.person.model_copy(update={field: value})
            jobs.append((case, field, value, case.state_for(person)))
    return jobs


async def _run_jobs(
    jobs: Sequence[tuple[Case, str, Any, dict[str, Any]]],
    client: SystemOneClient,
    batch_size: int,
) -> pd.DataFrame:
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")

    rows: list[dict[str, Any]] = []
    for chunk in batched(jobs, batch_size):
        batch = list(chunk)
        results = await asyncio.gather(
            *[client.system_one(state, case.questions) for case, _field, _value, state in batch]
        )
        for (case, field, value, _state), result in zip(batch, results, strict=True):
            rows.append(_row(case.id, field, value, result))
    return pd.DataFrame(rows)


async def run_perturbation(
    case: Case,
    field: str,
    values: Sequence[Any],
    client: SystemOneClient,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> pd.DataFrame:
    return await _run_jobs(_jobs((case,), field, values), client, batch_size)


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
) -> pd.DataFrame:
    return await _run_jobs(_jobs(cases, field, values), client, batch_size)
