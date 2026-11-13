import dataclasses
import json
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from cv import cli
from cv.ask import (
    Signals,
    append_correction,
    calibrate,
    load_ask_config,
    market_band,
    propose,
    signals_from_json,
    signals_json,
)
from cv.pay import load_params, load_tables

D = Decimal
REPO = Path(__file__).resolve().parents[1]
TODAY = date(2026, 11, 13)


@pytest.fixture
def example_root(tmp_path):
    """A root with only the shipped example configs, as in a fresh clone."""
    for name in ("ask.example.toml", "pay.example.toml"):
        shutil.copy(REPO / name, tmp_path / name)
    return tmp_path


@pytest.fixture
def cfg(example_root):
    config, fell_back = load_ask_config(example_root)
    assert fell_back
    return config


@pytest.fixture
def params(example_root):
    return load_params(example_root)[0]


@pytest.fixture
def tables():
    return load_tables(2026)


def acceptance():
    return Signals("br-startup", "clt", size=1000, rating=D("3.9"), reach="national", maturity="growth",
                   years=None, level="mid", org="embedded")


def row(amount, contract="clt", currency="BRL", period="month", reliability="posted",
        company_type="br-startup", when="2026-10-01"):
    return {"date": when, "company": "Example Co", "company_type": company_type, "contract": contract,
            "amount": amount, "currency": currency, "period": period, "reliability": reliability}


def test_acceptance_mid_embedded_br_startup(cfg, params, tables):
    r = propose(acceptance(), cfg, params, tables, [], TODAY)
    assert r.ask == D(15000)
    assert r.currency == "BRL"
    assert r.band_source == "config"
    assert not r.below_floor


def test_nudge_only_pulls_high_positions_down(cfg, params, tables):
    s = acceptance()
    no_nudge = propose(s, dataclasses.replace(cfg, nudge=D(0)), params, tables, [], TODAY)
    full = propose(s, dataclasses.replace(cfg, nudge=D(1)), params, tables, [], TODAY)
    assert no_nudge.position < D("0.5") and full.position == no_nudge.position
    top = Signals("br-big", "clt", size=8000, rating=D("4.5"), reach="multinational", maturity="established",
                  years=5, level="senior", org="engineering")
    raw = propose(top, dataclasses.replace(cfg, nudge=D(0)), params, tables, [], TODAY).position
    half = propose(top, dataclasses.replace(cfg, nudge=D("0.5")), params, tables, [], TODAY).position
    assert half == raw - D("0.5") * (raw - D("0.5"))


def test_top_company_senior_lands_near_top(cfg, params, tables):
    s = Signals("br-big", "clt", size=8000, rating=D("4.5"), reach="multinational", maturity="established",
                years=5, level="senior", org="engineering", demands=frozenset({"on-call"}))
    r = propose(s, cfg, params, tables, [], TODAY)
    assert r.position >= D("0.75")


def test_all_unknown_is_middle(cfg, params, tables):
    r = propose(Signals("br-startup", "clt"), cfg, params, tables, [], TODAY)
    assert r.company == r.role == D("0.5")
    assert any("no signals" in s.detail for s in r.steps)
    assert r.ask == D(17500)  # the band's middle; the nudge keeps 0.5 where it is


def test_market_band_needs_three_market_rows():
    rows = [row("14000"), row("16000")] + [row("18000", reliability="vitor-ask") for _ in range(5)]
    assert market_band(rows, "br-startup", "clt", TODAY) is None
    rows = [row("14000"), row("15000-20000"), row("216000", period="year"), row("5000", currency="USD")]
    assert market_band(rows, "br-startup", "clt", TODAY) == (D(15750), D(17750))


def test_market_band_ignores_old_and_other_type_rows():
    rows = [row("14000"), row("15000"), row("16000", when="2025-01-01"), row("17000", company_type="br-big")]
    assert market_band(rows, "br-startup", "clt", TODAY) is None


