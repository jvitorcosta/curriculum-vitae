"""Check whether a company was applied to recently (re-apply windows)."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from cv.slug import slugify
from cv.tracker import Row

SUFFIXES = {"brasil", "brazil", "digital", "solutions", "group"}
MIN_KEY = 3
OLDER = "older application"


@dataclass(frozen=True)
class Match:
    folder: Path
    company: str
    role: str
    date: str
    status: str
    last_status_date: str
    reason: str


def _tokens(company: str) -> list[str]:
    tokens = slugify(company).split("-")
    while len(tokens) > 1 and tokens[-1] in SUFFIXES:
        tokens.pop()
    return tokens


def _same_company(a: str, b: str) -> bool:
    ta, tb = _tokens(a), _tokens(b)
    return any(len(t) >= MIN_KEY and t in other for t, other in ((ta[0], tb), (tb[0], ta)))


def _day(text: str) -> date | None:
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def find_matches(rows: list[Row], company: str, today: date, apply_days: int = 180, reject_days: int = 90) -> list[Match]:
    matches: list[Match] = []
    for folder, meta in rows:
        if meta.status == "draft" or not _same_company(company, meta.company):
            continue
        dates = [d for d in (h.get("date", "") for h in meta.history) if _day(d)]
        last = max(dates) if dates else meta.date
        applied, last_day = _day(meta.date), _day(last)
        if meta.status == "rejected" and last_day and (today - last_day).days <= reject_days:
            reason = f"rejected within {reject_days} days"
        elif meta.status != "rejected" and applied and (today - applied).days <= apply_days:
            reason = f"applied within {apply_days} days"
        else:
            reason = OLDER
        matches.append(Match(folder, meta.company, meta.role, meta.date, meta.status, last, reason))
    return matches


def blocks(matches: list[Match], role: str) -> bool:
    """Role similarity is the caller's judgment; any recent match blocks."""
    return any(m.reason != OLDER for m in matches)
