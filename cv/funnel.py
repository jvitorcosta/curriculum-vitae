"""Funnel stats: which channels, score bands and company types produce replies."""

import datetime
import math
import statistics
from collections import Counter
from dataclasses import dataclass
from typing import Literal

from cv.meta import AppMeta

By = Literal["channel", "score", "company_type", "archetype", "contract"]
BY = ("channel", "score", "company_type", "archetype", "contract")
NOT_SENT = ("draft", "withdrawn")
YIELD = ("screening", "interview", "offer")
OPEN = ("applied", "screening", "interview")
MIN_SAMPLE = 20


@dataclass(frozen=True)
class Bucket:
    key: str
    sent: int
    yielded: int
    rejected: int
    ghosted: int
    open: int
    rate: float
    sufficient: bool


def score_band(score: str) -> str:
    try:
        v = float(str(score).strip().replace(",", "."))
    except (TypeError, ValueError):
        return "unscored"
    if not math.isfinite(v) or not 0 <= v <= 5:
        return "unscored"
    if v >= 4.5:
        return "4.5+"
    if v >= 4.0:
        return "4.0–4.4"
    if v >= 3.0:
        return "3.0–3.9"
    return "<3.0"


def _yielded(m: AppMeta) -> bool:
    return m.status in YIELD or any(h.get("status") in YIELD for h in m.history)


def _key(m: AppMeta, by: str) -> str:
    if by == "score":
        return score_band(m.score)
    return (getattr(m, by) or "").strip() or "(none)"


def _sent(metas: list[AppMeta], since: datetime.date | None) -> list[AppMeta]:
    """Applications that were actually sent (not draft/withdrawn), on or after `since`."""
    return [m for m in metas if m.status not in NOT_SENT and not (since and m.date < since.isoformat())]


def funnel(metas: list[AppMeta], by: By, since: datetime.date | None = None) -> list[Bucket]:
    groups: dict[str, list[AppMeta]] = {}
    spellings: dict[str, Counter[str]] = {}
    for m in _sent(metas, since):
        key = _key(m, by)
        folded = " ".join(key.casefold().split())
        groups.setdefault(folded, []).append(m)
        spellings.setdefault(folded, Counter())[key] += 1
    buckets = []
    for folded, ms in groups.items():
        # most common original spelling; ties go to the alphabetically first
        key = min(spellings[folded].items(), key=lambda kv: (-kv[1], kv[0]))[0]
        sent, yielded = len(ms), sum(_yielded(m) for m in ms)
        buckets.append(Bucket(
            key=key, sent=sent, yielded=yielded,
            rejected=sum(m.status == "rejected" for m in ms),
            ghosted=sum(m.status == "ghosted" for m in ms),
            open=sum(m.status in OPEN for m in ms),
            rate=yielded / sent, sufficient=sent >= MIN_SAMPLE))
    buckets.sort(key=lambda b: (-b.sent, b.key))
    return buckets


def median_days_to_yield(metas: list[AppMeta], since: datetime.date | None = None) -> float | None:
    """Median days from application to the first screening/interview/offer, over the same set as the table."""
    days = []
    for m in _sent(metas, since):
        dates = [h["date"] for h in m.history if h.get("status") in YIELD and h.get("date")]
        if not dates:
            continue
        try:
            delta = (datetime.date.fromisoformat(min(dates)) - datetime.date.fromisoformat(m.date)).days
        except ValueError:
            continue
        if delta >= 0:
            days.append(delta)
    return float(statistics.median(days)) if days else None


def render_funnel(buckets: list[Bucket], median: float | None) -> str:
    lines = ["| Key | Sent | Yielded | Rate | Rejected | Ghosted | Open |", "|---|---|---|---|---|---|---|"]
    for b in buckets:
        key = b.key if b.sufficient else f"{b.key} (small sample)"
        lines.append(f"| {key} | {b.sent} | {b.yielded} | {b.rate:.0%} | {b.rejected} | {b.ghosted} | {b.open} |")
    lines += ["", "Median days to first screening/interview: " + (f"{median:g}" if median is not None else "n/a")]
    return "\n".join(lines)