def test_market_band_is_used_and_said(cfg, params, tables):
    rows = [row("16000"), row("17000"), row("18000")]
    r = propose(acceptance(), cfg, params, tables, rows, TODAY)
    assert r.band_source == "market"
    assert r.band == (D(16500), D(17500))
    r = propose(acceptance(), cfg, params, tables, rows[:2], TODAY)
    assert r.band_source == "config"
    assert any("2 market rows" in s.detail for s in r.steps)


def test_below_floor_band_flags(cfg, params, tables):
    low = dataclasses.replace(cfg, bands={**cfg.bands, ("br-regional", "clt"): (D(8000), D(9500))})
    r = propose(Signals("br-regional", "clt"), low, params, tables, [], TODAY)
    assert r.below_floor is True
    assert any("below floor" in s.detail for s in r.steps)


def test_floor_raises_ask_when_band_reaches_it(cfg, params, tables):
    # Floor 10000 net needs about 13.5k CLT gross: a 12–16k band at the bottom is raised to clear it.
    band = dataclasses.replace(cfg, bands={**cfg.bands, ("br-regional", "clt"): (D(12000), D(16000))}, nudge=D(0))
    s = Signals("br-regional", "clt", level="junior", org="embedded")
    r = propose(s, band, params, tables, [], TODAY)
    assert not r.below_floor
    assert r.net >= params.floor_brl_net
    assert r.ask % 500 == 0


def test_usd_rounds_to_100(cfg, params, tables):
    r = propose(Signals("offshore-usd", "contractor", level="senior"), cfg, params, tables, [], TODAY)
    assert r.ask % 100 == 0
    assert r.currency == "USD"


def test_unknown_band_errors(cfg, params, tables):
    with pytest.raises(ValueError, match="no band"):
        propose(Signals("br-big", "contractor"), cfg, params, tables, [], TODAY)


# CLI

ACCEPTANCE_FLAGS = ["--type", "br-startup", "--contract", "clt", "--size", "1000", "--rating", "3.9",
                    "--reach", "national", "--maturity", "growth", "--level", "mid", "--org", "embedded"]


@pytest.fixture
def cli_root(example_root, monkeypatch):
    monkeypatch.setattr(cli, "ROOT", example_root)
    return example_root


def test_cli_ask_flags_prints_steps_and_ask(cli_root, capsys):
    assert cli.main(["ask", *ACCEPTANCE_FLAGS]) == 0
    out = capsys.readouterr()
    assert "band:" in out.out and "role score:" in out.out
    last = out.out.strip().splitlines()[-1]
    assert last.startswith("Ask: R$ 15.000 CLT") and "net" in last
    assert "using ask.example.toml" in out.err


def test_cli_ask_all_unknown_exits_zero(cli_root, capsys):
    assert cli.main(["ask", "--type", "br-startup", "--contract", "pj"]) == 0
    assert "no signals" in capsys.readouterr().out


def test_cli_ask_card_missing_type_errors(cli_root, tmp_path, capsys):
    card = tmp_path / "evaluation.md"
    card.write_text("---\ncontract: clt\nlevel: mid\n---\n\n# Card\n", encoding="utf-8")
    assert cli.main(["ask", "--card", str(card)]) == 1
    err = capsys.readouterr().err
    assert "company_type" in err and "contract" not in err.split("missing", 1)[-1]


def test_cli_ask_card_without_front_matter_names_both(cli_root, tmp_path, capsys):
    card = tmp_path / "evaluation.md"
    card.write_text("# Card\n\nno front matter\n", encoding="utf-8")
    assert cli.main(["ask", "--card", str(card)]) == 1
    err = capsys.readouterr().err
    assert "company_type" in err and "contract" in err


def test_cli_ask_card_reads_signals(cli_root, tmp_path, capsys):
    card = tmp_path / "evaluation.md"
    card.write_text("---\ncompany_type: br-startup\ncontract: clt\nsize: 1000\nrating: 3.9\nreach: national\n"
                    "maturity: growth\nyears: null\nlevel: mid\norg: embedded\ndemands: []\n---\n", encoding="utf-8")
    assert cli.main(["ask", "--card", str(card)]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1].startswith("Ask: R$ 15.000 CLT")


