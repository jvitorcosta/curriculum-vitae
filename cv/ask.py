"""Propose an explained salary ask from company and role signals (anchor a band, then rank within it)."""

import json
import tomllib
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal
from pathlib import Path

from cv import pay

COMPANY_SIGNALS = ("size", "rating", "reach", "maturity")
ROLE_SIGNALS = ("years", "level", "org", "demands")
CONTRACTS = ("clt", "pj", "contractor")
HALF = Decimal("0.5")
MARKET_MIN_ROWS = 3
MARKET_MAX_AGE_DAYS = 365


@dataclass(frozen=True)
class Signals:
    company_type: str
    contract: str
    size: int | None = None
    rating: Decimal | None = None
    reach: str | None = None
    maturity: str | None = None
    years: int | None = None
    level: str | None = None
    org: str | None = None
    demands: frozenset[str] = frozenset()


@dataclass(frozen=True)
class AskConfig:
    bands: dict[tuple[str, str], tuple[Decimal, Decimal]]
    maps: dict[str, dict]  # signal -> {"weight": Decimal, "steps": [(at_least, value)]} or {"weight", "values": {label: value}}
    w_company: Decimal
    w_role: Decimal
    nudge: Decimal
    ceilings: dict[str, Decimal]


@dataclass(frozen=True)
class Step:
    name: str
    detail: str


@dataclass(frozen=True)
class AskResult:
    ask: Decimal
    currency: str
    contract: str
    net: Decimal
    below_floor: bool
    band: tuple[Decimal, Decimal]
    band_source: str
    company: Decimal
    role: Decimal
    position: Decimal
    steps: list[Step] = field(default_factory=list)


