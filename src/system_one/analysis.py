"""Noul perturbation analysis: per-case deltas, CIs, and Jev variability."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_NOUL_COLUMNS = ("case_id", "field", "value", "question", "type", "noul", "error")
_CELL_KEYS = ("case_id", "field", "value", "question")
_PAIR_KEYS = ("case_id", "field", "question")
_Z95 = 1.959963984540054


def sample_size_note(n: int, repeats: int) -> str:
    word = "replicate" if repeats == 1 else "replicates"
    return f"n = {n} cases, {repeats} Jev {word}"


def noul_rows(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in _NOUL_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"CSV is missing columns: {', '.join(missing)}")
    rows = frame.loc[
        frame["type"].eq("noul") & frame["error"].isna() & frame["noul"].notna()
    ].copy()
    rows["noul"] = rows["noul"].astype(float)
    if "repeat" not in rows.columns:
        rows["repeat"] = 0
    return rows


def case_nouls(rows: pd.DataFrame) -> pd.DataFrame:
    """Mean Noul per case, field, value, and question (averages Jev draws)."""
    return rows.groupby(list(_CELL_KEYS), sort=False, as_index=False).agg(
        noul=("noul", "mean"),
        repeats=("repeat", "nunique"),
    )


def paired_deltas(rows: pd.DataFrame, baseline: str) -> pd.DataFrame:
    """Diff each other value to `baseline` on the same case and question."""
    keys = list(_PAIR_KEYS)
    reference = rows.loc[rows["value"].eq(baseline), [*keys, "noul"]].rename(
        columns={"noul": "reference"}
    )
    if reference.empty:
        raise ValueError(f"no Noul rows for baseline {baseline!r}")
    others = rows.loc[~rows["value"].eq(baseline)]
    if others.empty:
        raise ValueError(f"no non-{baseline!r} Noul rows to compare")
    merged = others.merge(reference, on=keys, how="inner")
    if merged.empty:
        raise ValueError(f"no rows share a {baseline!r} Noul baseline")
    merged["delta"] = merged["noul"] - merged["reference"]
    merged["baseline"] = baseline
    return merged


def noul_deltas(frame: pd.DataFrame, *, baseline: str) -> pd.DataFrame:
    return paired_deltas(case_nouls(noul_rows(frame)), baseline)


def mean_se_ci(values: pd.Series) -> tuple[float, float, float]:
    """Mean of case-level diffs with a 95% interval from the SE."""
    sample = np.asarray(values, dtype=float)
    mean = float(sample.mean())
    if sample.size < 2:
        return mean, mean, mean
    se = float(sample.std(ddof=1) / np.sqrt(sample.size))
    return mean, mean - _Z95 * se, mean + _Z95 * se


def summarize_deltas(deltas: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    grouped = deltas.groupby(["field", "question", "baseline", "value"], sort=False)
    for (field, question, baseline, value), group in grouped:
        mean, lo95, hi95 = mean_se_ci(group["delta"])
        repeats = int(group["repeats"].iloc[0]) if "repeats" in group.columns else 1
        rows.append(
            {
                "field": field,
                "question": question,
                "value": value,
                "baseline": baseline,
                "n": len(group),
                "repeats": repeats,
                "mean_delta": mean,
                "ci95_low": lo95,
                "ci95_high": hi95,
            }
        )
    return pd.DataFrame(rows)


def _signed(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.3f}"


def format_summary(summary: pd.DataFrame) -> str:
    lines: list[str] = []
    for (field, question, baseline), group in summary.groupby(
        ["field", "question", "baseline"], sort=False
    ):
        n = int(group["n"].iloc[0])
        repeats = int(group["repeats"].iloc[0])
        header = f"{field} / {question}: Noul − {baseline} across {n} cases"
        if repeats > 1:
            header += f" ({repeats} Jev draws averaged per case)"
        lines.append(header)
        lines.append(f"  {'':<42} {'mean':>7}  {'95% CI':^21}")
        for row in group.itertuples():
            ci95 = f"[{_signed(row.ci95_low)}, {_signed(row.ci95_high)}]"
            lines.append(f"  {row.value:<42} {_signed(row.mean_delta):>7}  {ci95:^21}")
        lines.append("")
    lines.append("CIs are mean ± z·SE of case-level diffs.")
    lines.append("Positive means more yes than the baseline on that same case.")
    return "\n".join(lines)


def _mean_pairwise_abs(values: np.ndarray) -> float:
    n = values.size
    diffs = np.abs(values[:, None] - values[None, :])
    return float(diffs[np.triu_indices(n, k=1)].mean())


def jev_pairwise_deviations(rows: pd.DataFrame) -> pd.DataFrame:
    """Pair draws of the same case, value, and question; mean |Noul_i − Noul_j|."""
    records: list[dict[str, object]] = []
    grouped = rows.groupby(list(_CELL_KEYS), sort=False)
    for (case_id, field, value, question), group in grouped:
        values = group["noul"].to_numpy(dtype=float)
        if values.size < 2:
            continue
        records.append(
            {
                "case_id": case_id,
                "field": field,
                "value": value,
                "question": question,
                "n_draws": int(values.size),
                "mean_abs_diff": _mean_pairwise_abs(values),
            }
        )
    return pd.DataFrame(records)


def format_jev(deviations: pd.DataFrame) -> str:
    lines: list[str] = []
    for (field, question), by_question in deviations.groupby(["field", "question"], sort=False):
        n = int(by_question["case_id"].nunique())
        draws = int(by_question["n_draws"].iloc[0])
        lines.append(
            f"{field} / {question}: Jev variability on identical cases ({draws} draws, {n} cases)"
        )
        lines.append(f"  {'':<42} {'mean |i−j|':>11}")
        for value, group in by_question.groupby("value", sort=False):
            mean = float(group["mean_abs_diff"].mean())
            lines.append(f"  {value:<42} {mean:11.3f}")
        lines.append("")
    lines.append("Each case/value is paired across its Jev draws; |Noul_i − Noul_j| is averaged.")
    return "\n".join(lines)


def plot_noul_deltas(summary: pd.DataFrame, path: Path, *, title: str) -> Path:
    values = list(summary["value"])
    y = np.arange(len(values))
    mean = summary["mean_delta"].to_numpy()
    err95 = np.vstack(
        [mean - summary["ci95_low"].to_numpy(), summary["ci95_high"].to_numpy() - mean]
    )
    height = max(5.0, 0.32 * len(values) + 1.8)
    fig, ax = plt.subplots(figsize=(8.2, height))
    ax.axvline(0, color="0.35", linewidth=1.2)
    ax.errorbar(mean, y, xerr=err95, fmt="o", capsize=4, color="C0", linewidth=2.2)
    ax.set_yticks(y, values)
    ax.set_ylim(len(values) - 0.5, -0.5)
    ax.grid(True, axis="both", color="0.9")
    ax.set_axisbelow(True)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    note = sample_size_note(int(summary["n"].iloc[0]), int(summary["repeats"].iloc[0]))
    ax.set_title(f"{title}\n{note}")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_jev_variability(
    deviations: pd.DataFrame, path: Path, *, title: str = "Jev variability on identical cases"
) -> Path:
    order = list(deviations["value"].drop_duplicates())
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    rng = np.random.default_rng(0)
    for index, value in enumerate(order):
        xs = deviations.loc[deviations["value"].eq(value), "mean_abs_diff"].to_numpy()
        jitter = rng.uniform(-0.18, 0.18, size=len(xs))
        ax.scatter(xs, np.full(len(xs), index) + jitter, s=16, color="0.55", alpha=0.45, zorder=1)
        ax.scatter(xs.mean(), index, s=72, color="C0", marker="D", zorder=3)
    ax.scatter([], [], s=72, color="C0", marker="D", label="mean across cases")
    ax.set_yticks(np.arange(len(order)), order)
    ax.set_ylim(len(order) - 0.5, -0.5)
    ax.grid(True, axis="both", color="0.9")
    ax.set_axisbelow(True)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    ax.set_xlabel("Mean |Noul_i − Noul_j| across Jev draws")
    note = sample_size_note(
        int(deviations["case_id"].nunique()),
        int(deviations["n_draws"].iloc[0]),
    )
    ax.set_title(f"{title}\n{note}")
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.02, 1.0))
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