def test_cli_ask_json_round_trips(cli_root, capsys):
    assert cli.main(["ask", *ACCEPTANCE_FLAGS, "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ask"] == "15000" and D(data["net"]) > 0
    assert data["steps"] and {"name", "detail"} <= set(data["steps"][0])


def test_cli_ask_uses_private_observations(cli_root, capsys):
    salary = cli_root / "private" / "salary"
    salary.mkdir(parents=True)
    header = "date\tcompany\tcompany_type\tsize\trole\tseniority\tcontract\tamount\tcurrency\tperiod\tsource\treliability\tnote\n"
    rows = "".join(f"{date.today().isoformat()}\tExample Co\tbr-startup\t\tEngineer\tsenior\tclt\t{a}\tBRL\tmonth\tsite\tposted\t\n"
                   for a in ("16000", "17000", "18000"))
    (salary / "observations.tsv").write_text(header + rows, encoding="utf-8")
    assert cli.main(["ask", *ACCEPTANCE_FLAGS]) == 0
    assert "market 25th" in capsys.readouterr().out


def test_cli_ask_unknown_type_errors(cli_root, capsys):
    assert cli.main(["ask", "--type", "nope", "--contract", "clt"]) == 1
    assert "no band" in capsys.readouterr().err


# Corrections and calibration

def test_correct_appends_row(tmp_path):
    path = tmp_path / "salary" / "ask-corrections.tsv"
    s = Signals("br-startup", "clt", rating=D("3.9"), level="mid", demands=frozenset({"travel"}))
    append_correction(path, "lead-1", s, D(15500), D(15000), TODAY)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0].split("\t") == ["date", "lead_id", "signals_json", "proposed", "corrected"]
    assert len(lines) == 2
    date_, lead, sj, proposed, corrected = lines[1].split("\t")
    assert (date_, lead, proposed, corrected) == ("2026-11-13", "lead-1", "15500", "15000")
    assert signals_from_json(sj) == s
    append_correction(path, "lead-2", s, D(15500), D(15000), TODAY)
    assert len(path.read_text(encoding="utf-8").splitlines()) == 3


def test_correct_rejects_tab_in_lead_id(tmp_path):
    with pytest.raises(ValueError):
        append_correction(tmp_path / "c.tsv", "a\tb", Signals("br-startup", "clt"), D(1), D(1), TODAY)


def _corrections(n):
    senior = Signals("br-startup", "clt", size=8000, rating=D("4.5"), reach="multinational", years=5, level="senior")
    return [{"date": "2026-11-01", "lead_id": f"lead-{i}", "signals_json": signals_json(senior),
             "proposed": "19000", "corrected": "15000"} for i in range(n)]


def test_calibrate_reduces_error(cfg, params, tables):
    best, before, after = calibrate(_corrections(10), cfg, params, tables)
    assert set(best) == {"w_company", "w_role", "nudge"}
    assert best["w_company"] + best["w_role"] == 1
    assert after < before


def _write_corrections(root, rows):
    salary = root / "private" / "salary"
    salary.mkdir(parents=True, exist_ok=True)
    header = "date\tlead_id\tsignals_json\tproposed\tcorrected\n"
    body = "".join("\t".join(r[k] for k in ("date", "lead_id", "signals_json", "proposed", "corrected")) + "\n"
                   for r in rows)
    (salary / "ask-corrections.tsv").write_text(header + body, encoding="utf-8")


def test_calibrate_needs_ten(cli_root, capsys):
    _write_corrections(cli_root, _corrections(9))
    assert cli.main(["ask", "calibrate"]) == 1
    assert "10" in capsys.readouterr().err


def test_calibrate_without_file_needs_ten(cli_root, capsys):
    assert cli.main(["ask", "calibrate"]) == 1
    assert "10" in capsys.readouterr().err


