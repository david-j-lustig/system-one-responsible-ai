"""CLI seed-set selection."""

from __future__ import annotations

from pathlib import Path

import pytest

from stress_tests.harm.run import parse_args, selected_seeds
from system_one.search import DEFAULT_PARENTS
from system_one.seeds import SEED_SETS, SEEDS


def test_selected_sets_and_defaults() -> None:
    assert selected_seeds(parse_args(["--all"])) == SEEDS
    assert selected_seeds(parse_args(["--self-harm"])) == SEED_SETS["self_harm"]
    args = parse_args(["--self-harm", "--violence"])
    assert selected_seeds(args) == (*SEED_SETS["self_harm"], *SEED_SETS["violence"])
    assert args.mutate is False
    assert args.parents == DEFAULT_PARENTS


def test_mutate_flag_rules(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        parse_args(["--dry-run"])
    with pytest.raises(SystemExit):
        parse_args(["--all", "--sweep", "--mutate"])
    prior = tmp_path / "prior.json"
    prior.write_text("[]\n")
    args = parse_args(["--self-harm", "--from-json", str(prior)])
    assert args.mutate is True
    assert args.from_json == prior
