# Vitor Pinheiro · AI/ML Software Engineer

**[📄 Resume (PDF)](resume/Vitor_Pinheiro_Resume.pdf)** · [Word version](resume/Vitor_Pinheiro_Resume.docx) · [Read it here](resume/resume.md) · [LinkedIn](https://www.linkedin.com/in/jvpro/) · [GitHub](https://github.com/jvitorcosta)

I'm an AI/ML engineer from Manaus, Brazil, with 5 years building production ML and LLM systems, mostly in fintech: lending at Nubank, fraud detection for Coastal Community Bank through Qubika, and demand forecasting for Comgás at EloGroup.

### A few things I've built

- **Fraud model for Coastal Community Bank (Qubika).** A LightGBM model that cut transaction-monitoring alerts by 99.2% and raised analyst-facing precision from 1.29% to 76.4% on a 24-month backtest, plus a SHAP + LLM layer that explains every alert in plain language.
- **Support agent at Nubank.** A LangGraph assistant over our framework's code, docs and Slack history that resolves 80% of support tickets on its own (10 → 2 a week).
- **Gas demand forecasting (EloGroup).** Time-series work behind an ensemble forecast that helped Comgás avoid roughly R$200M in contractual fines in three months.
- **[Car Cyberdeck](https://github.com/jvitorcosta/car-cyberdeck).** A side project: ESP32 firmware that shows my Spotify music on the car dashboard as a Pokémon battle, with a Bluetooth OBD gauge cluster.

The full record, with every project and the numbers behind it, is in [`main/`](main/).

---

## How this repo works

This is my resume kept as code, in public on purpose: an example of a developer managing their own career record the way they'd manage any other project. Markdown is the source; PDF and DOCX are what gets sent.

- `main/` is the full record of experience, projects and skills, each accomplishment with its facts and the approved ways to phrase it. Every tailored resume is drawn from it, so each claim traces back to one place.
- `resume/` is the general resume above, built with `uv run python tools/build_public_resume.py`.
- `case-studies/` holds the write-ups published on [my site](https://jvitorcosta.github.io).
- `cv/` is a small Python CLI (uv, pandoc, Typst) that scaffolds applications, tracks their status and exports ATS-friendly PDF/DOCX.
- `examples/sample-application/` is a made-up application ("Example Labs") showing what one looks like end to end.
- `tools/leak_scan.py` runs before every commit and reports `file:line` for anything private that slipped into a file about to be committed, PDF and DOCX included.

The personal half (contact details, the applications themselves, the tracker, answers to application forms, internal notes) lives in `private/`, a separate private repo nested in this folder and ignored here. Without it, everything falls back to `profile.example.yaml` and `claims-banned.example.toml`, so a fresh clone still tests and builds.

Tailoring is done with Claude Code following the rules in [`CLAUDE.md`](CLAUDE.md): reword and reorder freely, but never add a metric, tool or date that isn't in `main/`.

### Try it

```bash
git clone https://github.com/jvitorcosta/curriculum-vitae && cd curriculum-vitae
uv run pytest -q
uv run cv build examples/sample-application
```

### Commands

Run with `uv run cv <command>` from the repo root.

| Command | What it does |
|---|---|
| `cv new "<company>" "<role>" [--date YYYY-MM-DD] [--channel linkedin] [--url URL]` | Create `private/applications/<date>-<company>-<role>/` |
| `cv status <folder> <status> [--date] [--note]` | Record a status change (draft, applied, screening, interview, offer, rejected, withdrawn, ghosted) |
| `cv build <folder>` | Export resume and cover letter to `out/` as PDF and DOCX |
| `cv tracker` | Regenerate `private/tracker.md` |
| `cv pay clt\|pj\|usd <amount> [--benefits N] [--export]` | Convert an offer to monthly net and check it against your floor (`--benefits` for CLT, `--export` for PJ) |
| `cv pay target <net>` | Gross needed per contract for a monthly net (PJ is solved at the domestic Simples rate) |
| `cv seen "<Company>" ["<Role>"]` | Check for a recent application to the same company; exit 3 = blocked, 1 = error (including unreadable `meta.yaml`) |
| `cv funnel [--by channel\|score\|company_type\|archetype\|contract] [--since YYYY-MM-DD]` | Reply rates by bucket, with small-sample warnings and the median days to first screening/interview |

`cv pay` setup: copy `pay.example.toml` to `private/salary/pay.toml` and fill in your own figures. Without it, the example values are used and a warning is printed.

Exports need [pandoc](https://pandoc.org) and [Typst](https://typst.app):
`winget install --id JohnMacFarlane.Pandoc -e` and `winget install --id Typst.Typst -e`.
The Word styles come from `templates/reference.docx` (regenerate with `tools/make_reference_docx.py`).