def test_cli_calibrate_prints_and_never_writes_config(cli_root, capsys):
    private_cfg = cli_root / "private" / "salary" / "ask.toml"
    _write_corrections(cli_root, _corrections(10))
    shutil.copy(cli_root / "ask.example.toml", private_cfg)
    before = private_cfg.read_bytes()
    assert cli.main(["ask", "calibrate"]) == 0
    out = capsys.readouterr().out
    assert "w_company" in out and "nudge" in out and "MAE" in out
    assert private_cfg.read_bytes() == before


def test_cli_correct_records_proposed_and_figure(cli_root, capsys):
    assert cli.main(["ask", "correct", "lead-9", "15k", *ACCEPTANCE_FLAGS]) == 0
    lines = (cli_root / "private" / "salary" / "ask-corrections.tsv").read_text(encoding="utf-8").splitlines()
    row = dict(zip(lines[0].split("\t"), lines[1].split("\t")))
    assert row["lead_id"] == "lead-9" and row["proposed"] == "15000" and row["corrected"] == "15000"
    assert signals_from_json(row["signals_json"]) == acceptance()


def test_cli_correct_needs_signals(cli_root, capsys):
    assert cli.main(["ask", "correct", "lead-9", "15000"]) == 1
    assert "--type" in capsys.readouterr().err


# Review fixes

def test_calibrate_uses_market_band_as_of_each_correction(cfg, params, tables):
    # Market rows put br-startup clt at 16.5–17.5k, so with no signals cv ask proposed 17k (the config band gives 17.5k).
    obs = [row("16000", when="2026-10-01"), row("17000", when="2026-10-01"), row("18000", when="2026-10-01")]
    corrections = [{"date": "2026-11-01", "lead_id": f"l{i}", "signals_json": signals_json(Signals("br-startup", "clt")),
                    "proposed": "17000", "corrected": "16500"} for i in range(10)]
    best, before, after = calibrate(corrections, cfg, params, tables, obs)
    assert after <= before
    assert before == 500  # 0.5 in the market band = 17000, not the config band's 17500 (error 1000)


def test_card_years_none_means_none_asked(cli_root, tmp_path, capsys):
    card = tmp_path / "evaluation.md"
    card.write_text("---\ncompany_type: br-startup\ncontract: clt\nyears: none\ndemands: none\n---\n", encoding="utf-8")
    assert cli.main(["ask", "--card", str(card), "--json"]) == 0
    steps = json.loads(capsys.readouterr().out)["steps"]
    assert any(s["name"] == "years" and s["detail"].startswith("0 ->") for s in steps)


@pytest.mark.parametrize("value", ["NaN", "9", "abc"])
def test_card_bad_rating_is_a_clean_error(cli_root, tmp_path, capsys, value):
    card = tmp_path / "evaluation.md"
    card.write_text(f"---\ncompany_type: br-startup\ncontract: clt\nrating: {value}\n---\n", encoding="utf-8")
    assert cli.main(["ask", "--card", str(card)]) == 1
    assert "rating" in capsys.readouterr().err


@pytest.mark.parametrize("line", ["2026-11-01\tl1", "2026-11-01\tl1\t[1]\t1\t1", '2026-11-01\tl1\t{"company_type":"br-startup","contract":"clt","size":"abc"}\t1\t1'])
def test_calibrate_bad_row_is_a_clean_error(cli_root, capsys, line):
    salary = cli_root / "private" / "salary"
    salary.mkdir(parents=True)
    rows = [line] + ["\t".join(r[k] for k in ("date", "lead_id", "signals_json", "proposed", "corrected"))
                     for r in _corrections(10)]
    (salary / "ask-corrections.tsv").write_text("date\tlead_id\tsignals_json\tproposed\tcorrected\n" + "\n".join(rows) + "\n",
                                                encoding="utf-8")
    assert cli.main(["ask", "calibrate"]) == 1
    assert "row 2" in capsys.readouterr().err
