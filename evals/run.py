"""Score a small fixed set of eval cases."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from pathlib import Path

import pandas as pd

from system_one.client import FakeTypeSafeClient, SystemOneClient, TypesafeClient
from system_one.config import REPO_ROOT, Settings, load_settings
from system_one.evals import CASE_SETS, CASES, EvalCase
from system_one.evals.score import run_eval_cases
from system_one.perturbation import DEFAULT_BATCH_SIZE, write_results_csv

RESULTS_DIR = REPO_ROOT / "evals" / "results"


def default_output(*, when: datetime | None = None) -> Path:
    stamp = (when or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return RESULTS_DIR / f"eval_{stamp}.csv"


def flag_for(name: str) -> str:
    return name.replace("_", "-")


def _case_ids(cases: tuple[EvalCase, ...]) -> str:
    return ", ".join(case.id for case in cases)


def _add_set_flags(parser: argparse.ArgumentParser) -> None:
    for name, cases in CASE_SETS.items():
        parser.add_argument(
            f"--{flag_for(name)}",
            dest=name,
            action="store_true",
            help=f"Run {flag_for(name)} evals ({_case_ids(cases)})",
        )
    parser.add_argument(
        "--all",
        action="store_true",
        help=f"Run every eval case ({_case_ids(CASES)})",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    _add_set_flags(parser)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use the fake client instead of calling TypeSafe",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Parallel TypeSafe requests per batch (default {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV path (default: evals/results/eval_<timestamp>.csv)",
    )
    args = parser.parse_args(argv)
    if args.output is None:
        args.output = default_output()
    if not args.all and not any(getattr(args, name) for name in CASE_SETS):
        args.all = True
    return args


def selected_cases(args: argparse.Namespace) -> tuple[EvalCase, ...]:
    if args.all:
        return CASES
    chosen: list[EvalCase] = []
    for name, cases in CASE_SETS.items():
        if getattr(args, name):
            chosen.extend(cases)
    return tuple(chosen)


def _client(args: argparse.Namespace, settings: Settings) -> SystemOneClient:
    if args.dry_run:
        return FakeTypeSafeClient()
    if not settings.typesafe_api_key:
        raise SystemExit(
            "Set TYPESAFE_API_KEY in .env (see .env.example). "
            "Use --dry-run to skip the API."
        )
    return TypesafeClient(api_key=settings.typesafe_api_key)


def _result_text(row: pd.Series) -> str:
    kind = row["type"]
    if kind == "noul":
        return f"noul={row['noul']:.2f}"
    if kind == "choice":
        return f"choice={row['choice']}"
    if kind == "score":
        return f"score={row['score']:.2f}"
    return str(kind)


def _summarize(frame: pd.DataFrame) -> str:
    lines: list[str] = []
    for _, row in frame.iterrows():
        case_id = row["case_id"]
        if pd.notna(row["error"]):
            lines.append(f"{case_id}: error {row['error']}")
            continue
        unsafe = "unsafe" if bool(row["unsafe"]) else "safe"
        lines.append(f"{case_id}: {row['type']} {_result_text(row)} ({unsafe})")
    return "\n".join(lines)


async def run(args: argparse.Namespace) -> Path:
    settings = load_settings()
    client = _client(args, settings)
    cases = selected_cases(args)
    async with client:
        frame = await run_eval_cases(cases, client, batch_size=args.batch_size)
    path = write_results_csv(frame, args.output)
    print(f"Wrote {len(frame)} rows ({_case_ids(cases)}) to {path}")
    summary = _summarize(frame)
    if summary:
        print(summary)
    return path


def main(argv: list[str] | None = None) -> None:
    asyncio.run(run(parse_args(argv)))


if __name__ == "__main__":
    main()
