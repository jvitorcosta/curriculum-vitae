"""Command line: uv run cv <command>."""

import argparse
import csv
import dataclasses
import datetime
import json
import subprocess
import sys
import tomllib
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

from cv import ask, pay
from cv.build import ToolMissing, build_outputs, pdf_text, split_front_matter
from cv.funnel import BY, funnel, median_days_to_yield, render_funnel
from cv.history import blocks, find_matches
from cv.meta import MetaError, load_meta, save_meta, set_status
from cv.profile import load_profile
from cv.scaffold import new_application
from cv.tracker import collect, render_tracker

ROOT = Path(__file__).resolve().parents[1]


def _private() -> Path:
    """Personal data (profile, applications, tracker) lives in a git-ignored folder."""
    return ROOT / "private"


def _today() -> str:
    return datetime.date.today().isoformat()


def cmd_new(args: argparse.Namespace) -> int:
    date = args.date or _today()
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        print(f"Invalid --date {date!r}: use YYYY-MM-DD", file=sys.stderr)
        return 1
    try:
        folder = new_application(_private(), args.company, args.role, date, args.channel, args.url)
    except FileExistsError as e:
        print(f"Already exists: {e.filename}", file=sys.stderr)
        return 1
    print(folder.relative_to(ROOT))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    meta_path = Path(args.folder) / "meta.yaml"
    try:
        meta = load_meta(meta_path)
        set_status(meta, args.status, args.date or _today(), args.note)
    except (MetaError, ValueError) as e:
        print(e, file=sys.stderr)
        return 1
    save_meta(meta_path, meta)
    print(f"{meta.company} - {meta.role}: {meta.status}")
    return 0


