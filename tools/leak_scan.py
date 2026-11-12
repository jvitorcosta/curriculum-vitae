"""Leak scan: report file:line for anything private found in the public tree. Never prints what matched.

Run: uv run python tools/leak_scan.py [--untracked-too]

Checks every tracked file (or, with --untracked-too, every file outside private/, .git, .venv, site/)
for:
- the phone number, in any formatting, and the legal name from private/profile.yaml
- every applied-to company in private/tracker.md, except the employers already public on the resume
- internal-note markers (cv/markers.py) in published content: main/, case-studies/, resume/
Exits 1 on any hit, 0 when clean. A fresh clone without private/ only checks the markers.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cv.markers import CONTENT_DIRS, INTERNAL_MARKERS  # noqa: E402 (needs ROOT on sys.path first)

# Employers and clients already public on the resume, so their names may appear.
PUBLIC_EMPLOYERS = {"nubank", "qubika", "elogroup", "coastal community bank", "comgás", "comgas"}
SKIP_DIRS = {"private", ".git", ".venv", "site", "__pycache__", ".pytest_cache", ".superpowers"}
SKIP_FILES = {"uv.lock"}


def private_terms(root: Path) -> list[str]:
    """Literal strings that must never appear in public files. Empty without private/."""
    terms: list[str] = []
    profile_path = root / "private" / "profile.yaml"
    if profile_path.exists():
        profile = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
        terms += [str(profile[k]) for k in ("phone", "legal_name") if profile.get(k)]
    tracker = root / "private" / "tracker.md"
    stack = _public_stack(root)
    if tracker.exists():
        for line in tracker.read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 6 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[0]):
                company = cells[1]
                if (company and company.lower() not in PUBLIC_EMPLOYERS and company not in terms
                        and not re.search(rf"(?<!\w){re.escape(company.lower())}(?!\w)", stack)):
                    terms.append(company)
    return terms


def _public_stack(root: Path) -> str:
    """Lower-cased text of what is already public by design: the skills list, the tools lines, the
    published resume and the certificates. A company named there (a product I use, a client, a
    certificate issuer) says nothing about where I applied."""
    parts = []
    for rel in ("main/skills.md", "main/certificates.md", "resume/resume.md"):
        if (root / rel).exists():
            parts.append((root / rel).read_text(encoding="utf-8"))
    for path in (root / "main").rglob("*.md") if (root / "main").exists() else []:
        parts += [line for line in path.read_text(encoding="utf-8").splitlines() if "Technologies and tools" in line]
    return "\n".join(parts).lower()


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def scan(root: Path, files: list[Path], terms: list[str], patterns: list[str]) -> list[str]:
    """'relpath:line' for each line holding a private term, or a marker inside published content."""
    phones = [_digits(t) for t in terms if len(_digits(t)) >= 8]
    words = [t.lower() for t in terms if len(_digits(t)) < 8]
    hits = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        is_content = rel.split("/", 1)[0] in CONTENT_DIRS
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary files (PDF, images) are checked by eye in the file list review
        for number, line in enumerate(text.splitlines(), 1):
            lower = line.lower()
            found = any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", lower) for w in words)
            found = found or any(p in _digits(line) for p in phones)
            found = found or (is_content and any(re.search(m, line, re.IGNORECASE) for m in patterns))
            if found:
                hits.append(f"{rel}:{number}")
    return hits


def public_files(root: Path, untracked_too: bool) -> list[Path]:
    if not untracked_too:
        listed = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True).stdout
        return [root / line for line in listed.splitlines() if line]
    return [p for p in root.rglob("*") if p.is_file()
            and not SKIP_DIRS.intersection(p.relative_to(root).parts) and p.name not in SKIP_FILES]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--untracked-too", action="store_true", help="scan the working tree, not only tracked files")
    args = parser.parse_args()
    hits = scan(ROOT, public_files(ROOT, args.untracked_too), private_terms(ROOT), INTERNAL_MARKERS)
    for hit in hits:
        print(hit)
    print(f"{len(hits)} possible leak(s)" if hits else "clean")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
