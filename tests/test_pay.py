from decimal import Decimal

import pytest

from cv import cli
from cv.pay import (
    PayParams,
    Tables,
    clt_annualized,
    clt_net,
    gross_for_net,
    inss,
    irrf,
    load_params,
    load_tables,
    meets_floor,
    parse_money,
    pj_net,
    usd_net,
)

D = Decimal

EXAMPLE = """
simples_rate_domestic = 0.06
simples_rate_export = 0.0305
prolabore = 4500
accountant_fee = 300
deel_fee_pct = 0.012
usd_brl = 5.0
floor_brl_net = 10000
floor_usd = 4000
"""


@pytest.fixture
def tables():
    return Tables(
        inss=[(D(2000), D("0.10")), (D(5000), D("0.20"))],
        inss_ceiling=D(5000),
        irrf=[(D(3000), D(0), D(0)), (D(10**9), D("0.10"), D(300))],
        irrf_reduction={},
    )


@pytest.fixture
def params():
    return PayParams(
        simples_rate_domestic=D("0.06"),
        simples_rate_export=D("0.0305"),
        prolabore=D(4500),
        accountant_fee=D(300),
        deel_fee_pct=D("0.012"),
        usd_brl=D(5),
        floor_brl_net=D(10000),
        floor_usd=D(4000),
    )


def test_parse_money_formats():
    for s in ["15000", "15.000,00", "15,000.00", "15k", "R$ 15.000", " 15 000 "]:
        assert parse_money(s) == Decimal(15000)
    assert parse_money("USD 4,500") == Decimal(4500)


def test_parse_money_never_inflates_br_format():
    assert parse_money("15.000,00") != Decimal(1500000)
    assert parse_money("1.234,56") == D("1234.56")
    assert parse_money("1,234.56") == D("1234.56")
    assert parse_money("14,5") == D("14.5")
    assert parse_money("1.5k") == D(1500)


def test_parse_money_rejects_garbage():
    for s in ["", "abc", "R$"]:
        with pytest.raises(ValueError):
            parse_money(s)


def test_inss_capped_above_ceiling(tables):
    # 10% of 2,000 + 20% of 3,000 = 800, and nothing more above the 5,000 ceiling
    assert inss(Decimal(9000), tables) == inss(Decimal(5000), tables) == Decimal(800)


def test_inss_bracket_boundary(tables):
    assert inss(Decimal(2000), tables) == Decimal(200)
    assert inss(Decimal("2000.01"), tables) == Decimal("200.00")  # 0.01 x 20% rounds to 0.00


def test_irrf_uses_deduction_and_inss(tables):
    # gross 4000: inss 200+400=600, base 3400, 10% - 300 = 40
    assert irrf(D(4000), tables) == D("40.00")
    assert irrf(D(2500), tables) == D("0.00")


def test_irrf_reduction_exempts_up_to_5000():
    t = load_tables(2026)
    assert irrf(D(5000), t) == D("0.00")
    assert irrf(D(4000), t) == D("0.00")


def test_irrf_reduction_partial_and_none_above():
    t = load_tables(2026)
    assert irrf(D(6000), t) == D("385.10")
    # above 7,350 the full table applies, no reduction
    base = D(8000) - inss(D(8000), t)
    full = (base * D("0.275") - D("908.73")).quantize(D("0.01"))
    assert irrf(D(8000), t) == full


def test_real_2026_tables_loaded():
    t = load_tables(2026)
    assert t.inss_ceiling == D("8475.55")
    assert inss(D(20000), t) == inss(D("8475.55"), t)


def test_clt_net_real_tables_ballpark():
    t = load_tables(2026)
    assert D(10300) < clt_net(D(14000), t) < D(10500)


def test_clt_annualized_adds_thirteenth_and_vacation(tables):
    net = clt_net(D(4000), tables)
    ann = clt_annualized(D(4000), tables)
    assert ann > net
    assert clt_annualized(D(4000), tables, D(500)) == ann + 500


def test_pj_net_export_uses_export_rate(params, tables):
    assert pj_net(Decimal(20000), params, tables, export=True) > pj_net(Decimal(20000), params, tables)


def test_usd_net_converts_with_deel_fee(params, tables):
    expected = pj_net(D(1000) * (1 - D("0.012")) * D(5), params, tables, export=True)
    assert usd_net(D(1000), params, tables) == expected


def test_gross_for_net_round_trips(params, tables):
    g = gross_for_net("pj", Decimal(14500), params, tables)
    assert abs(pj_net(g, params, tables) - Decimal(14500)) <= 1


