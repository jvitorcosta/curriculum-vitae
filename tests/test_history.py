from datetime import date

from cv import cli
from cv.history import Match, blocks, find_matches
from cv.meta import load_meta, save_meta, set_status
from cv.scaffold import new_application
from cv.tracker import collect

TODAY = date(2026, 11, 13)


def _app(root, company, role, day, *statuses):
    folder = new_application(root / "private", company, role, day)
    meta = load_meta(folder / "meta.yaml")
    for status, status_day in statuses:
        set_status(meta, status, status_day)
    save_meta(folder / "meta.yaml", meta)
    return folder


def _rows(root):
    return collect(root / "private")[0]


def test_applied_within_window_matches_across_suffix_and_parens(tmp_path):
    _app(tmp_path, "Acme (Labs)", "ML Engineer", "2026-11-11", ("applied", "2026-11-11"))
    rows = _rows(tmp_path)
    [m] = find_matches(rows, "Acme Digital", TODAY)
    assert isinstance(m, Match)
    assert m.company == "Acme (Labs)" and m.reason == "applied within 180 days"
    assert m.last_status_date == "2026-11-11"


def test_rejected_within_window_matches_spaced_ampersand_name(tmp_path):
    _app(tmp_path, "Bit&Co", "ML Engineer", "2026-08-20", ("applied", "2026-08-20"), ("rejected", "2026-09-01"))
    [m] = find_matches(_rows(tmp_path), "Bit Co", TODAY)
    assert m.reason == "rejected within 90 days"
    assert m.last_status_date == "2026-09-01"
    assert blocks([m], "ML Engineer")


def test_rejected_long_ago_does_not_block(tmp_path):
    _app(tmp_path, "Bit&Co", "ML Engineer", "2026-06-20", ("applied", "2026-06-20"), ("rejected", "2026-07-01"))
    [m] = find_matches(_rows(tmp_path), "Bit Co", TODAY)
    assert m.reason == "older application"
    assert not blocks([m], "ML Engineer")


def test_old_application_is_older_and_does_not_block(tmp_path):
    _app(tmp_path, "Acme (Labs)", "ML Engineer", "2025-03-01", ("applied", "2025-03-01"))
    [m] = find_matches(_rows(tmp_path), "Acme", TODAY)
    assert m.reason == "older application"
    assert not blocks([m], "ML Engineer")


def test_drafts_and_other_companies_are_ignored(tmp_path):
    _app(tmp_path, "Acme (Labs)", "ML Engineer", "2026-11-11")
    _app(tmp_path, "Orbital", "ML Engineer", "2026-11-11", ("applied", "2026-11-11"))
    rows = _rows(tmp_path)
    assert find_matches(rows, "Acme Digital", TODAY) == []
    assert find_matches(rows, "Orb", TODAY) == []
    assert find_matches(rows, "Bit Co", TODAY) == []


def test_blocks_false_for_no_matches():
    assert not blocks([], "ML Engineer")


def test_cli_seen_exit_codes(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    _app(tmp_path, "Acme (Labs)", "ML Engineer", "2026-11-11", ("applied", "2026-11-11"))
    assert cli.main(["seen", "Acme Digital", "Staff Engineer"]) == 3
    out = capsys.readouterr().out
    assert "applied within 180 days" in out and "ML Engineer" in out
    assert cli.main(["seen", "Globex"]) == 0


def test_short_first_token_matches_by_concatenated_name(tmp_path):
    _app(tmp_path, "XY&Z", "ML Engineer", "2026-08-20", ("applied", "2026-08-20"), ("rejected", "2026-09-01"))
    rows = _rows(tmp_path)
    for query in ("XY Z", "XY&Z", "XYZ"):
        [m] = find_matches(rows, query, TODAY)
        assert m.reason == "rejected within 90 days"
        assert blocks([m], "ML Engineer")
    assert find_matches(rows, "XYZW Labs", TODAY) == []


def _reason(tmp_path, status_chain, applied, today=TODAY):
    _app(tmp_path, "Acme (Labs)", "ML Engineer", applied, *status_chain)
    [m] = find_matches(_rows(tmp_path), "Acme", today)
    return m.reason


def test_reject_window_edges(tmp_path):
    # 2026-11-13 minus 90 days = 2026-08-15; minus 91 = 2026-08-14
    chain = (("applied", "2026-06-01"), ("rejected", "2026-08-15"))
    assert _reason(tmp_path, chain, "2026-06-01") == "rejected within 90 days"


def test_reject_window_edge_plus_one(tmp_path):
    chain = (("applied", "2026-06-01"), ("rejected", "2026-08-14"))
    assert _reason(tmp_path, chain, "2026-06-01") == "older application"


def test_apply_window_edges(tmp_path):
    # 2026-11-13 minus 180 days = 2026-05-17; minus 181 = 2026-05-16
    assert _reason(tmp_path, (("applied", "2026-05-17"),), "2026-05-17") == "applied within 180 days"


def test_apply_window_edge_plus_one(tmp_path):
    assert _reason(tmp_path, (("applied", "2026-05-16"),), "2026-05-16") == "older application"


def test_cli_seen_unreadable_meta_is_not_all_clear(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    bad = tmp_path / "private" / "applications" / "2026-01-01-acme-eng"
    bad.mkdir(parents=True)
    (bad / "meta.yaml").write_text("company: [unclosed" + chr(10), encoding="utf-8")
    assert cli.main(["seen", "Acme"]) == 1
    assert "needs fixing" in capsys.readouterr().err
    _app(tmp_path, "Acme", "ML Engineer", "2026-11-11", ("applied", "2026-11-11"))
    assert cli.main(["seen", "Acme"]) == 3  # a blocking match still wins


def test_same_company_empty_names_never_match():
    from cv.history import _same_company
    assert not _same_company("", "")
    assert not _same_company("&&", "&&")
