"""Claims that must never appear on a resume or cover letter, because main/ does not back them.

Used by the Claude Code PostToolUse hook (tools/claims_check.py). The banned phrases live in
private/claims-banned.toml; a fresh clone falls back to claims-banned.example.toml. Lines that
negate the term ("no blockchain", "planned …") pass; only positive claims are flagged.
"""

import re
import tomllib
from fnmatch import fnmatch
from pathlib import Path

NEGATION = re.compile(r"\b(no|not|never|without|haven't|hasn't|didn't|don't|planned)\b", re.IGNORECASE)

CHECKED = [
    "resume/*.md",
    "private/applications/*/resume.md",
    "private/applications/*/cover-letter.md",
]


def load_banned(root: Path) -> list[tuple[str, str]]:
    """(pattern, why) pairs from private/claims-banned.toml, else the public example list."""
    path = root / "private" / "claims-banned.toml"
    if not path.exists():
        path = root / "claims-banned.example.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"{path} is not valid TOML: {error}") from error
    return [(entry["pattern"], entry["why"]) for entry in data.get("banned", [])]


def is_checked(rel_path: str) -> bool:
    """True for resume and cover-letter files; answer banks may discuss gaps, so they are skipped."""
    rel = rel_path.replace("\\", "/")
    return any(fnmatch(rel, pattern) for pattern in CHECKED)


def find_claims(text: str, banned: list[tuple[str, str]]) -> list[str]:
    """One message per line that makes an unbacked claim."""
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        if NEGATION.search(line):
            continue
        for pattern, why in banned:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                found.append(f'line {number}: "{match.group(0)}": {why}')
    return found
