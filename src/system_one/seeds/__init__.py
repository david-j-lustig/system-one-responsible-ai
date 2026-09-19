"""Seeds grouped by category."""

from system_one.seeds.seed import Frame, Seed
from system_one.seeds.self_harm import SEEDS as SELF_HARM
from system_one.seeds.violence import SEEDS as VIOLENCE

SEED_SETS = {
    "self_harm": SELF_HARM,
    "violence": VIOLENCE,
}

SEEDS = tuple(seed for seeds in SEED_SETS.values() for seed in seeds)

__all__ = [
    "SEED_SETS",
    "SEEDS",
    "Frame",
    "Seed",
]
