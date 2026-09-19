"""Gender-via-name ticket perturbation: names, corpus, runner, analysis, CLI."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from explainability.bias.gender.analyze import (
    group_names,
    name_deltas_vs_neutral,
    name_deltas_vs_peers,
)
from explainability.bias.gender.analyze import parse_args as parse_analyze
from explainability.bias.gender.analyze import run as run_analyze
from explainability.bias.gender.run import (
    PILOT_CASE_COUNT,
    default_output,
    parse_args,
    selected_cases,
    selected_names,
)
from explainability.bias.gender.run import run as run_gender
from system_one.analysis import case_nouls, noul_deltas
from system_one.cases.ticket_source import ensure_tickets
from system_one.cases.tickets import CASES as TICKET_CASES
from system_one.client import FakeTypeSafeClient
from system_one.perturbation import run_perturbation
from system_one.values import (
    FEMININE_NAMES,
    GENDER_NEUTRAL_NAMES,
    MASCULINE_NAMES,
    NAME_GENDER,
    NAME_VALUES,
    PILOT_NAMES,
)

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]\d{4}\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def test_name_lists_are_ten_each_and_disjoint() -> None:
    assert len(FEMININE_NAMES) == 10
    assert len(MASCULINE_NAMES) == 10
    assert len(GENDER_NEUTRAL_NAMES) == 10
    assert len(NAME_VALUES) == 30
    assert len(set(NAME_VALUES)) == 30
    assert set(FEMININE_NAMES).isdisjoint(MASCULINE_NAMES)
    assert set(FEMININE_NAMES).isdisjoint(GENDER_NEUTRAL_NAMES)
    assert set(MASCULINE_NAMES).isdisjoint(GENDER_NEUTRAL_NAMES)


def test_pilot_names_are_two_from_each_gender_group() -> None:
    assert PILOT_NAMES == ("Emily", "Jessica", "Taylor", "Jordan", "James", "Michael")
    groups = [NAME_GENDER[name] for name in PILOT_NAMES]
    assert groups.count("feminine") == 2
    assert groups.count("masculine") == 2
    assert groups.count("gender_neutral") == 2
    assert set(NAME_GENDER) == set(NAME_VALUES)


def test_ticket_corpus_is_two_hundred_unique_signoff_templates() -> None:
    assert len(TICKET_CASES) == 200
    assert len({case.id for case in TICKET_CASES}) == 200
    for case in TICKET_CASES:
        assert "{name}" in case.description
        assert case.description.endswith("Thanks, {name}.")
        assert "person" in case.questions
        assert case.questions["person"].type == "noul"
        assert case.person.name is None
        assert case.person.gender is None
        assert not _EMAIL.search(case.description)
        assert not _PHONE.search(case.description)
        assert not _SSN.search(case.description)


def test_name_perturbation_fills_signoff_and_omits_gender() -> None:
    async def _run() -> None:
        client = FakeTypeSafeClient()
        case = TICKET_CASES[0]
        frame = await run_perturbation(case, "name", ["Emily"], client, batch_size=10)
        assert list(frame["type"].unique()) == ["noul"]
        assert list(frame["question"].unique()) == ["person"]
        state, questions = client.calls[0]
        assert state["description"].endswith("Thanks, Emily.")
        assert "{name}" not in state["description"]
        assert state["person"] == {"name": "Emily"}
        assert "gender" not in state["person"]
        assert "person" in questions

    asyncio.run(_run())


def _grouped_rows() -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for case_id, feminine, masculine, neutral in (
        ("t1", 0.70, 0.40, 0.50),
        ("t2", 0.60, 0.45, 0.55),
    ):
        for names, noul in (
            (FEMININE_NAMES, feminine),
            (MASCULINE_NAMES, masculine),
            (GENDER_NEUTRAL_NAMES, neutral),
        ):
            for name in names:
                records.append(
                    {
                        "case_id": case_id,
                        "field": "name",
                        "value": name,
                        "repeat": 0,
                        "question": "person",
                        "type": "noul",
                        "noul": noul,
                        "error": None,
                    }
                )
    return pd.DataFrame(records)


def test_group_names_averages_ten_names_per_gender() -> None:
    grouped = group_names(_grouped_rows())
    assert set(grouped["value"]) == {"feminine", "masculine", "gender_neutral"}
    means = case_nouls(grouped)
    t1 = means.loc[means["case_id"].eq("t1")].set_index("value")["noul"]
    assert t1["feminine"] == pytest.approx(0.70)
    assert t1["masculine"] == pytest.approx(0.40)
    assert t1["gender_neutral"] == pytest.approx(0.50)
    deltas = noul_deltas(grouped, baseline="gender_neutral")
    deltas = deltas.set_index(["case_id", "value"])["delta"]
    assert deltas.loc[("t1", "feminine")] == pytest.approx(0.20)
    assert deltas.loc[("t1", "masculine")] == pytest.approx(-0.10)


def test_name_deltas_are_vs_neutral_group_mean() -> None:
    deltas = name_deltas_vs_neutral(_grouped_rows())
    t1 = deltas.loc[deltas["case_id"].eq("t1")].set_index("value")["delta"]
    assert t1["Emily"] == pytest.approx(0.20)
    assert t1["James"] == pytest.approx(-0.10)
    assert t1["Taylor"] == pytest.approx(0.0)


def test_name_deltas_are_vs_mean_of_other_names() -> None:
    deltas = name_deltas_vs_peers(_grouped_rows())
    t1 = deltas.loc[deltas["case_id"].eq("t1")].set_index("value")["delta"]
    emily_others = (9 * 0.70 + 10 * 0.40 + 10 * 0.50) / 29
    taylor_others = (10 * 0.70 + 10 * 0.40 + 9 * 0.50) / 29
    assert t1["Emily"] == pytest.approx(0.70 - emily_others)
    assert t1["Taylor"] == pytest.approx(0.50 - taylor_others)


def test_default_cli_is_pilot() -> None:
    args = parse_args([])
    assert selected_cases(args) == TICKET_CASES[:PILOT_CASE_COUNT]
    assert selected_names(args) == PILOT_NAMES
    assert args.repeats == 3
    all_args = parse_args(["--all-tickets", "--all-names"])
    assert selected_cases(all_args) == TICKET_CASES
    assert selected_names(all_args) == NAME_VALUES
    assert all_args.repeats == 1
    assert selected_cases(parse_args(["--limit", "4"])) == TICKET_CASES[:4]


def test_default_output_is_timestamped() -> None:
    path = default_output(when=datetime(2026, 9, 19, 16, 20, 0))
    assert path.name == "gender_perturbation_20260919-162000.csv"
    args = parse_args([])
    assert args.output.name.startswith("gender_perturbation_")
    assert args.output.suffix == ".csv"


def test_dry_run_and_analyze_write_outputs(tmp_path: Path) -> None:
    csv = tmp_path / "gender_perturbation_20260919-162000.csv"
    asyncio.run(run_gender(parse_args(["--dry-run", "--output", str(csv)])))
    assert csv.exists()
    frame = pd.read_csv(csv)
    assert set(frame["value"]) == set(PILOT_NAMES)
    assert list(frame["question"].unique()) == ["person"]
    plot = tmp_path / "gender_perturbation_20260919-162000_person_vs_neutral.png"
    run_analyze(parse_analyze([str(csv), "--output", str(plot)]))
    assert plot.exists()
    assert plot.stat().st_size > 0
    by_name = tmp_path / "gender_perturbation_20260919-162000_person_vs_neutral_by_name.png"
    assert by_name.exists()
    assert by_name.stat().st_size > 0
    vs_peers = tmp_path / "gender_perturbation_20260919-162000_person_vs_peers_by_name.png"
    assert vs_peers.exists()
    assert vs_peers.stat().st_size > 0


def test_ensure_tickets_skips_download_when_cache_exists(tmp_path: Path) -> None:
    cache = tmp_path / "tickets.json"
    cache.write_text("[]\n")
    assert ensure_tickets(cache) == cache
    assert cache.read_text() == "[]\n"


def test_ensure_tickets_writes_missing_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = tmp_path / "data" / "tickets.json"

    def fake_write(path=cache, *, source=None):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('[{"id": "TCK-1"}]\n')
        return path

    monkeypatch.setattr("system_one.cases.ticket_source.write_snapshot", fake_write)
    assert ensure_tickets(cache) == cache
    assert cache.exists()
    assert "TCK-1" in cache.read_text()
