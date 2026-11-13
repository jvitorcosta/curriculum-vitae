"""Command line: uv run cv <command>."""

import argparse
import datetime
import subprocess
import sys
from pathlib import Path

import yaml

from cv.build import ToolMissing, build_outputs, pdf_text
from cv import pay
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
        params, fell_back = pay.load_params(ROOT)
        tables = pay.load_tables(pay.latest_year())
        amount = pay.parse_money(args.amount)
        benefits = pay.parse_money(getattr(args, "benefits", "0"))
    except (OSError, ValueError) as e:
        print(f"Invalid pay input or config (amount {args.amount!r}): {e}", file=sys.stderr)
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


def cmd_seen(args: argparse.Namespace) -> int:
    rows, _ = collect(_private())
    matches = find_matches(rows, args.company, datetime.date.today())
    for m in matches:
        print(f"{m.date} · {m.status} · {m.role} · {m.reason} · {m.folder.name}")
    if not matches:
        print(f"No earlier application to {args.company}")
    if args.role:
        print(f"Role being considered: {args.role}")
    return 3 if blocks(matches, args.role) else 0


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

    p = sub.add_parser("seen", help="check whether a company was applied to recently")
    p.add_argument("company")
    p.add_argument("role", nargs="?", default="")
    p.set_defaults(func=cmd_seen)

    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
