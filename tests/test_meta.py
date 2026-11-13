import pytest

from cv.meta import AppMeta, set_status


def test_set_status_appends_history():
    m = AppMeta(company="Umbrella", role="Senior AI Engineer", date="2026-10-01")
    set_status(m, "rejected", "2026-10-16", note="Ashby email")
    assert m.status == "rejected"
    assert m.history[-1] == {"status": "rejected", "date": "2026-10-16", "note": "Ashby email"}


def test_set_status_rejects_unknown():
    with pytest.raises(ValueError):
        set_status(AppMeta(company="X", role="Y", date="2026-01-01"), "hired", "2026-01-02")


def test_load_without_new_fields_defaults_empty(tmp_path):
    from cv.meta import load_meta

    p = tmp_path / "meta.yaml"
    p.write_text("company: A\nrole: B\ndate: '2026-01-01'\nstatus: applied\n", encoding="utf-8")
    m = load_meta(p)
    assert (m.score, m.company_type, m.archetype, m.contract, m.ask) == ("", "", "", "", "")


def test_new_fields_round_trip_and_empty_not_written(tmp_path):
    from cv.meta import load_meta, save_meta

    p = tmp_path / "meta.yaml"
    save_meta(p, AppMeta(company="A", role="B", date="2026-01-01", score="4.3", company_type="br-big"))
    assert load_meta(p).score == "4.3"
    assert load_meta(p).company_type == "br-big"
    text = p.read_text(encoding="utf-8")
    assert "archetype" not in text and "ask" not in text


def test_constants_exposed():
    from cv.meta import ARCHETYPES, COMPANY_TYPES

    assert "br-big" in COMPANY_TYPES and "mlops" in ARCHETYPES
