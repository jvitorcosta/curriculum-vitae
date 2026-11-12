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
