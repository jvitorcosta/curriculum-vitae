import datetime

from cv import cli
from cv.funnel import funnel, median_days_to_yield, score_band
from cv.meta import AppMeta


def meta(status="applied", hist=(), channel="LinkedIn", date="2026-01-01", **kw):
    return AppMeta(company="C", role="R", date=date, channel=channel, status=status,
                   history=[{"status": s, "date": d} for s, d in hist], **kw)


def by_key(buckets):
    return {b.key: b for b in buckets}


def test_screening_then_rejected_is_yielded_and_rejected():
    b = funnel([meta("rejected", [("applied", "2026-01-01"), ("screening", "2026-01-05"), ("rejected", "2026-01-09")])], "channel")[0]
    assert (b.sent, b.yielded, b.rejected) == (1, 1, 1)


def test_draft_and_withdrawn_not_sent():
    assert funnel([meta("draft"), meta("withdrawn")], "channel") == []


def test_ghosted_and_open_counted_from_status():
    b = funnel([meta("ghosted"), meta("applied"), meta("interview", [("interview", "2026-01-03")])], "channel")[0]
    assert (b.sent, b.ghosted, b.open, b.yielded) == (3, 1, 2, 1)


def test_sufficient_and_sort():
    metas = [meta(channel="LinkedIn")] * 21 + [meta(channel="Referral")] * 3
    b = funnel(metas, "channel")
    assert [x.key for x in b] == ["LinkedIn", "Referral"]
    assert b[0].sufficient and not b[1].sufficient


def test_since_filters_by_application_date():
    metas = [meta(date="2025-12-31"), meta(date="2026-02-01")]
    assert funnel(metas, "channel", since=datetime.date(2026, 1, 1))[0].sent == 1


def test_score_band():
    assert score_band("4.0") == "4.0–4.4"
    assert score_band("4.5") == "4.5+"
    assert score_band("3.9") == "3.0–3.9"
    assert score_band("2.5") == "<3.0"
    assert score_band("") == "unscored"
    assert score_band("n/a") == "unscored"


def test_funnel_by_score_and_empty_key():
    b = by_key(funnel([meta(score="4.3"), meta(), meta(company_type="br-big")], "score"))
    assert set(b) == {"4.0–4.4", "unscored"}
    assert by_key(funnel([meta(channel="")], "channel"))["(none)"].sent == 1


def test_median_days_to_yield():
    a = meta("screening", [("applied", "2026-01-01"), ("screening", "2026-01-06")])
    b = meta("offer", [("interview", "2026-01-10")])
    assert median_days_to_yield([a, b, meta()]) == 7.0
    assert median_days_to_yield([meta()]) is None


def test_cli_funnel(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    cli.main(["new", "Acme", "Eng", "--date", "2026-01-01", "--channel", "LinkedIn"])
    cli.main(["status", str(tmp_path / "private" / "applications" / "2026-01-01-acme-eng"), "applied", "--date", "2026-01-01"])
    assert cli.main(["funnel", "--by", "channel", "--since", "2025-01-01"]) == 0
    out = capsys.readouterr().out
    assert "LinkedIn" in out and "(small sample)" in out and "Median" in out
    assert cli.main(["funnel", "--since", "bad"]) == 1


def test_since_and_median_use_same_set():
    old = meta("screening", [("screening", "2026-01-30")], date="2025-01-01")  # 394 days, excluded by since
    new = meta("screening", [("screening", "2026-02-04")], date="2026-02-01")  # 3 days
    draft = meta("draft", [("screening", "2026-02-20")], date="2026-02-01")  # not sent
    metas = [old, new, draft]
    assert median_days_to_yield(metas, since=datetime.date(2026, 1, 1)) == 3.0


def test_median_skips_negative_and_unsent():
    neg = meta("screening", [("screening", "2026-01-01")], date="2026-01-05")
    ok = meta("screening", [("screening", "2026-01-04")], date="2026-01-01")
    wd = meta("withdrawn", [("screening", "2026-03-01")], date="2026-01-01")
    assert median_days_to_yield([neg, ok, wd]) == 3.0


def test_buckets_case_insensitive_with_common_spelling():
    metas = [meta(channel="LinkedIn"), meta(channel="LinkedIn"), meta(channel="linkedin "), meta(channel="Referral")]
    b = by_key(funnel(metas, "channel"))
    assert set(b) == {"LinkedIn", "Referral"}
    assert b["LinkedIn"].sent == 3


def test_yielded_by_current_status_without_history():
    assert funnel([meta("interview")], "channel")[0].yielded == 1


def test_score_band_edge_inputs():
    for s in ["nan", "inf", "-inf", "5.1", "-1", "6"]:
        assert score_band(s) == "unscored"
    assert score_band("4,3") == "4.0–4.4"
    assert score_band("5") == "4.5+"
    assert score_band("0") == "<3.0"


def test_cli_funnel_reports_unreadable_meta(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    bad = tmp_path / "private" / "applications" / "2026-01-01-acme-eng"
    bad.mkdir(parents=True)
    (bad / "meta.yaml").write_text("company: [unclosed" + chr(10), encoding="utf-8")
    assert cli.main(["funnel"]) == 0
    assert "needs fixing" in capsys.readouterr().err
