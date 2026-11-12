import pytest

from cv.meta import load_meta
from cv.scaffold import new_application


def test_new_application_creates_folder(tmp_path):
    d = new_application(tmp_path, "Acme Labs", "Senior AI/ML Engineer", "2026-10-19", channel="linkedin")
    assert d.name == "2026-10-19-acme-labs-senior-ai-ml-engineer"
    assert {p.name for p in d.iterdir()} == {"job.md", "resume.md", "cover-letter.md", "answers.md", "meta.yaml"}
    m = load_meta(d / "meta.yaml")
    assert (m.company, m.status, m.history) == ("Acme Labs", "draft", [{"status": "draft", "date": "2026-10-19"}])


def test_same_company_same_day_different_roles(tmp_path):
    a = new_application(tmp_path, "Globex", "Senior AI Engineer", "2026-09-26")
    b = new_application(tmp_path, "Globex", "Senior Platform Engineer with Python", "2026-09-26")
    assert a != b


def test_exact_duplicate_refuses(tmp_path):
    new_application(tmp_path, "Initech", "ML Engineer", "2026-10-14")
    with pytest.raises(FileExistsError):
        new_application(tmp_path, "Initech", "ML Engineer", "2026-10-14")


def test_headline_with_yaml_special_characters_round_trips(tmp_path):
    from cv.build import split_front_matter
    for role in ["Software Engineer (ID: 3117395)", "Engineer #2", "Yes", "[Lead] Engineer"]:
        d = new_application(tmp_path, "Acme Labs", role, "2026-01-01")
        front, _ = split_front_matter((d / "resume.md").read_text(encoding="utf-8"))
        assert front["headline"] == role
