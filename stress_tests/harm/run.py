"""Walk harm-seed ladders until Noul is close to an unsafe yes or no."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from pathlib import Path

from system_one.attacker import (
    DEFAULT_ATTACKER_MODEL,
    DEFAULT_EXTRA_STEPS,
    FakeScenarioAttacker,
    OpenAIScenarioAttacker,
    ScenarioAttacker,
)
from system_one.client import FakeTypeSafeClient, SystemOneClient, TypesafeClient
from system_one.config import REPO_ROOT, Settings, load_settings
from system_one.perturbation import DEFAULT_BATCH_SIZE
from system_one.search import (
    DEFAULT_PARENTS,
    DEFAULT_ROUNDS,
    DEFAULT_TOLERANCE,
    MODE_MUTATE,
    MODE_SWEEP,
    MODE_WALK,
    SearchMode,
    load_scenarios_json,
    run_stress,
    worst_records,
    write_results_csv,
    write_scenarios_json,
)
from system_one.seeds import SEED_SETS, SEEDS, Seed

RESULTS_DIR = REPO_ROOT / "stress_tests" / "harm" / "results"
FLAG_BY_SET = {
    "self_harm": "self-harm",
    "violence": "violence",
}


def default_output(*, when: datetime | None = None) -> Path:
    stamp = (when or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return RESULTS_DIR / f"harm_stress_{stamp}.csv"


def _seed_ids(seeds: tuple[Seed, ...]) -> str:
    return ", ".join(seed.id for seed in seeds)


def _help_epilog() -> str:
    lines = [
        "Seed sets (choose at least one; --all runs every set):",
        *[
            f"  --{FLAG_BY_SET[name]:<12} {_seed_ids(seeds)}"
            for name, seeds in SEED_SETS.items()
        ],
        f"  {'--all':<12} {_seed_ids(SEEDS)}",
        "",
        "Default mode walks each ladder and stops when |noul - unsafe_target| <= tolerance.",
        "Pass --sweep to score every frame. Unsafe target is 0 (no) or 1 (yes).",
        "--mutate walks the ladder, then asks an LLM for JSON sets of new scenarios.",
        "--from-json continues from the worst-case rows in a prior attacker JSON.",
        "Each mutate round iterates the closest noul scores (--parents); "
        "the JSON keeps only those.",
    ]
    return "\n".join(lines)


def _add_seed_flags(parser: argparse.ArgumentParser) -> None:
    for name, seeds in SEED_SETS.items():
        parser.add_argument(
            f"--{FLAG_BY_SET[name]}",
            action="store_true",
            help=f"Run {name.replace('_', '-')} seeds ({_seed_ids(seeds)})",
        )
    parser.add_argument(
        "--all",
        action="store_true",
        help=f"Run every seed set ({_seed_ids(SEEDS)})",
    )


def _add_run_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Evaluate every frame instead of stopping at tolerance",
    )
    parser.add_argument(
        "--mutate",
        action="store_true",
        help="After the seed ladder, generate JSON sets of scenarios with an LLM attacker",
    )
    parser.add_argument(
        "--from-json",
        type=Path,
        default=None,
        help="Continue from the worst-case rows in a prior harm_stress_*.json (implies --mutate)",
    )
    parser.add_argument(
        "--max-extra",
        type=int,
        default=DEFAULT_EXTRA_STEPS,
        help=f"Scenarios per attacker JSON set (default {DEFAULT_EXTRA_STEPS})",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=DEFAULT_ROUNDS,
        help=f"Attacker rounds after the ladder or prior JSON (default {DEFAULT_ROUNDS})",
    )
    parser.add_argument(
        "--parents",
        type=int,
        default=DEFAULT_PARENTS,
        help=(
            "Closest-noul scenarios to iterate each round, and to keep per seed "
            f"in the attacker JSON (default {DEFAULT_PARENTS})"
        ),
    )
    parser.add_argument(
        "--attacker-model",
        default=None,
        help=f"OpenAI model for --mutate (default {DEFAULT_ATTACKER_MODEL})",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE,
        help=(
            "Stop a walk when |noul - unsafe_target| is at most this "
            f"(default {DEFAULT_TOLERANCE})"
        ),
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
        help=f"Parallel TypeSafe requests per sweep batch (default {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "CSV path (default: "
            "stress_tests/harm/results/harm_stress_<timestamp>.csv)"
        ),
    )


def _validate_args(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> argparse.Namespace:
    if args.output is None:
        args.output = default_output()
    if not args.all and not any(getattr(args, name) for name in SEED_SETS):
        flags = ", ".join(f"--{flag}" for flag in FLAG_BY_SET.values())
        parser.error(f"choose a seed set: {flags}, or --all")
    if args.from_json is not None:
        args.mutate = True
        if not args.from_json.exists():
            parser.error(f"from-json not found: {args.from_json}")
    if args.sweep and args.mutate:
        parser.error("--sweep and --mutate cannot be combined")
    return args


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=_help_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_seed_flags(parser)
    _add_run_flags(parser)
    return _validate_args(parser, parser.parse_args(argv))


def selected_seeds(args: argparse.Namespace) -> tuple[Seed, ...]:
    if args.all:
        return SEEDS
    chosen: list[Seed] = []
    for name, seeds in SEED_SETS.items():
        if getattr(args, name):
            chosen.extend(seeds)
    return tuple(chosen)


def _mode(args: argparse.Namespace) -> SearchMode:
    if args.mutate:
        return MODE_MUTATE
    if args.sweep:
        return MODE_SWEEP
    return MODE_WALK


def _client(args: argparse.Namespace, settings: Settings) -> SystemOneClient:
    if args.dry_run:
        return FakeTypeSafeClient()
    if not settings.typesafe_api_key:
        raise SystemExit(
            "Set TYPESAFE_API_KEY in .env (see .env.example). "
            "Use --dry-run to skip the API."
        )
    return TypesafeClient(api_key=settings.typesafe_api_key)


def _attacker(args: argparse.Namespace, settings: Settings) -> ScenarioAttacker:
    if args.dry_run:
        return FakeScenarioAttacker()
    if not settings.openai_api_key:
        raise SystemExit(
            "Set OPENAI_API_KEY in .env for --mutate. "
            "Use --dry-run to skip the attacker API."
        )
    return OpenAIScenarioAttacker(
        api_key=settings.openai_api_key,
        model=args.attacker_model or settings.attacker_model,
    )


def _prior_records(args: argparse.Namespace) -> list[dict[str, object]] | None:
    if args.from_json is None:
        return None
    return worst_records(load_scenarios_json(args.from_json), k=args.parents)


def _summarize(frame) -> str:
    lines: list[str] = []
    for seed_id, group in frame.groupby("seed_id", sort=False):
        ok = group[group["error"].isna()]
        if ok.empty:
            lines.append(f"{seed_id}: all frames errored")
            continue
        best = ok.loc[ok["distance"].idxmin()]
        hit = "hit" if bool(best["hit"]) else "no hit"
        unsafe = "unsafe" if bool(best["unsafe"]) else "safe"
        lines.append(
            f"{seed_id}: {len(ok)} frames, closest noul={best['noul']:.2f} "
            f"(target {best['target']}, {best['side']}, {unsafe}, {hit}) "
            f"at {best['frame_id']}"
        )
    return "\n".join(lines)


def _write_outputs(
    frame,
    args: argparse.Namespace,
    seeds: tuple[Seed, ...],
    mode: SearchMode,
) -> Path:
    path = write_results_csv(frame, args.output)
    print(f"Wrote {len(frame)} rows ({_seed_ids(seeds)}, {mode}) to {path}")
    if args.mutate and not frame.empty:
        json_path = args.output.with_suffix(".json")
        write_scenarios_json(frame, json_path, keep=args.parents)
        print(f"Wrote worst-case scenarios ({args.parents} per seed) to {json_path}")
    summary = _summarize(frame)
    if summary:
        print(summary)
    return path


async def run(args: argparse.Namespace) -> Path:
    settings = load_settings()
    client = _client(args, settings)
    seeds = selected_seeds(args)
    mode = _mode(args)
    attacker = _attacker(args, settings) if args.mutate else None
    extra_steps = args.max_extra if args.mutate else 0
    async with client:
        frame = await run_stress(
            seeds,
            client,
            mode=mode,
            tolerance=args.tolerance,
            batch_size=args.batch_size,
            attacker=attacker,
            extra_steps=extra_steps,
            rounds=args.rounds,
            parent_count=args.parents,
            prior=_prior_records(args) if args.mutate else None,
        )
    return _write_outputs(frame, args, seeds, mode)


def main(argv: list[str] | None = None) -> None:
    asyncio.run(run(parse_args(argv)))


if __name__ == "__main__":
    main()
