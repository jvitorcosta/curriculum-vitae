"""Leak scan: report file:line for anything private found in the public tree. Never prints what matched.

Run: uv run python tools/leak_scan.py [--untracked-too]

Checks every file git would commit (tracked plus untracked, not ignored), or with --untracked-too
every file outside private/, .git, .venv, site/, for:
- the phone number, in any formatting and with or without the country code, and the legal name
  (accents and spacing ignored) from private/profile.yaml
- every applied-to company (private/applications/*/meta.yaml and private/tracker.md), except the
  employers already public on the resume and the names listed in private/leak-scan-allow.txt
- internal-note markers (cv/markers.py) in published content: main/, case-studies/, resume/
PDF and DOCX files are scanned through their text. Exits 1 on any hit, 0 when clean. A fresh clone
without private/ only checks the markers, and says so.
"""

import argparse
import re
import subprocess
import sys
import unicodedata
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cv.markers import CONTENT_DIRS, INTERNAL_MARKERS  # noqa: E402 (needs ROOT on sys.path first)
from cv.tracker import collect  # noqa: E402

# Employers and clients already public on the resume, so their names may appear.
PUBLIC_EMPLOYERS = {"nubank", "qubika", "elogroup", "coastal community bank", "comgás", "comgas"}
SKIP_DIRS = {"private", ".git", ".venv", "site", "__pycache__", ".pytest_cache", ".superpowers"}
SKIP_FILES = {"uv.lock"}
PHONE_TAIL = 9  # a Brazilian mobile number without area or country code


def private_terms(root: Path) -> list[str]:
    """Literal strings that must never appear in public files. Empty without private/."""
    terms: list[str] = []
    private = root / "private"
    profile_path = private / "profile.yaml"
    if profile_path.exists():
        profile = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
        terms += [str(profile[k]) for k in ("phone", "legal_name") if profile.get(k)]
    allowed = PUBLIC_EMPLOYERS | _allowlist(private)
    companies = [meta.company for _, meta in collect(private)[0]] if private.exists() else []
    tracker = private / "tracker.md"
    if tracker.exists():
        for line in tracker.read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 6 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[0]):
                companies.append(cells[1])
    for company in companies:
        if company and _norm(company) not in allowed and company not in terms:
            terms.append(company)
    return terms


def _allowlist(private: Path) -> set[str]:
    """Names in private/leak-scan-allow.txt that are public anyway (a product I use, a client)."""
    path = private / "leak-scan-allow.txt"
    if not path.exists():
        return set()
    lines = path.read_text(encoding="utf-8").splitlines()
    return {_norm(line) for line in lines if line.strip() and not line.lstrip().startswith("#")}


def _norm(text: str) -> str:
    """Lower case, accents stripped, runs of whitespace collapsed."""
    plain = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", plain).strip().lower()


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def _lines(path: Path) -> list[str] | None:
    """The file's text lines; PDF and DOCX through their extracted text; None for other binaries."""
    try:
        if path.suffix.lower() == ".pdf":
            from pypdf import PdfReader
            return ["\n".join(page.extract_text() or "" for page in PdfReader(path).pages).replace("\n", " ")]
        if path.suffix.lower() == ".docx":
            with zipfile.ZipFile(path) as z:
                xml = " ".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist()
                               if n.startswith(("word/", "docProps/")) and n.endswith(".xml"))
            return [re.sub(r"<[^>]+>", " ", xml)]
        return path.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError, zipfile.BadZipFile, ValueError):
        return None  # images and other binaries are checked by eye in the file list review


def scan(root: Path, files: list[Path], terms: list[str], patterns: list[str]) -> list[str]:
    """'relpath:line' for each line holding a private term, or a marker inside published content.
    PDF and DOCX hits are reported as the bare relpath."""
    phones = [_digits(t)[-PHONE_TAIL:] for t in terms if len(_digits(t)) >= 8]
    words = [_norm(t) for t in terms if len(_digits(t)) < 8]
    hits = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        is_content = rel.split("/", 1)[0] in CONTENT_DIRS
        lines = _lines(path)
        if lines is None:
            continue
        whole_file = path.suffix.lower() in (".pdf", ".docx")
        for number, line in enumerate(lines, 1):
            plain = _norm(line)
            found = any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", plain) for w in words)
            found = found or any(p in _digits(line) for p in phones)
            found = found or (is_content and any(re.search(m, line, re.IGNORECASE) for m in patterns))
            if found:
                hits.append(rel if whole_file else f"{rel}:{number}")
    return hits


def public_files(root: Path, untracked_too: bool) -> list[Path]:
    """What a commit could include: tracked plus untracked files git does not ignore."""
    if not untracked_too:
        listed = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                                cwd=root, capture_output=True, text=True, check=True).stdout
        return [root / line for line in listed.splitlines() if line and (root / line).is_file()]
    return [p for p in root.rglob("*") if p.is_file()
            and not SKIP_DIRS.intersection(p.relative_to(root).parts) and p.name not in SKIP_FILES]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--untracked-too", action="store_true", help="scan the whole working tree, ignored files too")
    args = parser.parse_args()
    terms = private_terms(ROOT)
    hits = scan(ROOT, public_files(ROOT, args.untracked_too), terms, INTERNAL_MARKERS)
    for hit in hits:
        print(hit)
    if hits:
        print(f"{len(hits)} possible leak(s)")
    elif terms:
        print(f"clean ({len(terms)} private terms checked)")
    else:
        print("clean for markers, but no private terms were loaded (no private/ here), so names and phone were not checked")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