def cmd_tracker(args: argparse.Namespace) -> int:
    _private().mkdir(parents=True, exist_ok=True)
    rows, errors = collect(_private())
    text = render_tracker(rows, errors)
    (_private() / "tracker.md").write_text(text, encoding="utf-8")
    print(text.splitlines()[2])
    for e in errors:
        print(f"needs fixing: {e}", file=sys.stderr)
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    try:
        profile = load_profile(ROOT)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    try:
        outputs = build_outputs(Path(args.folder), profile, ROOT / "templates")
    except (ToolMissing, MetaError) as e:
        print(e, file=sys.stderr)
        return 1
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    except yaml.YAMLError as e:
        print(f"Front matter in resume.md or cover-letter.md is not valid YAML (quote values containing ': ' or '#'):\n{e}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as e:
        print(f"{Path(e.cmd[0]).stem} failed:\n{e.stderr}", file=sys.stderr)
        return 1
    for path in outputs:
        print(path)
    for pdf in (p for p in outputs if p.suffix == ".pdf"):
        text = pdf_text(pdf)
        if profile["name"] not in text or profile["email"] not in text:
            print(f"{pdf.name}: PDF text not extractable - ATS would fail", file=sys.stderr)
            return 1
    return 0


def _brl(v) -> str:
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def cmd_pay(args: argparse.Namespace) -> int:
    try:
        amount = pay.parse_money(args.amount)
        benefits = pay.parse_money(getattr(args, "benefits", "0"))
    except ValueError as e:
        print(f"Invalid amount {args.amount!r}: {e}", file=sys.stderr)
        return 1
    try:
        params, fell_back = pay.load_params(ROOT)
        tables = pay.load_tables(pay.latest_year())
    except (OSError, ValueError, KeyError, tomllib.TOMLDecodeError) as e:
        print(f"Pay config problem: {e!r}" if isinstance(e, KeyError) else f"Pay config problem: {e}", file=sys.stderr)
        return 1
    if fell_back:
        print("using pay.example.toml (no private/salary/pay.toml)", file=sys.stderr)
    if args.kind == "target":
        for label, contract in (("CLT", "clt"), ("PJ", "pj"), ("USD", "usd")):
            gross = pay.gross_for_net(contract, amount, params, tables)
            shown = f"USD {gross:,.2f}" if contract == "usd" else _brl(gross)
            print(f"{label}: {shown} / month for {_brl(amount)} net")
        return 0
    if args.kind == "clt":
        net = pay.clt_net(amount, tables)
        print(f"CLT gross {_brl(amount)} -> monthly net {_brl(net)}")
        print(f"Annualized net (13th + vacation third + benefits) {_brl(pay.clt_annualized(amount, tables, benefits))}")
    elif args.kind == "pj":
        net = pay.pj_net(amount, params, tables, export=args.export)
        print(f"PJ invoice {_brl(amount)}{' (export)' if args.export else ''} -> monthly net {_brl(net)}")
    else:
        net = pay.usd_net(amount, params, tables)
        print(f"USD invoice {amount:,.2f} -> monthly net {_brl(net)} at {params.usd_brl} BRL/USD")
    ok = pay.meets_floor(args.kind, amount, params, tables, export=getattr(args, "export", False))
    floor = f"USD {params.floor_usd:,.0f} invoice" if args.kind == "usd" else f"{_brl(params.floor_brl_net)} net"
    print(f"Floor ({floor}): {'meets' if ok else 'BELOW'}")
    return 0


ASK_LEVELS = ("junior", "mid", "senior", "staff", "lead")
ASK_REACH = ("local", "national", "multinational", "usd-payer")
ASK_MATURITY = ("early", "growth", "established")
ASK_ORG = ("engineering", "embedded")
ASK_DEMANDS = ("on-call", "client-facing", "leads-people", "travel")
UNKNOWN = (None, "", "unknown", "none", "null")


def _front_matter(path: Path) -> dict:
    data, _ = split_front_matter(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _card_signals(path: Path) -> ask.Signals:
    """Signals from an evaluation card's front matter; company_type and contract are required."""
    fm = _front_matter(path)
    missing = [k for k in ("company_type", "contract") if fm.get(k) in UNKNOWN]
    if missing:
        raise ValueError(f"{path.name}: front matter is missing {', '.join(missing)}")

    def opt(key, kind):
        value = fm.get(key)
        if isinstance(value, str) and value.strip().lower() in UNKNOWN or value is None:
            return None
        try:
            return kind(value)
        except (ValueError, TypeError, InvalidOperation):
            raise ValueError(f"{path.name}: {key} must be a {kind.__name__}, got {value!r}") from None

    demands = fm.get("demands") or []
    if isinstance(demands, str):
        demands = [d.strip() for d in demands.split(",") if d.strip()]
    if not isinstance(demands, list):
        raise ValueError(f"{path.name}: demands must be a list, got {demands!r}")
    return ask.Signals(
        str(fm["company_type"]), str(fm["contract"]).lower(),
        size=opt("size", int), rating=opt("rating", lambda v: Decimal(str(v))),
        reach=opt("reach", str), maturity=opt("maturity", str), years=opt("years", int),
        level=opt("level", str), org=opt("org", str), demands=frozenset(str(d) for d in demands),
    )


def _flag_signals(args: argparse.Namespace) -> ask.Signals:
    if not args.type or not args.contract:
        raise ValueError("give --card <evaluation.md>, or --type and --contract")
    return ask.Signals(args.type, args.contract, size=args.size, rating=args.rating, reach=args.reach,
                       maturity=args.maturity, years=args.years, level=args.level, org=args.org,
                       demands=frozenset(args.demand or ()))


def _signals(args: argparse.Namespace) -> ask.Signals:
    return _card_signals(Path(args.card)) if args.card else _flag_signals(args)


def _observations() -> list[dict]:
    path = _private() / "salary" / "observations.tsv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _ask_setup():
    cfg, fell_back = ask.load_ask_config(ROOT)
    params, pay_fell_back = pay.load_params(ROOT)
    if fell_back:
        print("using ask.example.toml (no private/salary/ask.toml)", file=sys.stderr)
    if pay_fell_back:
        print("using pay.example.toml (no private/salary/pay.toml)", file=sys.stderr)
    return cfg, params, pay.load_tables(pay.latest_year())


def _jsonable(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def _shown(amount: Decimal, currency: str) -> str:
    return f"USD {amount:,.0f}" if currency == "USD" else "R$ " + f"{amount:,.0f}".replace(",", ".")


def cmd_ask(args: argparse.Namespace) -> int:
    try:
        benefits = pay.parse_money(args.benefits)
        signals = _signals(args)
        cfg, params, tables = _ask_setup()
        result = ask.propose(signals, cfg, params, tables, _observations(), datetime.date.today())
    except (OSError, ValueError, KeyError, tomllib.TOMLDecodeError, yaml.YAMLError) as e:
        print(f"cv ask: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(_jsonable(dataclasses.asdict(result)), ensure_ascii=False, indent=2))
        return 0
    for step in result.steps:
        print(f"{step.name}: {step.detail}")
    line = f"Ask: {_shown(result.ask, result.currency)} {result.contract.upper()} ≈ {_brl(result.net)} net"
    if result.contract == "clt":
        line += f" ({_brl(pay.clt_annualized(result.ask, tables, benefits))} annualized)"
    if result.below_floor:
        line += " · BELOW FLOOR"
    print(line)
    return 0


def _add_signal_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--card", help="evaluation card whose front matter holds the signals")
    p.add_argument("--type", help="company type, a key of [bands] in ask.toml (e.g. br-startup)")
    p.add_argument("--contract", choices=ask.CONTRACTS)
    p.add_argument("--size", type=int, help="employees")
    p.add_argument("--rating", type=Decimal, help="Glassdoor rating, 0-5")
    p.add_argument("--reach", choices=ASK_REACH)
    p.add_argument("--maturity", choices=ASK_MATURITY)
    p.add_argument("--years", type=int, help="years of experience the posting asks for")
    p.add_argument("--level", choices=ASK_LEVELS)
    p.add_argument("--org", choices=ASK_ORG)
    p.add_argument("--demand", action="append", choices=ASK_DEMANDS, help="repeatable")


def cmd_seen(args: argparse.Namespace) -> int:
    rows, errors = collect(_private())
    for e in errors:
        print(f"needs fixing: {e}", file=sys.stderr)
    matches = find_matches(rows, args.company, datetime.date.today())
    for m in matches:
        print(f"{m.date} · {m.status} · {m.role} · {m.reason} · {m.folder.name}")
    if not matches:
        print(f"No earlier application to {args.company}")
    if args.role:
        print(f"Role being considered: {args.role}")
    if blocks(matches, args.role):
        return 3
    # An unreadable meta.yaml may hide a recent application: never report that as clear.
    return 1 if errors else 0


def cmd_funnel(args: argparse.Namespace) -> int:
    since = None
    if args.since:
        try:
            since = datetime.date.fromisoformat(args.since)
        except ValueError:
            print(f"Invalid --since {args.since!r}: use YYYY-MM-DD", file=sys.stderr)
            return 1
    rows, errors = collect(_private())
    metas = [m for _, m in rows]
    print(render_funnel(funnel(metas, args.by, since), median_days_to_yield(metas, since)))
    for e in errors:
        print(f"needs fixing: {e}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cv")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("new", help="create an application folder")
    p.add_argument("company")
    p.add_argument("role")
    p.add_argument("--date")
    p.add_argument("--channel", default="")
    p.add_argument("--url", default="")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("status", help="set an application's status")
    p.add_argument("folder")
    p.add_argument("status")
    p.add_argument("--date")
    p.add_argument("--note", default="")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("tracker", help="regenerate tracker.md")
    p.set_defaults(func=cmd_tracker)

    p = sub.add_parser("build", help="export resume and cover letter to PDF and DOCX")
    p.add_argument("folder")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("pay", help="convert an offer to monthly net, or a target net to gross")
    pay_sub = p.add_subparsers(dest="kind", required=True)
    for kind in ("clt", "pj", "usd"):
        q = pay_sub.add_parser(kind, help=f"monthly net of a {kind.upper()} offer")
        q.add_argument("amount")
        if kind == "clt":
            q.add_argument("--benefits", default="0", help="monthly benefits in BRL added to the annualized figure")
        if kind == "pj":
            q.add_argument("--export", action="store_true", help="use the export Simples rate")
    q = pay_sub.add_parser("target", help="gross needed per contract for a monthly net")
    q.add_argument("amount")
    p.set_defaults(func=cmd_pay)

    p = sub.add_parser("ask", help="an explained salary ask from company and role signals")
    _add_signal_args(p)
    p.add_argument("--benefits", default="0", help="monthly CLT benefits in BRL added to the annualized figure")
    p.add_argument("--json", action="store_true", help="print the result as JSON")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("seen", help="check whether a company was applied to recently")
    p.add_argument("company")
    p.add_argument("role", nargs="?", default="")
    p.set_defaults(func=cmd_seen)

    p = sub.add_parser("funnel", help="which channels, score bands and company types yield replies")
    p.add_argument("--by", choices=BY, default="channel")
    p.add_argument("--since", help="only applications dated on or after YYYY-MM-DD")
    p.set_defaults(func=cmd_funnel)

    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
