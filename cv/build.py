"""Export resume.md / cover-letter.md to PDF (pandoc -> Typst) and DOCX (pandoc)."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

import yaml
from pypdf import PdfReader

from cv.meta import load_meta
from cv.slug import filename_part

Kind = Literal["resume", "cover-letter"]

PT_HEADINGS = {
    "SUMMARY": "RESUMO", "SKILLS": "HABILIDADES", "EXPERIENCE": "EXPERIÊNCIA", "PROJECTS": "PROJETOS",
    "EDUCATION": "FORMAÇÃO", "CERTIFICATES": "CERTIFICADOS", "LANGUAGES": "IDIOMAS",
}
LANGS = ("en", "pt")
STEMS = {"resume": "Resume", "cover-letter": "Cover_Letter"}


class ToolMissing(Exception):
    def __init__(self, tool: str):
        super().__init__(f"{tool} not found on PATH. Install it with: winget install --id "
                         + {"pandoc": "JohnMacFarlane.Pandoc", "typst": "Typst.Typst"}[tool] + " -e")
        self.tool = tool


def split_front_matter(text: str) -> tuple[dict, str]:
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n?", text, re.S)
    if not match:
        return {}, text
    return yaml.safe_load(match.group(1)) or {}, text[match.end():]


def compose_document(profile: dict, body_md: str, kind: Kind) -> str:
    front, body = split_front_matter(body_md)
    if front.get("lang", "en") not in LANGS:
        raise ValueError(f"lang must be one of {', '.join(LANGS)}, got {front.get('lang')!r}")
    if front.get("lang") == "pt":
        body = re.sub(r"^## (\w+)\s*$", lambda m: f"## {PT_HEADINGS.get(m.group(1), m.group(1))}", body, flags=re.M)
    links = profile.get("links") or {}
    contact = [profile.get("location"), profile.get("phone"), profile.get("email"), links.get("linkedin"), links.get("github")]
    lines = [f"# {profile['name']}", ""]
    if kind == "resume" and front.get("headline"):
        lines += [f"**{front['headline']}**", ""]
    lines += [" | ".join(c for c in contact if c), "", body.strip(), ""]
    return "\n".join(lines)


def check_tools() -> dict[str, str]:
    found = {}
    for tool in ("pandoc", "typst"):
        path = shutil.which(tool)
        if not path:
            raise ToolMissing(tool)
        found[tool] = path
    return found


def _run(args: list[str]) -> None:
    subprocess.run(args, check=True, capture_output=True, text=True, encoding="utf-8")


def build_outputs(app_dir: Path, profile: dict, templates: Path) -> list[Path]:
    tools = check_tools()
    meta = load_meta(app_dir / "meta.yaml")
    out_dir = app_dir / "out"
    out_dir.mkdir(exist_ok=True)
    outputs: list[Path] = []
    for kind in ("resume", "cover-letter"):
        source = app_dir / f"{kind}.md"
        if not source.exists() or not split_front_matter(source.read_text(encoding="utf-8"))[1].strip():
            continue
        text = source.read_text(encoding="utf-8")
        lang = split_front_matter(text)[0].get("lang", "en")
        stem = f"{filename_part(profile['name'])}_{STEMS[kind]}_{filename_part(meta.company)}"
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "doc.md"
            md.write_text(compose_document(profile, text, kind), encoding="utf-8")
            typ = Path(tmp) / "doc.typ"
            _run([tools["pandoc"], str(md), "-f", "markdown", "-t", "typst", "--template", str(templates / "resume.typ"),
                  "-V", f"lang={lang}", "-M", f"pagetitle={stem.replace('_', ' ')}", "-o", str(typ)])
            pdf = out_dir / f"{stem}.pdf"
            _run([tools["typst"], "compile", str(typ), str(pdf)])
            docx = out_dir / f"{stem}.docx"
            _run([tools["pandoc"], str(md), "-f", "markdown", "--reference-doc", str(templates / "reference.docx"), "-o", str(docx)])
        outputs += [pdf, docx]
    return outputs


def pdf_text(path: Path) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


def resume_headings(resume_md: str) -> list[str]:
    """The `## ` section headings of a resume source, as they appear in its PDF (translated for lang: pt)."""
    front, body = split_front_matter(resume_md)
    names = re.findall(r"^## (.+?)\s*$", body, flags=re.M)
    if front.get("lang") == "pt":
        names = [PT_HEADINGS.get(n, n) for n in names]
    return names


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def ats_report(text: str, profile: dict, headings: list[str] | None = None) -> list[str]:
    """Problems an applicant tracking system would hit in the PDF's extracted text. Empty list means clean."""
    problems = []
    if profile["name"] not in text:
        problems.append("name not found as text")
    if profile["email"] not in text:
        problems.append("email not found as text")
    phone = profile.get("phone") or ""
    if _digits(phone) and _digits(phone) not in _digits(text):
        problems.append("phone not found as text")
    if "(cid:" in text or "�" in text:
        problems.append("broken glyphs in text ((cid:) or U+FFFD): a font did not map to text")
    lines = [line.strip() for line in text.splitlines()]
    pos = -1
    for h in headings or []:
        try:
            at = lines.index(h, pos + 1)
        except ValueError:
            problems.append(f"heading {h} missing" if h not in lines else f"heading {h} out of order")
            continue
        pos = at
    return problems


_STOPWORDS = set("""a about above after all also an and any are as at be been being but by can could do does each for from had
has have how if in into is it its may more most must no not of on or our out over should so such than that the their them
then there these they this those to up us use used using was we were what when where which while who will with within would
you your years year experience work working team role strong ability skills including etc plus job company candidate""".split())


def keyword_report(posting: str, resume_text: str, limit: int = 25) -> tuple[list[str], list[str]]:
    """Terms the posting repeats, split into those present in the resume text and those absent. Report only."""
    words = re.findall(r"[a-z][a-z0-9+#.]*[a-z0-9+#]|[a-z]", posting.lower())
    counts: dict[str, int] = {}
    for w in words:
        if len(w) >= 3 and w not in _STOPWORDS:
            counts[w] = counts.get(w, 0) + 1
    ranked = sorted((w for w, n in counts.items() if n >= 2), key=lambda w: (-counts[w], w))[:limit]
    low = resume_text.lower()
    found = [w for w in ranked if w in low]
    return found, [w for w in ranked if w not in low]
