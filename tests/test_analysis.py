"""Case-level Noul deltas vs White, Jev variability, and the analysis CLI."""

from pathlib import Path

import pandas as pd
import pytest

from explainability.bias.race.analyze import parse_args, run
from system_one.analysis import (
    format_summary,
    jev_pairwise_deviations,
    noul_deltas,
    plot_noul_deltas,
    summarize_deltas,
)
from system_one.perturbation import OMITTED_VALUE


def _rows(*, repeats: int = 1) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for case_id, omitted, white, black in (
        ("case_a", 0.50, 0.60, 0.40),
        ("case_b", 0.40, 0.55, 0.35),
    ):
        for repeat in range(repeats):
            bump = 0.02 * repeat
            for value, noul in (
                (OMITTED_VALUE, omitted + bump),
                ("White", white + bump),
                ("Black or African American", black + bump),
            ):
                records.append(
                    {
                        "case_id": case_id,
                        "field": "race",
                        "value": value,
                        "repeat": repeat,
                        "question": "approve",
                        "type": "noul",
                        "noul": noul,
                        "error": None,
                    }
                )
    return pd.DataFrame(records)


def test_each_case_is_paired_to_its_own_baseline() -> None:
    deltas = noul_deltas(_rows(), baseline=OMITTED_VALUE).set_index(["case_id", "value"])["delta"]
    assert deltas.loc[("case_a", "White")] == pytest.approx(0.10)
    assert deltas.loc[("case_b", "White")] == pytest.approx(0.15)
    assert deltas.loc[("case_a", "Black or African American")] == pytest.approx(-0.10)
    assert deltas.loc[("case_b", "Black or African American")] == pytest.approx(-0.05)


def test_repeats_are_averaged_before_pairing() -> None:
    deltas = noul_deltas(_rows(repeats=2), baseline=OMITTED_VALUE)
    white = deltas.loc[deltas["value"].eq("White")]
    assert len(white) == 2
    assert set(white["case_id"]) == {"case_a", "case_b"}
    assert white.loc[white["case_id"].eq("case_a"), "delta"].iloc[0] == pytest.approx(0.10)


def test_summary_is_over_cases_not_draws() -> None:
    summary = summarize_deltas(noul_deltas(_rows(repeats=2), baseline="White"))
    omitted = summary.loc[summary["value"].eq(OMITTED_VALUE)].iloc[0]
    assert omitted["n"] == 2
    assert omitted["repeats"] == 2
    assert omitted["mean_delta"] == pytest.approx(-0.125)
    text = format_summary(summary)
    assert "2 cases" in text
    assert "2 Jev draws averaged per case" in text
    assert "95% CI" in text


def test_jev_pairs_draws_of_the_same_case() -> None:
    white_a = jev_pairwise_deviations(_rows(repeats=2))
    white_a = white_a.loc[white_a["case_id"].eq("case_a") & white_a["value"].eq("White")].iloc[0]
    assert white_a["n_draws"] == 2
    assert white_a["mean_abs_diff"] == pytest.approx(0.02)


def test_plot_writes_png(tmp_path: Path) -> None:
    summary = summarize_deltas(noul_deltas(_rows(), baseline="White"))
    path = plot_noul_deltas(summary, tmp_path / "noul.png", title="Diff vs White")
    assert path.exists()
    assert path.stat().st_size > 0


def test_cli_writes_vs_white_and_jev_plots(tmp_path: Path) -> None:
    csv = tmp_path / "race_perturbation_20260919-142109.csv"
    _rows(repeats=2).to_csv(csv, index=False)
    args = parse_args([str(csv)])
    assert args.output == tmp_path / "race_perturbation_20260919-142109_noul_vs_white.png"
    run(args)
    assert args.output.exists()
    assert (tmp_path / "race_perturbation_20260919-142109_jev_variability.png").exists()
