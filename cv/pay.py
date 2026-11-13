"""Convert CLT, PJ and USD offers to monthly net pay (Decimal money, cents rounded half up)."""

import re
import tomllib
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

Contract = Literal["clt", "pj", "usd"]
CENT = Decimal("0.01")
TABLES_DIR = Path(__file__).parent / "pay_tables"


def _dec(value: object, key: str = "value") -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"{key} must be a number, got {value!r}") from None


def _cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Tables:
    inss: list[tuple[Decimal, Decimal]]  # (upper limit, rate), progressive slices
    inss_ceiling: Decimal
    irrf: list[tuple[Decimal, Decimal, Decimal]]  # (upper limit, rate, deduction)
    irrf_reduction: dict  # full_limit, full_amount, partial_limit, partial_a, partial_b; {} = none
    simplified_deduction: Decimal = Decimal(0)
    prolabore_inss_rate: Decimal = Decimal("0.11")


@dataclass(frozen=True)
class PayParams:
    simples_rate_domestic: Decimal
    simples_rate_export: Decimal
    prolabore: Decimal
    accountant_fee: Decimal
    deel_fee_pct: Decimal
    usd_brl: Decimal
    floor_brl_net: Decimal
    floor_usd: Decimal


def parse_money(text: str) -> Decimal:
    """Parse '15000', '15.000,00', '15,000.00', '15k', '4,5k', 'R$ 15.000', 'USD 4,500'.

    A lone separator followed by exactly three digits is a thousands separator ('15.000');
    otherwise it is a decimal mark ('14,5'). A repeated separator must always group by three
    ('1.234.567'); anything else ('15.000.00') is rejected rather than guessed.
    """
    m = re.fullmatch(r"\s*(?:R\$|US\$|USD|BRL|\$)?\s*([\d.,\s]*\d[\d.,\s]*?)\s*([kK])?\s*", text, re.IGNORECASE)
    if not m:
        raise ValueError(f"Not an amount: {text!r}")
    s = re.sub(r"\s", "", m.group(1))
    multiplier = Decimal(1000) if m.group(2) else Decimal(1)
    bad = ValueError(f"Not an amount (check the digit grouping): {text!r}")
    dot, comma = s.rfind("."), s.rfind(",")
    if dot >= 0 and comma >= 0:
        mark, thousands = (".", ",") if dot > comma else (",", ".")
        int_part, _, frac = s.rpartition(mark)
        if not frac or not re.fullmatch(rf"\d+|\d{{1,3}}(?:\{thousands}\d{{3}})+", int_part):
            raise bad
        digits = int_part.replace(thousands, "") + "." + frac
    else:
        sep = "." if dot >= 0 else "," if comma >= 0 else ""
        if not sep:
            digits = s
        elif s.count(sep) > 1:
            if not re.fullmatch(rf"\d{{1,3}}(?:\{sep}\d{{3}})+", s):
                raise bad
            digits = s.replace(sep, "")
        elif re.fullmatch(rf"\d{{1,3}}\{sep}\d{{3}}", s):
            digits = s.replace(sep, "")
        else:
            int_part, _, frac = s.partition(sep)
            if not int_part or not frac:
                raise bad
            digits = int_part + "." + frac
    return Decimal(digits) * multiplier


def load_tables(year: int) -> Tables:
    with (TABLES_DIR / f"{year}.toml").open("rb") as f:
        raw = tomllib.load(f)
    return Tables(
        inss=[(_dec(r["upto"]), _dec(r["rate"])) for r in raw["inss"]],
        inss_ceiling=_dec(raw["inss_ceiling"]),
        irrf=[(_dec(r["upto"]), _dec(r["rate"]), _dec(r["deduction"])) for r in raw["irrf"]],
        irrf_reduction={k: _dec(v) for k, v in raw.get("irrf_reduction", {}).items()},
        simplified_deduction=_dec(raw.get("simplified_deduction", 0)),
        prolabore_inss_rate=_dec(raw.get("prolabore_inss_rate", "0.11")),
    )


def latest_year() -> int:
    return max(int(p.stem) for p in TABLES_DIR.glob("*.toml"))


