"""Claude Code SessionStart hook: print the interviews and tasks from private/upcoming.md.

Prints nothing when the file is missing (fresh clones have no private/ folder).
"""

import re
import sys
from datetime import date, datetime
from pathlib import Path

UPCOMING = Path(__file__).resolve().parents[1] / "private" / "upcoming.md"
MAX_ROWS = 8
URGENT_DAYS = 7
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def flag(when: str, today: date) -> str:
    """'overdue' for a passed date, 'urgent' for today through 7 days ahead, else ''."""
    m = DATE.search(when)
    if not m:
        return ""
    days = (datetime.strptime(m.group(), "%Y-%m-%d").date() - today).days
    if days < 0:
        return "overdue"
    return "urgent" if days <= URGENT_DAYS else ""


def rows(text: str, today: date | None = None) -> list[str]:
    """'When | Company | What' for each table row, skipping headers and separators."""
    today = today or date.today()
    out = []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not line.startswith("|") or len(cells) < 4 or set(cells[0]) <= set("-: "):
            continue
        if cells[0] in ("When (Manaus)", "Due"):
            continue
        what = cells[3] if len(cells[3]) <= 90 else cells[3][:87] + "..."
        when = cells[0]
        state = flag(when, today)
        if state:
            when = f"{when.replace('(overdue)', '').strip()} [{state.upper()}]"
        out.append(f"- {when} | {cells[1]} | {what}")
    return out


def main() -> int:
    if not UPCOMING.exists():
        return 0
    text = UPCOMING.read_text(encoding="utf-8")
    items = rows(text)
    if not items:
        return 0
    updated = next((line for line in text.splitlines() if line.startswith("Updated:")), "")
    print(f"Next deadlines from private/upcoming.md ({updated or 'no update time'}):")
    print("\n".join(items[:MAX_ROWS]))
    if len(items) > MAX_ROWS:
        print(f"... and {len(items) - MAX_ROWS} more in private/upcoming.md")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