def _dec(value: object, key: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError(f"{key} must be a number, got {value!r}")
    return pay._dec(value, key)


def load_ask_config(root: Path) -> tuple[AskConfig, bool]:
    """Read private/salary/ask.toml, else ask.example.toml. The bool is True when it fell back."""
    private = root / "private" / "salary" / "ask.toml"
    fell_back = not private.exists()
    path = root / "ask.example.toml" if fell_back else private
    with path.open("rb") as f:
        raw = tomllib.load(f)
    return parse_ask_config(raw, path.name), fell_back


def parse_ask_config(raw: dict, name: str = "ask config") -> AskConfig:
    missing = [k for k in ("w_company", "w_role", "nudge", "bands", "signals") if k not in raw]
    if missing:
        raise ValueError(f"{name} is missing: {', '.join(missing)}")
    w_company, w_role, nudge = (_dec(raw[k], k) for k in ("w_company", "w_role", "nudge"))
    if abs(w_company + w_role - 1) > Decimal("0.001"):
        raise ValueError(f"{name}: w_company + w_role must be 1, got {w_company + w_role}")
    if not 0 <= nudge <= 1:
        raise ValueError(f"{name}: nudge must be between 0 and 1, got {nudge}")
    bands = {}
    for company_type, by_contract in raw["bands"].items():
        for contract, pair in by_contract.items():
            key = f"bands.{company_type}.{contract}"
            if contract not in CONTRACTS:
                raise ValueError(f"{name}: {key}: contract must be one of {', '.join(CONTRACTS)}")
            if not isinstance(pair, list) or len(pair) != 2:
                raise ValueError(f"{name}: {key} must be [low, high]")
            low, high = _dec(pair[0], key), _dec(pair[1], key)
            if low > high:
                raise ValueError(f"{name}: {key} has low above high")
            bands[(company_type, contract)] = (low, high)
    maps = {}
    for signal in COMPANY_SIGNALS + ROLE_SIGNALS:
        spec = raw["signals"].get(signal)
        if spec is None:
            raise ValueError(f"{name} is missing: signals.{signal}")
        key = f"signals.{signal}"
        entry = {"weight": _dec(spec.get("weight", 1), f"{key}.weight")}
        if "steps" in spec:
            entry["steps"] = sorted((_dec(a, key), _dec(v, key)) for a, v in spec["steps"])
        elif "values" in spec:
            entry["values"] = {label: _dec(v, f"{key}.{label}") for label, v in spec["values"].items()}
        else:
            raise ValueError(f"{name}: {key} needs steps or values")
        maps[signal] = entry
    ceilings = {c: _dec(v, f"ceilings.{c}") for c, v in raw.get("ceilings", {}).items()}
    return AskConfig(bands, maps, w_company, w_role, nudge, ceilings)


def currency_of(contract: str) -> str:
    return "USD" if contract == "contractor" else "BRL"


def _monthly(r: dict, currency: str) -> Decimal | None:
    """A row's monthly figure in the given currency, the midpoint for a range; None if it can't be used."""
    if (r.get("currency") or "").strip().upper() != currency:
        return None
    text = (r.get("amount") or "").strip()
    try:
        parts = [pay.parse_money(p) for p in text.split("-")] if text else []
    except ValueError:
        return None
    if len(parts) not in (1, 2):
        return None
    value = sum(parts) / len(parts)
    period = (r.get("period") or "month").strip().lower()
    if period == "year":
        return value / 12
    return value if period == "month" else None


def market_rows(rows: list[dict], company_type: str, contract: str, today: date) -> list[Decimal]:
    """Monthly figures of the usable market rows: same type and contract, not vitor-ask, within 365 days."""
    currency = currency_of(contract)
    out = []
    for r in rows:
        if (r.get("company_type") or "").strip() != company_type or (r.get("contract") or "").strip() != contract:
            continue
        if (r.get("reliability") or "").strip() == "vitor-ask":
            continue
        try:
            when = date.fromisoformat((r.get("date") or "").strip())
        except ValueError:
            continue
        if not 0 <= (today - when).days <= MARKET_MAX_AGE_DAYS:
            continue
        value = _monthly(r, currency)
        if value is not None:
            out.append(value)
    return out


def _percentile(sorted_values: list[Decimal], q: Decimal) -> Decimal:
    idx = (len(sorted_values) - 1) * q
    lo = int(idx)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (idx - lo)


def market_band(rows: list[dict], company_type: str, contract: str, today: date) -> tuple[Decimal, Decimal] | None:
    values = sorted(market_rows(rows, company_type, contract, today))
    if len(values) < MARKET_MIN_ROWS:
        return None
    return _percentile(values, Decimal("0.25")), _percentile(values, Decimal("0.75"))


def _signal_value(signal: str, raw: object, spec: dict) -> Decimal:
    if signal == "demands":
        unknown = sorted(set(raw) - set(spec["values"]))
        if unknown:
            raise ValueError(f"unknown {signal}: {', '.join(unknown)} (known: {', '.join(spec['values'])})")
        return min(sum((spec["values"][d] for d in raw), Decimal(0)), Decimal(1))
    if "steps" in spec:
        value = Decimal(0)
        for at_least, v in spec["steps"]:
            if Decimal(str(raw)) >= at_least:
                value = v
        return value
    if raw not in spec["values"]:
        raise ValueError(f"unknown {signal}: {raw!r} (known: {', '.join(spec['values'])})")
    return spec["values"][raw]


def _score(s: Signals, cfg: AskConfig, names: tuple[str, ...], label: str) -> tuple[Decimal, list[Step]]:
    steps, total, weights = [], Decimal(0), Decimal(0)
    for name in names:
        raw = getattr(s, name)
        if raw is None or (name == "demands" and not raw):
            continue
        spec = cfg.maps[name]
        value = _signal_value(name, raw, spec)
        shown = ", ".join(sorted(raw)) if name == "demands" else raw
        steps.append(Step(name, f"{shown} -> {value:.2f} (weight {spec['weight']})"))
        total += value * spec["weight"]
        weights += spec["weight"]
    if weights == 0:
        steps.append(Step(label, "0.50 (no signals)"))
        return HALF, steps
    score = total / weights
    steps.append(Step(label, f"{score:.2f}"))
    return score, steps


def company_score(s: Signals, cfg: AskConfig) -> tuple[Decimal, list[Step]]:
    return _score(s, cfg, COMPANY_SIGNALS, "company score")


def role_score(s: Signals, cfg: AskConfig) -> tuple[Decimal, list[Step]]:
    return _score(s, cfg, ROLE_SIGNALS, "role score")


def _round_to(value: Decimal, unit: Decimal, rounding=ROUND_HALF_UP) -> Decimal:
    return (value / unit).quantize(Decimal(1), rounding=rounding) * unit


def _money(value: Decimal, currency: str) -> str:
    if currency == "USD":
        return f"USD {value:,.0f}"
    return "R$ " + f"{value:,.0f}".replace(",", ".")


def _pay_contract(contract: str) -> str:
    return "usd" if contract == "contractor" else contract


def _net(contract: str, amount: Decimal, params: pay.PayParams, tables: pay.Tables) -> Decimal:
    if contract == "clt":
        return pay.clt_net(amount, tables)
    if contract == "pj":
        return pay.pj_net(amount, params, tables)
    return pay.usd_net(amount, params, tables)


def propose(s: Signals, cfg: AskConfig, params: pay.PayParams, tables: pay.Tables,
            observations: list[dict], today: date) -> AskResult:
    key = (s.company_type, s.contract)
    if key not in cfg.bands:
        known = ", ".join(f"{t} {c}" for t, c in sorted(cfg.bands))
        raise ValueError(f"no band for {s.company_type} {s.contract} (known: {known})")
    currency = currency_of(s.contract)
    unit = Decimal(100) if currency == "USD" else Decimal(500)
    steps: list[Step] = []

    market = market_band(observations, s.company_type, s.contract, today)
    if market is not None:
        band, source = market, "market"
        n = len(market_rows(observations, s.company_type, s.contract, today))
        steps.append(Step("band", f"{_money(band[0], currency)}–{_money(band[1], currency)} {s.contract}, "
                                  f"market 25th–75th percentile of {n} rows"))
    else:
        band, source = cfg.bands[key], "config"
        n = len(market_rows(observations, s.company_type, s.contract, today))
        steps.append(Step("band", f"{_money(band[0], currency)}–{_money(band[1], currency)} {s.contract}, "
                                  f"config band ({n} market rows, need {MARKET_MIN_ROWS})"))
    low, high = band

    company, company_steps = company_score(s, cfg)
    role, role_steps = role_score(s, cfg)
    steps += company_steps + role_steps
    raw_position = cfg.w_company * company + cfg.w_role * role
    # The get-hired nudge only pulls high positions toward the middle; it never raises a low ask.
    position = raw_position - cfg.nudge * max(raw_position - HALF, Decimal(0))
    nudged = (f"nudged {cfg.nudge} toward the middle = {position:.3f}" if position != raw_position
              else "below the middle, so no nudge")
    steps.append(Step("position", f"{cfg.w_company} x {company:.2f} + {cfg.w_role} x {role:.2f} = {raw_position:.3f}, "
                                  f"{nudged}"))

    ask = low + position * (high - low)
    ceiling = cfg.ceilings.get(s.contract)
    if ceiling is not None and ask > ceiling:
        ask = ceiling
        steps.append(Step("ceiling", f"capped at {_money(ceiling, currency)}"))
    ask = _round_to(ask, unit)
    if ceiling is not None and ask > ceiling:
        ask = _round_to(ceiling, unit, rounding=ROUND_FLOOR)

    below_floor = False
    pc = _pay_contract(s.contract)
    if currency == "USD":
        floor_gross = params.floor_usd
        floor_text = f"floor {_money(params.floor_usd, 'USD')} invoice"
    else:
        floor_gross = pay.gross_for_net(pc, params.floor_brl_net, params, tables)
        floor_text = f"floor {_money(params.floor_brl_net, 'BRL')} net = {_money(floor_gross, 'BRL')} {s.contract}"
    floor_ask = _round_to(floor_gross, unit, rounding=ROUND_CEILING)
    if ask >= floor_gross:
        steps.append(Step("floor", f"clears the {floor_text}"))
    elif high >= floor_gross:
        ask = floor_ask  # rounded up, so it clears the floor even when that is a step above the band's top
        steps.append(Step("floor", f"raised to {_money(ask, currency)} to clear the {floor_text}"))
    else:
        below_floor = True
        steps.append(Step("floor", f"below floor: the band tops out at {_money(high, currency)}, under the "
                                   f"{floor_text} ({_money(floor_ask, currency)})"))

    net = _net(s.contract, ask, params, tables)
    return AskResult(ask, currency, s.contract, net, below_floor, band, source, company, role, position, steps)


CORRECTION_COLUMNS = ("date", "lead_id", "signals_json", "proposed", "corrected")
CALIBRATE_MIN = 10


def signals_json(s: Signals) -> str:
    data = {k: getattr(s, k) for k in Signals.__dataclass_fields__}
    data["rating"] = None if s.rating is None else str(s.rating)
    data["demands"] = sorted(s.demands)
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def signals_from_json(text: str) -> Signals:
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"signals must be a JSON object, got {text!r}")
    unknown = set(data) - set(Signals.__dataclass_fields__)
    if unknown:
        raise ValueError(f"unknown signal fields: {', '.join(sorted(unknown))}")
    for key in ("company_type", "contract"):
        if not isinstance(data.get(key), str):
            raise ValueError(f"{key} must be text, got {data.get(key)!r}")
    for key in ("size", "years"):
        if data.get(key) is not None and (isinstance(data[key], bool) or not isinstance(data[key], int)):
            raise ValueError(f"{key} must be a whole number, got {data[key]!r}")
    for key in ("reach", "maturity", "level", "org"):
        if data.get(key) is not None and not isinstance(data[key], str):
            raise ValueError(f"{key} must be text, got {data[key]!r}")
    if data.get("rating") is not None:
        data["rating"] = _dec(data["rating"], "rating")
        if not data["rating"].is_finite():
            raise ValueError(f"rating must be a number, got {data['rating']}")
    demands = data.get("demands") or []
    if not isinstance(demands, list) or not all(isinstance(d, str) for d in demands):
        raise ValueError(f"demands must be a list of labels, got {demands!r}")
    data["demands"] = frozenset(demands)
    return Signals(**data)


