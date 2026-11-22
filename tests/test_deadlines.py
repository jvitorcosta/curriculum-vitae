import importlib.util
from datetime import date
from pathlib import Path

from cv.meta import load_meta, save_meta, set_status
from cv.scaffold import new_application
from cv.tracker import collect, render_tracker

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("next_deadlines", ROOT / "tools" / "next_deadlines.py")
nd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nd)

TODAY = date(2026, 11, 22)


def test_flag_urgent_within_seven_days():
    assert nd.flag("2026-11-22", TODAY) == "urgent"
    assert nd.flag("2026-11-29", TODAY) == "urgent"
    assert nd.flag("2026-11-30", TODAY) == ""


def test_flag_overdue_when_passed():
    assert nd.flag("2026-11-21", TODAY) == "overdue"
    assert nd.flag("2026-11-21 (overdue)", TODAY) == "overdue"


def test_flag_none_without_a_date():
    assert nd.flag("none", TODAY) == ""
    assert nd.flag("none (check if done)", TODAY) == ""


def test_flag_uses_time_range_date():
    assert nd.flag("2026-11-24 10:30–11:00", TODAY) == "urgent"


def test_rows_mark_flags_and_drop_stale_handwritten_marker():
    text = (
        "| Due | Company | Role | What | Link |\n|---|---|---|---|---|\n"
        "| 2026-11-20 (overdue) | Acme | R | Do it | x |\n"
        "| 2026-11-25 | Globex | R | Soon | x |\n"
        "| 2026-12-30 | Initech | R | Later | x |\n"
        "| none | Hooli | R | Whenever | x |\n"
    )
    out = nd.rows(text, TODAY)
    assert out[0].startswith("- 2026-11-20 [OVERDUE] | Acme")
    assert out[1].startswith("- 2026-11-25 [URGENT] | Globex")
    assert out[2].startswith("- 2026-12-30 | Initech")
    assert out[3].startswith("- none | Hooli")


def test_tracker_lists_drafts_under_own_heading(tmp_path):
    d = new_application(tmp_path, "Acme Labs", "ML Engineer", "2026-10-19")
    set_status(m := load_meta(d / "meta.yaml"), "applied", "2026-10-19")
    save_meta(d / "meta.yaml", m)
    new_application(tmp_path, "Blue Harbor", "Data Engineer", "2026-10-20")
    out = render_tracker(*collect(tmp_path))
    assert "## Prepared, not submitted" in out
    section = out.split("## Prepared, not submitted")[1]
    assert "Blue Harbor" in section and "Acme Labs" not in section
    assert "Not counted as quiet" in section


def test_tracker_without_drafts_has_no_draft_heading(tmp_path):
    d = new_application(tmp_path, "Acme Labs", "ML Engineer", "2026-10-19")
    set_status(m := load_meta(d / "meta.yaml"), "applied", "2026-10-19")
    save_meta(d / "meta.yaml", m)
    assert "Prepared, not submitted" not in render_tracker(*collect(tmp_path))
