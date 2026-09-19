"""Batched perturbation runner and CSV output."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from system_one.cases import CASES
from system_one.cases.criminal import CASES as CRIMINAL_CASES
from system_one.client import FakeTypeSafeClient
from system_one.perturbation import OMITTED_VALUE, run_cases, run_perturbation, write_results_csv
from system_one.values import RACE_VALUES


def test_runner_one_row_per_question_and_omitted_baseline() -> None:
    async def _run() -> None:
        client = FakeTypeSafeClient()
        values = [None, "unknown", "White"]
        case = CRIMINAL_CASES[0]
        frame = await run_perturbation(case, "race", values, client, batch_size=10)
        assert list(frame["value"].unique()) == [OMITTED_VALUE, "unknown", "White"]
        assert set(frame["type"]) == {"noul", "score"}
        assert set(frame["question"]) == {"guilty", "punishment"}
        assert len(frame) == len(values) * 2
        people = [call[0]["person"] for call in client.calls]
        assert people[0] == {"name": case.person.name}
        assert people[1] == {"name": case.person.name, "race": "unknown"}
        assert people[2] == {"name": case.person.name, "race": "White"}
        assert "case_id" not in client.calls[0][0]
        assert case.person.name in client.calls[0][0]["description"]

    asyncio.run(_run())


def test_runner_respects_batch_size() -> None:
    async def _run() -> None:
        client = FakeTypeSafeClient(delay=0.01)
        values = ["a", "b", "c", "d", "e"]
        await run_perturbation(CRIMINAL_CASES[0], "race", values, client, batch_size=2)
        assert client.max_in_flight == 2
        assert len(client.calls) == 5

    asyncio.run(_run())


def test_failed_call_writes_error_row_and_keeps_others() -> None:
    async def _run() -> None:
        def fail_when(state: object) -> bool:
            return isinstance(state, dict) and (state.get("person") or {}).get("race") == "White"

        client = FakeTypeSafeClient(fail_when=fail_when)
        frame = await run_perturbation(
            CRIMINAL_CASES[0],
            "race",
            [None, "White", "Asian"],
            client,
            batch_size=10,
        )
        errors = frame[frame["error"].notna()]
        ok = frame[frame["error"].isna()]
        assert len(errors) == 1
        assert errors.iloc[0]["value"] == "White"
        assert "RuntimeError" in errors.iloc[0]["error"]
        assert set(ok["value"]) == {OMITTED_VALUE, "Asian"}
        assert set(ok["type"]) == {"noul", "score"}

    asyncio.run(_run())


def test_run_cases_writes_long_csv(tmp_path: Path) -> None:
    async def _run() -> None:
        client = FakeTypeSafeClient()
        frame = await run_cases(CASES, "race", RACE_VALUES, client, batch_size=10)
        expected_rows = sum(len(case.questions) for case in CASES) * len(RACE_VALUES)
        assert len(frame) == expected_rows
        assert list(frame.columns) == [
            "case_id",
            "field",
            "value",
            "model",
            "question",
            "type",
            "noul",
            "answer",
            "error",
        ]
        expected_values = {OMITTED_VALUE if value is None else value for value in RACE_VALUES}
        assert set(frame["value"]) == expected_values
        nouls = frame[frame["type"] == "noul"]
        assert nouls["noul"].notna().all()
        assert nouls["answer"].isna().all()
        scores = frame[frame["type"] == "score"]
        assert scores["noul"].isna().all()
        payloads = [json.loads(payload) for payload in scores["answer"]]
        assert payloads
        assert all("score" in payload and "legend" in payload for payload in payloads)
        legends = [payload["legend"] for payload in payloads]
        assert any("No punishment." in labels.values() for labels in legends)
        assert any("Deny the loan." in labels.values() for labels in legends)
        path = write_results_csv(frame, tmp_path / "results" / "race_perturbation.csv")
        text = path.read_text()
        assert "question" in text
        assert "noul" in text

    asyncio.run(_run())
