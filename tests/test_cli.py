"""CLI dry-run writes a CSV."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from system_one.config import REPO_ROOT


def _load_run():
    path = REPO_ROOT / "explainability" / "bias" / "race" / "run.py"
    spec = importlib.util.spec_from_file_location("race_perturbation_run", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_all_flag_runs_every_set(tmp_path: Path) -> None:
    run = _load_run()
    output = tmp_path / "out.csv"
    run.main(["--dry-run", "--all", "--output", str(output), "--batch-size", "10"])
    assert output.exists()
    text = output.read_text()
    assert "criminal_guilt" in text
    assert "mortgage_approval" in text
    assert "omitted" in text


def test_criminal_flag_runs_only_criminal(tmp_path: Path) -> None:
    run = _load_run()
    output = tmp_path / "criminal.csv"
    run.main(["--dry-run", "--criminal", "--output", str(output)])
    text = output.read_text()
    assert "criminal_guilt" in text
    assert "mortgage_approval" not in text


def test_financial_flag_runs_only_financial(tmp_path: Path) -> None:
    run = _load_run()
    output = tmp_path / "financial.csv"
    run.main(["--dry-run", "--financial", "--output", str(output)])
    text = output.read_text()
    assert "mortgage_approval" in text
    assert "criminal_guilt" not in text


def test_missing_case_set_asks_what_to_run(capsys: pytest.CaptureFixture[str]) -> None:
    run = _load_run()
    with pytest.raises(SystemExit) as exc:
        run.parse_args(["--dry-run"])
    assert exc.value.code == 2
    text = capsys.readouterr().err
    assert "choose a case set" in text
    assert "--criminal" in text
    assert "--financial" in text
    assert "--all" in text


def test_help_lists_case_sets(capsys: pytest.CaptureFixture[str]) -> None:
    run = _load_run()
    with pytest.raises(SystemExit) as exc:
        run.parse_args(["--help"])
    assert exc.value.code == 0
    text = capsys.readouterr().out
    assert "--criminal" in text
    assert "criminal_guilt" in text
    assert "--financial" in text
    assert "mortgage_approval" in text
    assert "--all" in text
    assert "choose at least one" in text
