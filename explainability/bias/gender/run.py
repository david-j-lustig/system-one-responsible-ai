"""Toggle person.name on support tickets; write a CSV of Noul answers.

Default is a 90-call pilot (5 tickets × 6 names × 3 Jev repeats). Pass
--all-tickets --all-names only after the pilot looks right.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from pathlib import Path

from system_one.cases.case import Case
from system_one.cases.tickets import CASES as TICKET_CASES
from system_one.client import FakeTypeSafeClient, TypesafeClient
from system_one.config import REPO_ROOT, load_settings
from system_one.perturbation import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_REPEATS,
    run_cases,
    write_results_csv,
)
from system_one.values import NAME_VALUES, PILOT_NAMES

RESULTS_DIR = REPO_ROOT / "explainability" / "bias" / "gender" / "results"
PILOT_CASE_COUNT = 5
PILOT_REPEATS = 3


def default_output(*, when: datetime | None = None) -> Path:
    stamp = (when or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return RESULTS_DIR / f"gender_perturbation_{stamp}.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--pilot",
        action="store_true",
        help=(
            f"{PILOT_CASE_COUNT} tickets × {len(PILOT_NAMES)} names × "
            f"{PILOT_REPEATS} repeats (default). Ignored if --all-tickets or --all-names is set."
        ),
    )
    parser.add_argument(
        "--all-tickets",
        action="store_true",
        help=f"Run every ticket case ({len(TICKET_CASES)})",
    )
    parser.add_argument(
        "--all-names",
        action="store_true",
        help=f"Sweep every name ({len(NAME_VALUES)}) instead of the {len(PILOT_NAMES)} pilot names",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Use only the first N tickets (overrides --all-tickets)",
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
        "--repeats",
        type=int,
        default=None,
        help=(
            "Independent TypeSafe calls per case/value, to sample Jev non-determinism "
            f"(default {PILOT_REPEATS} for the pilot, {DEFAULT_REPEATS} otherwise)"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "CSV path (default: explainability/bias/gender/results/"
            "gender_perturbation_<timestamp>.csv)"
        ),
    )
    args = parser.parse_args(argv)
    if args.repeats is None:
        args.repeats = PILOT_REPEATS if _is_pilot(args) else DEFAULT_REPEATS
    if args.repeats < 1:
        parser.error("repeats must be >= 1")
    if args.limit is not None and args.limit < 1:
        parser.error("limit must be >= 1")
    if args.output is None:
        args.output = default_output()
    return args


def _is_pilot(args: argparse.Namespace) -> bool:
    return not args.all_tickets and not args.all_names and args.limit is None


def selected_cases(args: argparse.Namespace) -> tuple[Case, ...]:
    if args.limit is not None:
        return TICKET_CASES[: args.limit]
    if args.all_tickets:
        return TICKET_CASES
    return TICKET_CASES[:PILOT_CASE_COUNT]


def selected_names(args: argparse.Namespace) -> tuple[str, ...]:
    if args.all_names:
        return NAME_VALUES
    return PILOT_NAMES


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
    names = selected_names(args)
    async with client:
        frame = await run_cases(
            cases,
            "name",
            names,
            client,
            batch_size=args.batch_size,
            repeats=args.repeats,
        )
    path = write_results_csv(frame, args.output)
    case_ids = ", ".join(case.id for case in cases)
    print(
        f"Wrote {len(frame)} rows ({case_ids}; {len(names)} names; "
        f"repeats={args.repeats}) to {path}"
    )
    return path


def main(argv: list[str] | None = None) -> None:
    asyncio.run(run(parse_args(argv)))


if __name__ == "__main__":
    main()
