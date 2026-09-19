"""Download a local Polaris ticket snapshot (gitignored). Re-run to refresh."""

from __future__ import annotations

import argparse
from pathlib import Path

from system_one.cases.ticket_source import TICKETS_PATH, write_snapshot


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Local Polaris CSV (default: download)",
    )
    parser.add_argument("--output", type=Path, default=TICKETS_PATH)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the local snapshot even if it already exists",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.output.exists() and not args.force:
        print(f"Already have {args.output} (pass --force to refresh)")
        return
    path = write_snapshot(args.output, source=args.input)
    print(f"Wrote tickets to {path}")


if __name__ == "__main__":
    main()