def load_params(root: Path) -> tuple[PayParams, bool]:
    """Read private/salary/pay.toml, else pay.example.toml. The bool is True when it fell back."""
    private = root / "private" / "salary" / "pay.toml"
    fell_back = not private.exists()
    path = root / "pay.example.toml" if fell_back else private
    with path.open("rb") as f:
        raw = tomllib.load(f)
    fields = list(PayParams.__dataclass_fields__)
    missing = [k for k in fields if k not in raw]
    if missing:
        raise ValueError(f"{path.name} is missing: {', '.join(missing)}")
    return PayParams(**{k: _dec(raw[k], k) for k in fields}), fell_back


def inss(gross: Decimal, t: Tables) -> Decimal:
    """Employee INSS: progressive slices summed unrounded, total rounded once; nothing above the ceiling."""
    base = min(gross, t.inss_ceiling)
    total, lower = Decimal(0), Decimal(0)
    for upto, rate in t.inss:
        if base <= lower:
            break
        total += (min(base, upto) - lower) * rate
        lower = upto
    return _cents(total)


def irrf(gross: Decimal, t: Tables, inss_paid: Decimal | None = None) -> Decimal:
    """Monthly income tax withheld: table on (gross - max(INSS, simplified deduction)), minus the 2026 reduction."""
    paid = inss(gross, t) if inss_paid is None else inss_paid
    base = max(gross - max(paid, t.simplified_deduction), Decimal(0))
    tax = Decimal(0)
    for upto, rate, deduction in t.irrf:
        if base <= upto:
            tax = max(_cents(base * rate - deduction), Decimal(0))
            break
    return max(tax - _reduction(gross, tax, t.irrf_reduction), Decimal(0))


def _reduction(income: Decimal, tax: Decimal, r: dict) -> Decimal:
    if not r:
        return Decimal(0)
    if income <= r["full_limit"]:
        return min(r["full_amount"], tax)
    if income <= r["partial_limit"]:
        return min(_cents(r["partial_a"] - r["partial_b"] * income), tax)
    return Decimal(0)


def clt_net(gross: Decimal, t: Tables) -> Decimal:
    """Monthly take-home of a CLT salary."""
    return gross - inss(gross, t) - irrf(gross, t)


def clt_annualized(gross: Decimal, t: Tables, benefits: Decimal = Decimal(0)) -> Decimal:
    """Average monthly net over a year: 13 salaries plus the net of the vacation third, over 12, plus benefits."""
    net = clt_net(gross, t)
    vacation_third = clt_net(gross + gross / 3, t) - net
    return _cents((13 * net + vacation_third) / 12) + benefits


def _prolabore_taxes(p: PayParams, t: Tables) -> Decimal:
    inss_pl = _cents(min(p.prolabore, t.inss_ceiling) * t.prolabore_inss_rate)
    return inss_pl + irrf(p.prolabore, t, inss_paid=inss_pl)


def pj_net(invoice: Decimal, p: PayParams, t: Tables, export: bool = False) -> Decimal:
    """Invoice minus Simples, minus INSS and IRRF on the pro-labore, minus the accountant fee."""
    rate = p.simples_rate_export if export else p.simples_rate_domestic
    return invoice - _cents(invoice * rate) - _prolabore_taxes(p, t) - p.accountant_fee


def usd_net(usd: Decimal, p: PayParams, t: Tables) -> Decimal:
    return pj_net(_cents(usd * (1 - p.deel_fee_pct) * p.usd_brl), p, t, export=True)


def _net_of(contract: Contract, amount: Decimal, p: PayParams, t: Tables, export: bool = False) -> Decimal:
    if contract == "clt":
        return clt_net(amount, t)
    if contract == "pj":
        return pj_net(amount, p, t, export=export)
    return usd_net(amount, p, t)


def gross_for_net(contract: Contract, target_net: Decimal, p: PayParams, t: Tables) -> Decimal:
    """Smallest gross (BRL for clt/pj, USD for usd) whose monthly net reaches target_net."""
    lo, hi = Decimal(0), Decimal(10_000_000)
    while hi - lo > CENT:
        mid = (lo + hi) / 2
        if _net_of(contract, mid, p, t) >= target_net:
            hi = mid
        else:
            lo = mid
    return _cents(hi)


def meets_floor(contract: Contract, amount: Decimal, p: PayParams, t: Tables, *, export: bool = False) -> bool:
    if contract == "usd":
        return amount >= p.floor_usd
    return _net_of(contract, amount, p, t, export) >= p.floor_brl_net
