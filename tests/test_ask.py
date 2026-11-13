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
