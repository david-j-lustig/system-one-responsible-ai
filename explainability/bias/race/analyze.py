"""Summarize case-level Noul vs White, plus Jev variability when there are repeats."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from system_one.analysis import (
    case_nouls,
    format_jev,
    format_summary,
    jev_pairwise_deviations,
    noul_rows,
    paired_deltas,
    plot_jev_variability,
    plot_noul_deltas,
    summarize_deltas,
)
from system_one.config import REPO_ROOT

RESULTS_DIR = REPO_ROOT / "explainability" / "bias" / "race" / "results"
PAIR_REFERENCE = "White"
APPROVE_QUESTION = "approve"
DELTA_TITLE = 'Diff in p(loan approval) compared to Race "white" (95% CI)'
JEV_TITLE = "Jev variability on identical cases"


def latest_results(directory: Path = RESULTS_DIR) -> Path:
    matches = sorted(directory.glob("race_perturbation_*.csv"))
    if not matches:
        raise SystemExit(f"No race_perturbation_*.csv files in {directory}")
    return matches[-1]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        type=Path,
        nargs="?",
        default=None,
        help="Perturbation CSV (default: newest race_perturbation_*.csv in results/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Plot path (default: <input stem>_noul_vs_white.png)",
    )
    args = parser.parse_args(argv)
    if args.input is None:
        args.input = latest_results()
    if args.output is None:
        args.output = args.input.with_name(f"{args.input.stem}_noul_vs_white.png")
    return args


def _select_rows(frame: pd.DataFrame) -> pd.DataFrame:
    rows = noul_rows(frame)
    if APPROVE_QUESTION in set(rows["question"]):
        return rows.loc[rows["question"].eq(APPROVE_QUESTION)]
    return rows


def _jev_plot_path(output: Path) -> Path:
    stem = output.stem.removesuffix("_noul_vs_white")
    return output.with_name(f"{stem}_jev_variability.png")


def run(args: argparse.Namespace) -> Path:
    rows = _select_rows(pd.read_csv(args.input))
    if PAIR_REFERENCE not in set(rows["value"]):
        raise SystemExit(f"CSV has no {PAIR_REFERENCE!r} Noul rows")
    summary = summarize_deltas(paired_deltas(case_nouls(rows), PAIR_REFERENCE))
    print(format_summary(summary))
    path = plot_noul_deltas(summary, args.output, title=DELTA_TITLE)
    print(f"Wrote {path}")
    jev = jev_pairwise_deviations(rows)
    if not jev.empty:
        print(format_jev(jev))
        print(f"Wrote {plot_jev_variability(jev, _jev_plot_path(args.output), title=JEV_TITLE)}")
    return path


def main(argv: list[str] | None = None) -> None:
    run(parse_args(argv))


if __name__ == "__main__":
    main()
