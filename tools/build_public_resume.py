"""Build the public resume (resume/resume.md) to PDF and DOCX.

Run: uv run python tools/build_public_resume.py [--copy-to <local clone of jvitorcosta/jvitorcosta.github.io>]

The website serves a copy of the PDF; --copy-to copies it into the site clone, then commit and
push there. The header comes from the public profile, never the phone number or legal name.
"""

import argparse
import shutil
import tempfile
from pathlib import Path

from pypdf import PdfReader

from cv.build import _run, check_tools, compose_document, pdf_text
from cv.profile import public_profile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "resume" / "resume.md"
STEM = "Vitor_Pinheiro_Resume"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--copy-to", type=Path, help="folder to copy the built PDF into (the site repo clone)")
    args = parser.parse_args()
    tools = check_tools()
    profile = public_profile(ROOT)
    out = SOURCE.parent
    with tempfile.TemporaryDirectory() as tmp:
        md = Path(tmp) / "doc.md"
        md.write_text(compose_document(profile, SOURCE.read_text(encoding="utf-8"), "resume"), encoding="utf-8")
        typ = Path(tmp) / "doc.typ"
        _run([tools["pandoc"], str(md), "-f", "markdown", "-t", "typst", "--template", str(ROOT / "templates" / "resume.typ"),
              "-V", "lang=en", "-M", "pagetitle=Vitor Pinheiro Resume", "-o", str(typ)])
        _run([tools["typst"], "compile", str(typ), str(out / f"{STEM}.pdf")])
        _run([tools["pandoc"], str(md), "-f", "markdown", "--reference-doc", str(ROOT / "templates" / "reference.docx"),
              "-o", str(out / f"{STEM}.docx")])
    pdf = out / f"{STEM}.pdf"
    pages = len(PdfReader(pdf).pages)
    assert "phone" not in profile and profile["name"] in pdf_text(pdf)
    print(f"Built {pdf.name} ({pages} page{'s' if pages != 1 else ''}) and {STEM}.docx")
    if pages > 2:
        raise SystemExit("Resume is longer than 2 pages: cut older or weaker bullets.")
    if args.copy_to:
        shutil.copy2(pdf, args.copy_to / pdf.name)
        print(f"Copied to {args.copy_to / pdf.name}: commit and push it there.")


if __name__ == "__main__":
    main()