def append_correction(path: Path, lead_id: str, signals: Signals, proposed: Decimal, corrected: Decimal,
                      today: date) -> None:
    """Append one correction row to the TSV, writing the header first when the file is new."""
    if not lead_id or any(c in lead_id for c in "\t\r\n"):
        raise ValueError(f"lead id must be non-empty with no tabs or line breaks: {lead_id!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as f:
        if new:
            f.write("\t".join(CORRECTION_COLUMNS) + "\n")
        f.write("\t".join((today.isoformat(), lead_id, signals_json(signals), str(proposed), str(corrected))) + "\n")


def _mae(cases: list[tuple[Signals, Decimal, date]], cfg: AskConfig, params: pay.PayParams, tables: pay.Tables,
         observations: list[dict]) -> Decimal:
    errors = [abs(propose(s, cfg, params, tables, observations, when).ask - corrected) for s, corrected, when in cases]
    return sum(errors, Decimal(0)) / len(errors)


def calibrate(corrections: list[dict], cfg: AskConfig, params: pay.PayParams, tables: pay.Tables,
              observations: list[dict] = ()) -> tuple[dict, Decimal, Decimal]:
    """Grid-search w_company (w_role = 1 - w_company) and nudge for the lowest mean absolute error
    against the corrected figures. Each correction is re-proposed with the market band as of its own date,
    as `cv ask` saw it then. Returns (best values, MAE now, MAE with the best values). Writes nothing."""
    if len(corrections) < CALIBRATE_MIN:
        raise ValueError(f"calibrate needs at least {CALIBRATE_MIN} corrections, found {len(corrections)}")
    observations = list(observations)
    cases = []
    for n, r in enumerate(corrections, start=2):  # row 1 is the header
        try:
            signals = signals_from_json(r.get("signals_json") or "")
            corrected = pay.parse_money(r.get("corrected") or "")
            when = date.fromisoformat((r.get("date") or "").strip())
            propose(signals, cfg, params, tables, observations, when)
        except (ValueError, TypeError, ArithmeticError) as e:
            raise ValueError(f"ask-corrections.tsv row {n}: {e}") from None
        cases.append((signals, corrected, when))
    before = _mae(cases, cfg, params, tables, observations)
    best, best_key = None, None
    for i in range(11):
        w_company = Decimal(i) / 10
        for j in range(11):
            nudge = Decimal(j) * Decimal("0.05")
            trial = replace(cfg, w_company=w_company, w_role=1 - w_company, nudge=nudge)
            mae = _mae(cases, trial, params, tables, observations)
            # Ties go to the values closest to the current config.
            key = (mae, abs(w_company - cfg.w_company) + abs(nudge - cfg.nudge))
            if best_key is None or key < best_key:
                best, best_key = {"w_company": w_company, "w_role": 1 - w_company, "nudge": nudge}, key
    return best, before, best_key[0]
