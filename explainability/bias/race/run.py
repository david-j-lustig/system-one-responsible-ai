"""Toggle person.race on decision cases; write a CSV of answers."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from pathlib import Path

from system_one.cases import CASE_SETS, CASES, Case
from system_one.client import FakeTypeSafeClient, TypesafeClient
from system_one.config import REPO_ROOT, load_settings
from system_one.perturbation import DEFAULT_BATCH_SIZE, run_cases, write_results_csv
from system_one.values import RACE_VALUES

RESULTS_DIR = REPO_ROOT / "explainability" / "bias" / "race" / "results"


def default_output(*, when: datetime | None = None) -> Path:
    stamp = (when or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return RESULTS_DIR / f"race_perturbation_{stamp}.csv"


def _case_ids(cases: tuple[Case, ...]) -> str:
    return ", ".join(case.id for case in cases)


def _help_epilog() -> str:
    lines = [
        "Case sets (choose at least one; --all runs every set):",
        *[f"  --{name:<12} {_case_ids(cases)}" for name, cases in CASE_SETS.items()],
        f"  {'--all':<12} {_case_ids(CASES)}",
    ]
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=_help_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    for name, cases in CASE_SETS.items():
        parser.add_argument(
            f"--{name}",
            action="store_true",
            help=f"Run {name} cases ({_case_ids(cases)})",
        )
    parser.add_argument(
        "--all",
        action="store_true",
        help=f"Run every case set ({_case_ids(CASES)})",
    )
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
        help=(
            "CSV path (default: "
            "explainability/bias/race/results/race_perturbation_<timestamp>.csv)"
        ),
    )
    args = parser.parse_args(argv)
    if args.output is None:
        args.output = default_output()
    if not args.all and not any(getattr(args, name) for name in CASE_SETS):
        sets = ", ".join(f"--{name}" for name in CASE_SETS)
        parser.error(f"choose a case set: {sets}, or --all")
    return args


def selected_cases(args: argparse.Namespace) -> tuple[Case, ...]:
    if args.all:
        return CASES
    chosen: list[Case] = []
    for name, cases in CASE_SETS.items():
        if getattr(args, name):
            chosen.extend(cases)
    return tuple(chosen)


async def run(args: argparse.Namespace) -> Path:
    settings = load_settings()
    if args.dry_run:
        client: FakeTypeSafeClient | TypesafeClient = FakeTypeSafeClient()
    else:
        if not settings.typesafe_api_key:
            raise SystemExit(
                "Set TYPESAFE_API_KEY in .env (see .env.example). Use --dry-run to skip the API."
            )
        client = TypesafeClient(api_key=settings.typesafe_api_key)

    cases = selected_cases(args)
    async with client:
        frame = await run_cases(
            cases,
            "race",
            RACE_VALUES,
            client,
            batch_size=args.batch_size,
        )
    path = write_results_csv(frame, args.output)
    print(f"Wrote {len(frame)} rows ({_case_ids(cases)}) to {path}")
    return path


def main(argv: list[str] | None = None) -> None:
    asyncio.run(run(parse_args(argv)))


if __name__ == "__main__":
    main()
