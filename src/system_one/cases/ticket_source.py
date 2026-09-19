"""Download a local Polaris ticket snapshot. Not shipped in git (CC BY-SA)."""

from __future__ import annotations

import hashlib
import io
import json
import re
import ssl
import subprocess
import urllib.request
from pathlib import Path
from urllib.error import URLError

import pandas as pd

DATASET_CSV = (
    "https://huggingface.co/datasets/VladislavMarinovich/polaris-support-tickets-v2"
    "/resolve/main/polaris_tickets_v2.csv"
)
TICKETS_PATH = Path(__file__).resolve().parent / "data" / "tickets.json"
SEED = 20260919
SAMPLE_SIZE = 200
PER_ROUTING = 40
ROUTING_ORDER = (
    "kb_autoresolve",
    "engineering",
    "sales_success",
    "retention",
    "security_incident",
)
FILL_ORDER = (
    "engineering",
    "sales_success",
    "retention",
    "security_incident",
    "kb_autoresolve",
)

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]\d{4}\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_SIGNOFF = re.compile(
    r"(?:\s*(?:thanks|thank you|cheers|regards|best|sincerely)\b[^\n]*)+$",
    re.IGNORECASE,
)


def _has_pii(text: str) -> bool:
    return bool(_EMAIL.search(text) or _PHONE.search(text) or _SSN.search(text))


def strip_signoff(body: str) -> str:
    return _SIGNOFF.sub("", body).rstrip()


def _body_key(body: str) -> str:
    normalized = re.sub(r"\s+", " ", body).strip().lower()
    return hashlib.sha256(normalized[:80].encode()).hexdigest()


def _download_csv() -> bytes:
    try:
        with urllib.request.urlopen(DATASET_CSV) as response:
            return response.read()
    except (ssl.SSLError, URLError):
        return subprocess.check_output(["curl", "-fsSL", DATASET_CSV])


def load_source(path: Path | None = None) -> pd.DataFrame:
    if path is not None:
        return pd.read_csv(path)
    return pd.read_csv(io.BytesIO(_download_csv()))


def clean(frame: pd.DataFrame) -> pd.DataFrame:
    rows = frame.copy()
    rows["subject"] = rows["subject"].fillna("").astype(str)
    rows["body"] = rows["body"].fillna("").astype(str).map(strip_signoff)
    rows = rows.loc[rows["body"].str.len() > 0]
    text = rows["subject"] + "\n" + rows["body"]
    rows = rows.loc[~text.map(_has_pii)]
    rows["body_key"] = rows["body"].map(_body_key)
    return rows.drop_duplicates("body_key")


def sample_tickets(frame: pd.DataFrame, *, seed: int = SEED) -> pd.DataFrame:
    rng = seed
    picked: list[pd.DataFrame] = []
    leftover_parts: list[pd.DataFrame] = []
    for routing in ROUTING_ORDER:
        pool = frame.loc[frame["routing"].eq(routing)]
        take_n = min(PER_ROUTING, len(pool))
        if take_n:
            take = pool.sample(n=take_n, random_state=rng)
            picked.append(take)
            leftover_parts.append(pool.drop(take.index))
        rng += 1
    selected = pd.concat(picked) if picked else pd.DataFrame(columns=frame.columns)
    need = SAMPLE_SIZE - len(selected)
    if need > 0 and leftover_parts:
        leftover = pd.concat(leftover_parts)
        fill_chunks: list[pd.DataFrame] = []
        remaining = need
        fill_seed = seed + 100
        for routing in FILL_ORDER:
            if remaining <= 0:
                break
            pool = leftover.loc[leftover["routing"].eq(routing)]
            take_n = min(remaining, len(pool))
            if not take_n:
                continue
            fill_chunks.append(pool.sample(n=take_n, random_state=fill_seed))
            remaining -= take_n
            fill_seed += 1
        if fill_chunks:
            selected = pd.concat([selected, *fill_chunks])
    if len(selected) < SAMPLE_SIZE:
        raise ValueError(f"only {len(selected)} unique tickets after filters; need {SAMPLE_SIZE}")
    return selected.head(SAMPLE_SIZE).sort_values("ticket_id")


def records(frame: pd.DataFrame) -> list[dict[str, str]]:
    return [
        {
            "id": str(row.ticket_id),
            "subject": str(row.subject),
            "body": str(row.body),
            "routing": str(row.routing),
            "type": str(row.type),
            "priority": str(row.priority),
        }
        for row in frame.itertuples(index=False)
    ]


def write_snapshot(path: Path = TICKETS_PATH, *, source: Path | None = None) -> Path:
    tickets = records(sample_tickets(clean(load_source(source))))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tickets, indent=2, ensure_ascii=False) + "\n")
    return path


def ensure_tickets(path: Path = TICKETS_PATH) -> Path:
    """Return the local snapshot, downloading Polaris once if it is missing."""
    if path.exists():
        return path
    print(f"Downloading Polaris support tickets (once) to {path}")
    return write_snapshot(path)
