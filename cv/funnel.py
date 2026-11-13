"""Funnel stats: which channels, score bands and company types produce replies."""

import datetime
import statistics
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
        v = float(score)
    except (TypeError, ValueError):
        return "unscored"
    if v >= 4.5:
        return "4.5+"
    if v >= 4.0:
        return "4.0–4.4"
    if v >= 3.0:
        return "3.0–3.9"
    return "<3.0"


def _yielded(m: AppMeta) -> bool:
    return any(h.get("status") in YIELD for h in m.history)


def _key(m: AppMeta, by: str) -> str:
    if by == "score":
        return score_band(m.score)
    return (getattr(m, by) or "").strip() or "(none)"


def funnel(metas: list[AppMeta], by: By, since: datetime.date | None = None) -> list[Bucket]:
    groups: dict[str, list[AppMeta]] = {}
    for m in metas:
        if m.status in NOT_SENT:
            continue
        if since and m.date < since.isoformat():
            continue
        groups.setdefault(_key(m, by), []).append(m)
    buckets = []
    for key, ms in groups.items():
        sent, yielded = len(ms), sum(_yielded(m) for m in ms)
        buckets.append(Bucket(
            key=key, sent=sent, yielded=yielded,
            rejected=sum(m.status == "rejected" for m in ms),
            ghosted=sum(m.status == "ghosted" for m in ms),
            open=sum(m.status in OPEN for m in ms),
            rate=yielded / sent, sufficient=sent >= MIN_SAMPLE))
    buckets.sort(key=lambda b: (-b.sent, b.key))
    return buckets


def median_days_to_yield(metas: list[AppMeta]) -> float | None:
    days = []
    for m in metas:
        dates = [h["date"] for h in m.history if h.get("status") in YIELD and h.get("date")]
        if not dates:
            continue
        try:
            days.append((datetime.date.fromisoformat(min(dates)) - datetime.date.fromisoformat(m.date)).days)
        except ValueError:
            continue
    return float(statistics.median(days)) if days else None


def render_funnel(buckets: list[Bucket], median: float | None) -> str:
    lines = ["| Key | Sent | Yielded | Rate | Rejected | Ghosted | Open |", "|---|---|---|---|---|---|---|"]
    for b in buckets:
        key = b.key if b.sufficient else f"{b.key} (small sample)"
        lines.append(f"| {key} | {b.sent} | {b.yielded} | {b.rate:.0%} | {b.rejected} | {b.ghosted} | {b.open} |")
    lines += ["", "Median days to first reply: " + (f"{median:g}" if median is not None else "n/a")]
    return "\n".join(lines)
