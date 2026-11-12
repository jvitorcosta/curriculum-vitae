from cv.meta import load_meta, save_meta, set_status
from cv.scaffold import new_application
from cv.tracker import collect, render_tracker


def test_tracker_sorted_with_counts(tmp_path):
    new_application(tmp_path, "Blue Harbor", "ML Engineer", "2026-10-14")
    d = new_application(tmp_path, "Acme Labs", "Senior AI/ML Engineer", "2026-10-19")
    m = load_meta(d / "meta.yaml")
    set_status(m, "applied", "2026-10-19")
    save_meta(d / "meta.yaml", m)
    out = render_tracker(*collect(tmp_path))
    assert out.index("Acme Labs") < out.index("Blue Harbor")
    assert "applied: 1" in out and "draft: 1" in out


def test_tracker_reports_broken_meta(tmp_path):
    new_application(tmp_path, "Hooli", "Senior Agentic Software Engineer", "2026-10-06")
    bad = new_application(tmp_path, "Stark Labs", "Senior Software Engineer AI", "2026-09-26")
    (bad / "meta.yaml").write_text("company: Stark Labs\nstatus: hired\n", encoding="utf-8")
    out = render_tracker(*collect(tmp_path))
    assert "Hooli" in out
    assert "Needs fixing" in out and bad.name in out


def test_tracker_survives_malformed_meta(tmp_path):
    good = new_application(tmp_path, "Hooli", "ML Engineer", "2026-10-06")
    listy = new_application(tmp_path, "Initech", "ML Engineer", "2026-10-05")
    (listy / "meta.yaml").write_text("- just\n- a list\n", encoding="utf-8")
    inty = new_application(tmp_path, "Globex", "ML Engineer", "2026-10-04")
    (inty / "meta.yaml").write_text("company: 123\nrole: 456\ndate: 2026-10-04\nstatus: applied\nchannel: 7\n", encoding="utf-8")
    out = render_tracker(*collect(tmp_path))
    assert "Hooli" in out and "123" in out
    assert "Needs fixing" in out and listy.name in out
