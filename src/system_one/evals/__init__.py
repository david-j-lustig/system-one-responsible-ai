"""Fixed eval cases grouped by category.

Register a new set here. CLI flags come from the keys (`self_harm` -> `--self-harm`).
"""

from collections.abc import Mapping

from system_one.evals.case import EvalCase
from system_one.evals.self_harm import CASES as SELF_HARM

_RESERVED_FLAGS = frozenset({"all", "dry_run", "batch_size", "output"})


def _case_sets(
    sets: Mapping[str, tuple[EvalCase, ...]],
) -> dict[str, tuple[EvalCase, ...]]:
    seen: set[str] = set()
    registered: dict[str, tuple[EvalCase, ...]] = {}
    for name, cases in sets.items():
        if not name.isidentifier():
            raise ValueError(f"eval set name must be an identifier, got {name!r}")
        if name in _RESERVED_FLAGS:
            raise ValueError(f"eval set name {name!r} collides with a CLI flag")
        if not cases:
            raise ValueError(f"{name}: eval set is empty")
        for case in cases:
            if case.category != name:
                raise ValueError(
                    f"{case.id}: category {case.category!r} does not match set {name!r}"
                )
            if case.id in seen:
                raise ValueError(f"duplicate eval id: {case.id}")
            seen.add(case.id)
        registered[name] = cases
    return registered


CASE_SETS = _case_sets(
    {
        "self_harm": SELF_HARM,
    }
)

CASES = tuple(case for cases in CASE_SETS.values() for case in cases)

__all__ = [
    "CASES",
    "CASE_SETS",
    "EvalCase",
]
