import shutil
from pathlib import Path

import pytest

from cv.build import build_outputs, compose_document, pdf_text
from cv.scaffold import new_application

needs_tools = pytest.mark.skipif(not shutil.which("pandoc") or not shutil.which("typst"),
                                 reason="pandoc/typst not installed")
TEMPLATES = Path(__file__).parents[1] / "templates"
PROFILE = {"name": "Vitor Pinheiro", "email": "vitor@example.com", "phone": "+00 00 00000-0000",
           "location": "Manaus, AM, Brazil",
           "links": {"linkedin": "linkedin.com/in/jvpro", "github": "github.com/jvitorcosta"}}


def test_compose_resume_header():
    doc = compose_document(PROFILE, "---\nheadline: AI/ML Software Engineer\nlang: en\n---\n## SKILLS\n- Python\n", "resume")
    assert doc.startswith("# Vitor Pinheiro\n")
    assert "AI/ML Software Engineer" in doc and "vitor@example.com" in doc
    assert "headline:" not in doc


def test_compose_portuguese_headings():
    doc = compose_document(PROFILE, "---\nheadline: Engenheiro de IA\nlang: pt\n---\n## EXPERIENCE\n", "resume")
    assert "## EXPERIÊNCIA" in doc


@needs_tools
def test_build_skips_empty_cover_letter(tmp_path):
    d = new_application(tmp_path, "Acme Labs", "Senior AI/ML Engineer", "2026-10-19")
    (d / "resume.md").write_text("---\nheadline: AI/ML Engineer\nlang: en\n---\n## EXPERIENCE\n- Built things\n", encoding="utf-8")
    outs = build_outputs(d, PROFILE, TEMPLATES)
    assert sorted(p.name for p in outs) == ["Vitor_Pinheiro_Resume_Acme_Labs.docx", "Vitor_Pinheiro_Resume_Acme_Labs.pdf"]


@needs_tools
def test_build_non_ascii_survives(tmp_path):
    d = new_application(tmp_path, "Comgás", "Data Scientist", "2026-10-19")
    (d / "resume.md").write_text("---\nheadline: Engenheiro\nlang: pt\n---\n## EXPERIENCE\n- João cut fines by R$200M → São Paulo – 中文\n", encoding="utf-8")
    (d / "cover-letter.md").write_text("Olá, sou o Vitor.\n", encoding="utf-8")
    outs = build_outputs(d, PROFILE, TEMPLATES)
    pdf = next(p for p in outs if p.name == "Vitor_Pinheiro_Resume_Comgas.pdf")
    text = pdf_text(pdf)
    assert "Vitor Pinheiro" in text and "R$200M" in text and "São Paulo" in text
    assert any(p.name == "Vitor_Pinheiro_Cover_Letter_Comgas.pdf" for p in outs)


def test_public_resume_labels_the_overlapping_qubika_role_as_a_contract():
    # It overlapped Nubank, so the label says why up front: a part-time contract.
    text = (Path(__file__).parents[1] / "resume" / "resume.md").read_text(encoding="utf-8")
    assert "Remote, part-time contract · Feb 2026 – Jul 2026" in text
