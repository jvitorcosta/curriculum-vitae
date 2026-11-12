"""Build tracker.md from every applications/*/meta.yaml."""

from collections import Counter
from pathlib import Path

from cv.meta import STATUSES, AppMeta, MetaError, load_meta

Row = tuple[Path, AppMeta]


def collect(root: Path) -> tuple[list[Row], list[MetaError]]:
    rows: list[Row] = []
    errors: list[MetaError] = []
    for folder in sorted(p for p in (root / "applications").glob("*") if p.is_dir()):
        meta_path = folder / "meta.yaml"
        if not meta_path.exists():
            errors.append(MetaError(meta_path, "missing meta.yaml"))
            continue
        try:
            rows.append((folder, load_meta(meta_path)))
        except MetaError as e:
            errors.append(e)
    rows.sort(key=lambda r: r[1].company.lower())
    rows.sort(key=lambda r: r[1].date, reverse=True)
    return rows, errors


def render_tracker(rows: list[Row], errors: list[MetaError]) -> str:
    counts = Counter(m.status for _, m in rows)
    summary = " · ".join(f"{s}: {counts[s]}" for s in STATUSES if counts[s])
    lines = ["# Applications", "", f"{len(rows)} applications — {summary}", "",
             "| Date | Company | Role | Channel | Status | Folder |",
             "|---|---|---|---|---|---|"]
    for folder, m in rows:
        cells = [m.date, m.company, m.role, m.channel, m.status, f"[{folder.name}](applications/{folder.name}/)"]
        lines.append("| " + " | ".join(" ".join(c.split()).replace("|", r"\|") for c in cells) + " |")
    if errors:
        lines += ["", "## Needs fixing", ""]
        lines += [f"- `{e.path.parent.name}`: {e.reason}" for e in errors]
    return "\n".join(lines) + "\n"
