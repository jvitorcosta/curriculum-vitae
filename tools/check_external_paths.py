"""Check that Claude skills and scheduled tasks only point at curriculum-vitae paths that exist.

Run: uv run python tools/check_external_paths.py

Reads ~/.claude/skills/*/SKILL.md and ~/.claude/scheduled-tasks/*/SKILL.md, pulls out every
curriculum-vitae\\... or curriculum-vitae/... path, and lists the ones missing from this repo.
A placeholder segment (<folder>, *, {date}) ends the path, so only the concrete part is checked.
Exits 1 on any missing path, 0 otherwise.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = re.compile(r"curriculum-vitae[\\/]([^\s`'\"()\[\]|]+)")
PLACEHOLDER = re.compile(r"[<>*{}]")


def repo_paths(text: str) -> list[str]:
    """Repo-relative paths named in the text, cut before the first placeholder segment."""
    found = []
    for match in PATH.finditer(text):
        parts = []
        for part in match.group(1).replace("\\", "/").split("/"):
            if not part or PLACEHOLDER.search(part):
                break
            parts.append(part)
        path = "/".join(parts).rstrip(".,:;")
        if path and path not in found:
            found.append(path)
    return found


def missing(root: Path, files: list[Path]) -> list[str]:
    """'<file>: <path>' for each named path that does not exist under root."""
    return [f"{f}: {p}" for f in files for p in repo_paths(f.read_text(encoding="utf-8"))
            if not (root / p).exists()]


def main() -> int:
    claude = Path.home() / ".claude"
    files = sorted([*claude.glob("skills/*/SKILL.md"), *claude.glob("scheduled-tasks/*/SKILL.md")])
    problems = missing(ROOT, files)
    for problem in problems:
        print(problem)
    print(f"{len(problems)} missing path(s) in {len(files)} files" if problems else f"ok ({len(files)} files)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
