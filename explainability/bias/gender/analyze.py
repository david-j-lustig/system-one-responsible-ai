"""Summarize Noul vs gender-neutral names, plus Jev variability when there are repeats."""

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
from system_one.values import NAME_GENDER, NAME_VALUES

RESULTS_DIR = REPO_ROOT / "explainability" / "bias" / "gender" / "results"
PAIR_REFERENCE = "gender_neutral"
PERSON_QUESTION = "person"
DELTA_TITLE = "Diff in p(person should handle) vs gender-neutral names (95% CI)"
NAME_DELTA_TITLE = "Diff in p(person should handle) vs gender-neutral names, by name (95% CI)"
PEER_DELTA_TITLE = "Diff in p(person should handle) vs mean of other names (95% CI)"
JEV_TITLE = "Jev variability on identical cases"


def latest_results(directory: Path = RESULTS_DIR) -> Path:
    matches = sorted(directory.glob("gender_perturbation_*.csv"))
    if not matches:
        raise SystemExit(f"No gender_perturbation_*.csv files in {directory}")
    return matches[-1]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        type=Path,
        nargs="?",
        default=None,
        help="Perturbation CSV (default: newest gender_perturbation_*.csv in results/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Plot path (default: <input stem>_person_vs_neutral.png)",
    )
    args = parser.parse_args(argv)
    if args.input is None:
        args.input = latest_results()
    if args.output is None:
        args.output = args.input.with_name(f"{args.input.stem}_person_vs_neutral.png")
    return args


def _select_rows(frame: pd.DataFrame) -> pd.DataFrame:
    rows = noul_rows(frame)
    if PERSON_QUESTION in set(rows["question"]):
        return rows.loc[rows["question"].eq(PERSON_QUESTION)]
    return rows


def group_names(rows: pd.DataFrame) -> pd.DataFrame:
    """Replace each first name with its gender group before averaging."""
    grouped = rows.copy()
    grouped["name"] = grouped["value"]
    grouped["value"] = grouped["value"].map(NAME_GENDER)
    missing = grouped.loc[grouped["value"].isna(), "name"].dropna().unique().tolist()
    if missing:
        names = sorted(str(name) for name in missing)
        raise SystemExit(f"CSV has names not in NAME_GENDER: {names}")
    return grouped


def name_deltas_vs_neutral(rows: pd.DataFrame) -> pd.DataFrame:
    """Diff each first name to the gender-neutral name mean on the same ticket."""
    cells = case_nouls(rows).copy()
    cells["group"] = cells["value"].map(NAME_GENDER)
    missing = cells.loc[cells["group"].isna(), "value"].dropna().unique().tolist()
    if missing:
        names = sorted(str(name) for name in missing)
        raise SystemExit(f"CSV has names not in NAME_GENDER: {names}")
    keys = ["case_id", "field", "question"]
    reference = (
        cells.loc[cells["group"].eq(PAIR_REFERENCE)]
        .groupby(keys, sort=False, as_index=False)
        .agg(reference=("noul", "mean"))
    )
    if reference.empty:
        raise SystemExit(f"CSV has no {PAIR_REFERENCE!r} Noul rows")
    merged = cells.merge(reference, on=keys, how="inner")
    merged["delta"] = merged["noul"] - merged["reference"]
    merged["baseline"] = PAIR_REFERENCE
    return merged


def name_deltas_vs_peers(rows: pd.DataFrame) -> pd.DataFrame:
    """Diff each first name to the mean of the other names on the same ticket."""
    cells = case_nouls(rows)
    keys = ["case_id", "field", "question"]
    totals = cells.groupby(keys, sort=False, as_index=False).agg(
        total=("noul", "sum"),
        n_names=("noul", "size"),
    )
    merged = cells.merge(totals, on=keys, how="inner")
    others = merged["n_names"] - 1
    if (others < 1).any():
        raise SystemExit("need at least two names per case to compare against other names")
    merged["reference"] = (merged["total"] - merged["noul"]) / others
    merged["delta"] = merged["noul"] - merged["reference"]
    merged["baseline"] = "other names"
    return merged


def _sort_names(summary: pd.DataFrame) -> pd.DataFrame:
    order = {name: index for index, name in enumerate(NAME_VALUES)}
    ranked = summary["value"].map(order)
    return summary.loc[ranked.sort_values(kind="stable").index].reset_index(drop=True)


def _jev_plot_path(output: Path) -> Path:
    stem = output.stem.removesuffix("_person_vs_neutral")
    return output.with_name(f"{stem}_jev_variability.png")


def _name_plot_path(output: Path) -> Path:
    stem = output.stem.removesuffix("_person_vs_neutral")
    return output.with_name(f"{stem}_person_vs_neutral_by_name.png")


def _peer_plot_path(output: Path) -> Path:
    stem = output.stem.removesuffix("_person_vs_neutral")
    return output.with_name(f"{stem}_person_vs_peers_by_name.png")


def run(args: argparse.Namespace) -> Path:
    rows = _select_rows(pd.read_csv(args.input))
    grouped = group_names(rows)
    if PAIR_REFERENCE not in set(grouped["value"]):
        raise SystemExit(f"CSV has no {PAIR_REFERENCE!r} Noul rows")
    summary = summarize_deltas(paired_deltas(case_nouls(grouped), PAIR_REFERENCE))
    print(format_summary(summary))
    path = plot_noul_deltas(summary, args.output, title=DELTA_TITLE)
    print(f"Wrote {path}")

    by_name = _sort_names(summarize_deltas(name_deltas_vs_neutral(rows)))
    print(format_summary(by_name))
    name_path = plot_noul_deltas(by_name, _name_plot_path(args.output), title=NAME_DELTA_TITLE)
    print(f"Wrote {name_path}")

    vs_peers = _sort_names(summarize_deltas(name_deltas_vs_peers(rows)))
    print(format_summary(vs_peers))
    peer_path = plot_noul_deltas(vs_peers, _peer_plot_path(args.output), title=PEER_DELTA_TITLE)
    print(f"Wrote {peer_path}")

    jev = jev_pairwise_deviations(rows)
    if not jev.empty:
        print(format_jev(jev))
        print(f"Wrote {plot_jev_variability(jev, _jev_plot_path(args.output), title=JEV_TITLE)}")
    return path


def main(argv: list[str] | None = None) -> None:
    run(parse_args(argv))


if __name__ == "__main__":
    main()
