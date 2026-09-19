"""CLI case-set selection."""

from __future__ import annotations

from datetime import datetime

import pytest

from explainability.bias.race.run import default_output, parse_args, selected_cases
from system_one.cases import CASE_SETS, CASES


def test_selected_sets() -> None:
    assert selected_cases(parse_args(["--all"])) == CASES
    assert selected_cases(parse_args(["--criminal"])) == CASE_SETS["criminal"]
    assert selected_cases(parse_args(["--financial"])) == CASE_SETS["financial"]
    assert selected_cases(parse_args(["--criminal", "--financial"])) == (
        *CASE_SETS["criminal"],
        *CASE_SETS["financial"],
    )


def test_missing_case_set_asks_what_to_run(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        parse_args(["--dry-run"])
    assert exc.value.code == 2
    text = capsys.readouterr().err
    assert "choose a case set" in text
    assert "--criminal" in text
    assert "--financial" in text
    assert "--all" in text


def test_default_repeats_is_one() -> None:
    assert parse_args(["--all"]).repeats == 1
    assert parse_args(["--financial", "--repeats", "3"]).repeats == 3


def test_default_output_is_timestamped() -> None:
    path = default_output(when=datetime(2026, 9, 19, 10, 47, 0))
    assert path.name == "race_perturbation_20260919-104700.csv"
    args = parse_args(["--all"])
    assert args.output.name.startswith("race_perturbation_")
    assert args.output.suffix == ".csv"


def test_help_lists_case_sets(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        parse_args(["--help"])
    assert exc.value.code == 0
    text = capsys.readouterr().out
    assert "--criminal" in text
    assert "--financial" in text
    assert "--all" in text
    assert "choose at least one" in text
    for case in CASES:
        assert case.id in text
