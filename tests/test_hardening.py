import pytest

from cv import cli
from cv.build import compose_document
from cv.meta import load_meta, save_meta, set_status
from cv.scaffold import new_application
from cv.slug import filename_part, slugify
from cv.tracker import collect, render_tracker


def test_cli_rejects_bad_date(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    assert cli.main(["new", "Acme", "Engineer", "--date", "../../x"]) == 1
    assert cli.main(["new", "Acme", "Engineer", "--date", "not-a-date"]) == 1
    assert not (tmp_path / "private" / "applications").exists() or not any((tmp_path / "private" / "applications").iterdir())
    assert "YYYY-MM-DD" in capsys.readouterr().err


def test_non_latin_names_get_a_fallback():
    assert slugify("株式会社") == "company"
    assert filename_part("株式会社") == "Company"


def test_tracker_row_survives_newlines(tmp_path):
    d = new_application(tmp_path, "Acme", "ML Engineer", "2026-01-01")
    m = load_meta(d / "meta.yaml")
    m.channel = "line one\nline two"
    save_meta(d / "meta.yaml", m)
    out = render_tracker(*collect(tmp_path))
    row = [line for line in out.splitlines() if "Acme" in line][0]
    assert "line one line two" in row


def test_folder_without_meta_is_reported(tmp_path):
    new_application(tmp_path, "Acme", "ML Engineer", "2026-01-01")
    (tmp_path / "applications" / "2026-01-02-orphan").mkdir()
    out = render_tracker(*collect(tmp_path))
    assert "Needs fixing" in out and "2026-01-02-orphan" in out


def test_unknown_lang_rejected():
    with pytest.raises(ValueError):
        compose_document({"name": "V", "email": "e"}, '---\nlang: fr\n---\nbody\n', "resume")


def test_history_dates_saved_as_strings(tmp_path):
    d = new_application(tmp_path, "Acme", "ML Engineer", "2026-01-01")
    (d / "meta.yaml").write_text("company: Acme\nrole: ML Engineer\ndate: 2026-01-01\nstatus: draft\nhistory:\n- status: draft\n  date: 2026-01-01\n", encoding="utf-8")
    m = load_meta(d / "meta.yaml")
    set_status(m, "applied", "2026-02-01")
    save_meta(d / "meta.yaml", m)
    assert all(isinstance(h["date"], str) for h in load_meta(d / "meta.yaml").history)
