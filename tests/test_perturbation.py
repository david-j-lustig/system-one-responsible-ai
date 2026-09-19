"""Batched perturbation runner and CSV output."""

from __future__ import annotations

import asyncio
from pathlib import Path

from system_one.cases.criminal import CASES as CRIMINAL_CASES
from system_one.cases.financial import CASES as FINANCIAL_CASES
from system_one.client import FakeTypeSafeClient
from system_one.perturbation import OMITTED_VALUE, run_cases, run_perturbation, write_results_csv
from system_one.values import RACE_VALUES


def test_runner_one_row_per_value_and_omitted_baseline() -> None:
    async def _run() -> None:
        client = FakeTypeSafeClient()
        values = [None, "unknown", "White"]
        frame = await run_perturbation(CRIMINAL_CASES[0], "race", values, client, batch_size=10)
        assert list(frame["value"]) == [OMITTED_VALUE, "unknown", "White"]
        assert list(frame["case_id"]) == ["criminal_guilt"] * 3
        assert list(frame["field"]) == ["race"] * 3
        assert "guilty_noul" in frame.columns
        assert "find_guilty_choice" in frame.columns
        assert "find_guilty_p_yes" in frame.columns
        assert "punishment_score" in frame.columns
        assert "punishment_confidence" in frame.columns
        assert frame.loc[frame["value"] == "White", "guilty_noul"].iloc[0] == 0.40
        people = [call[0]["person"] for call in client.calls]
        assert people[0] == {"name": "Alex Jordan"}
        assert people[1] == {"name": "Alex Jordan", "race": "unknown"}
        assert people[2] == {"name": "Alex Jordan", "race": "White"}

    asyncio.run(_run())


def test_runner_respects_batch_size() -> None:
    async def _run() -> None:
        client = FakeTypeSafeClient(delay=0.01)
        values = ["a", "b", "c", "d", "e"]
        await run_perturbation(CRIMINAL_CASES[0], "race", values, client, batch_size=2)
        assert client.max_in_flight == 2
        assert len(client.calls) == 5

    asyncio.run(_run())


def test_run_cases_and_csv(tmp_path: Path) -> None:
    async def _run() -> None:
        client = FakeTypeSafeClient(delay=0.01)
        frame = await run_cases(
            (*CRIMINAL_CASES, *FINANCIAL_CASES),
            "race",
            RACE_VALUES,
            client,
            batch_size=10,
        )
        assert len(frame) == len(RACE_VALUES) * 2
        assert set(frame["case_id"]) == {"criminal_guilt", "mortgage_approval"}
        assert client.max_in_flight == 10
        path = write_results_csv(frame, tmp_path / "results" / "race_perturbation.csv")
        assert path.exists()
        text = path.read_text()
        assert "criminal_guilt" in text
        assert "mortgage_approval" in text
        assert OMITTED_VALUE in text

    asyncio.run(_run())
