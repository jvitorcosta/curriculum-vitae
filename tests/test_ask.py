import dataclasses
import json
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from cv import cli
from cv.ask import Signals, load_ask_config, market_band, propose
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
    assert D(14500) <= r.ask <= D(15500)
    assert r.ask % 500 == 0
    assert r.currency == "BRL"
    assert r.band_source == "config"
    assert not r.below_floor


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
    assert last.startswith("Ask: R$ 15.500 CLT") and "net" in last
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
    assert capsys.readouterr().out.strip().splitlines()[-1].startswith("Ask: R$ 15.500 CLT")


def test_cli_ask_json_round_trips(cli_root, capsys):
    assert cli.main(["ask", *ACCEPTANCE_FLAGS, "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ask"] == "15500" and D(data["net"]) > 0
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