def test_gross_for_net_clt_and_usd(params, tables):
    g = gross_for_net("clt", D(8000), params, tables)
    assert abs(clt_net(g, tables) - D(8000)) <= 1
    u = gross_for_net("usd", D(14500), params, tables)
    assert abs(usd_net(u, params, tables) - D(14500)) <= 10


def test_floor_usd_on_invoice(params, tables):
    assert meets_floor("usd", Decimal(4000), params, tables) and not meets_floor("usd", Decimal(3999), params, tables)


def test_floor_br_on_net(params, tables):
    assert meets_floor("pj", D(20000), params, tables)
    assert not meets_floor("pj", D(5000), params, tables)


def test_missing_private_params_falls_back(tmp_path):
    (tmp_path / "pay.example.toml").write_text(EXAMPLE, encoding="utf-8")
    params, fell_back = load_params(tmp_path)
    assert fell_back is True
    assert params.floor_usd == D(4000)


def test_private_params_win(tmp_path):
    (tmp_path / "pay.example.toml").write_text(EXAMPLE, encoding="utf-8")
    (tmp_path / "private" / "salary").mkdir(parents=True)
    (tmp_path / "private" / "salary" / "pay.toml").write_text(EXAMPLE.replace("4000", "4500"), encoding="utf-8")
    params, fell_back = load_params(tmp_path)
    assert fell_back is False
    assert params.floor_usd == D(4500)


def test_cli_pay_target_prints_three_contracts(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    (tmp_path / "pay.example.toml").write_text(EXAMPLE, encoding="utf-8")
    assert cli.main(["pay", "target", "14500"]) == 0
    out = capsys.readouterr()
    assert all(k in out.out for k in ("CLT", "PJ", "USD"))
    assert "pay.example.toml" in out.err


def test_cli_pay_pj_and_clt(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    (tmp_path / "pay.example.toml").write_text(EXAMPLE, encoding="utf-8")
    assert cli.main(["pay", "pj", "16.000,00", "--export"]) == 0
    assert "net" in capsys.readouterr().out.lower()
    assert cli.main(["pay", "clt", "14k", "--benefits", "1000"]) == 0
    assert "annualized" in capsys.readouterr().out.lower()


def test_cli_pay_bad_amount(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    (tmp_path / "pay.example.toml").write_text(EXAMPLE, encoding="utf-8")
    assert cli.main(["pay", "pj", "abc"]) == 1
    assert "amount" in capsys.readouterr().err.lower()


def test_inss_max_contribution_real_2026_rounds_once():
    # 121.575 + 115.3656 + 174.1716 + 576.9792 = 988.0914 -> 988.09 (summed from the official brackets)
    t = load_tables(2026)
    assert inss(D("8475.55"), t) == inss(D(20000), t) == D("988.09")


def test_floor_honours_export_rate(params, tables):
    # find an invoice that clears the floor only at the export rate
    domestic = gross_for_net("pj", params.floor_brl_net, params, tables)
    amount = domestic - D(100)
    assert pj_net(amount, params, tables, export=True) >= params.floor_brl_net
    assert not meets_floor("pj", amount, params, tables)
    assert meets_floor("pj", amount, params, tables, export=True)


def test_parse_money_rejects_malformed_grouping_and_junk():
    for s in ["15.000.00", "15,000,00", "1.234.56", "15 mil", "1O000", "-5", "15kk", "12abc"]:
        with pytest.raises(ValueError):
            parse_money(s)


def test_parse_money_pins_valid_forms():
    assert parse_money("4,5k") == D(4500)
    assert parse_money("15,000") == D(15000)
    assert parse_money("1.234.567") == D(1234567)
    assert parse_money("1.234.567,89") == D("1234567.89")
    for s in ["R$ 15.000", "USD 15000", "BRL 15k", "US$15,000", "$15000"]:
        assert parse_money(s) == D(15000)


def test_cli_pay_bad_config_value_names_key(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    (tmp_path / "pay.example.toml").write_text(EXAMPLE.replace("usd_brl = 5.0", 'usd_brl = "abc"'), encoding="utf-8")
    assert cli.main(["pay", "clt", "10000"]) == 1
    err = capsys.readouterr().err
    assert "usd_brl" in err and "Traceback" not in err


def test_cli_pay_bad_amount_reports_amount_not_config(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    (tmp_path / "pay.example.toml").write_text(EXAMPLE, encoding="utf-8")
    assert cli.main(["pay", "clt", "15 mil"]) == 1
    err = capsys.readouterr().err
    assert "15 mil" in err and "config" not in err.lower()
