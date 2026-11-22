import shutil
from pathlib import Path

import pytest

from cv.build import ats_report, build_outputs, compose_document, keyword_report, overflow_warning, pdf_text, resume_headings
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


GOOD_TEXT = ("Vitor Pinheiro\nManaus, AM, Brazil | +00 00 00000-0000 | vitor@example.com\n"
             "SUMMARY\nBuilds things.\nSKILLS\nPython\nEXPERIENCE\nAcme\nEDUCATION\nBSc\n")
HEADINGS = ["SUMMARY", "SKILLS", "EXPERIENCE", "EDUCATION"]


def test_ats_report_passes_good_text():
    assert ats_report(GOOD_TEXT, PROFILE, HEADINGS) == []


def test_ats_report_flags_missing_phone():
    text = GOOD_TEXT.replace("+00 00 00000-0000", "")
    assert any("phone" in p for p in ats_report(text, PROFILE, HEADINGS))


def test_ats_report_skips_phone_when_profile_has_none():
    profile = {**PROFILE, "phone": ""}
    assert ats_report(GOOD_TEXT.replace("+00 00 00000-0000", ""), profile, HEADINGS) == []


def test_ats_report_flags_missing_heading():
    text = GOOD_TEXT.replace("SKILLS\n", "")
    problems = ats_report(text, PROFILE, HEADINGS)
    assert any("SKILLS" in p for p in problems)


def test_ats_report_flags_headings_out_of_order():
    text = GOOD_TEXT.replace("SKILLS\nPython\nEXPERIENCE\nAcme\n", "EXPERIENCE\nAcme\nSKILLS\nPython\n")
    assert any("order" in p for p in ats_report(text, PROFILE, HEADINGS))


@pytest.mark.parametrize("bad", ["(cid:123)", "�"])
def test_ats_report_flags_broken_glyphs(bad):
    problems = ats_report(GOOD_TEXT + f"Skill {bad}\n", PROFILE, HEADINGS)
    assert any("glyph" in p for p in problems)


def test_ats_report_flags_missing_name_and_email():
    problems = ats_report("SUMMARY\n", PROFILE, ["SUMMARY"])
    assert any("name" in p for p in problems) and any("email" in p for p in problems)


def test_resume_headings_follow_source_and_language():
    md = "---\nlang: pt\n---\n## SUMMARY\nx\n### Acme\n## EXPERIENCE\ny\n"
    assert resume_headings(md) == ["RESUMO", "EXPERIÊNCIA"]
    assert resume_headings("## SKILLS\n- a\n") == ["SKILLS"]


def test_keyword_report_splits_found_and_absent():
    posting = "We need Python and Kubernetes. Python, Kubernetes, Airflow. Airflow pipelines and Python."
    found, absent = keyword_report(posting, "I wrote Python and Airflow jobs.")
    assert "python" in found and "airflow" in found
    assert "kubernetes" in absent
    assert "and" not in found + absent


@needs_tools
def test_built_pdf_passes_ats_report(tmp_path):
    d = new_application(tmp_path, "Acme Labs", "AI Engineer", "2026-10-19")
    md = "---\nheadline: AI Engineer\nlang: en\n---\n## SUMMARY\nBuilds.\n\n## SKILLS\n- Python\n\n## EXPERIENCE\n- Built things\n"
    (d / "resume.md").write_text(md, encoding="utf-8")
    pdf = next(p for p in build_outputs(d, PROFILE, TEMPLATES) if p.suffix == ".pdf")
    assert ats_report(pdf_text(pdf), PROFILE, resume_headings(md)) == []


def test_overflow_warning_only_above_limit():
    assert overflow_warning(2) is None
    assert "3 pages" in overflow_warning(3) and "not the oldest" in overflow_warning(3)
