"""Load experiment settings from `.env` and the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    typesafe_api_key: str | None = None


def load_settings(*, env_file: Path | None = None) -> Settings:
    path = REPO_ROOT / ".env" if env_file is None else env_file
    if path.exists():
        load_dotenv(path)
    key = os.environ.get("TYPESAFE_API_KEY") or None
    return Settings(typesafe_api_key=key)
