# curriculum-vitae

Vitor Pinheiro's career record and resume generator, kept as code. Markdown is the source; PDF/DOCX are what gets sent. Claude does the tailoring and writing in conversation; the `cv` CLI does the mechanical parts.

## Layout

This repo is public. Everything personal lives in `private/`, a separate private git repo nested in this folder and git-ignored here. A fresh clone has no `private/` and still builds: it falls back to `profile.example.yaml` and `claims-banned.example.toml`.

- `main/`: the full record Claude tailors from. `experience/<company>.md` (each accomplishment's Facts and approved Variants, with tags), `projects/`, `summaries.md`, `skills.md`, `education.md`, `certificates.md`, `languages.md`. Internal notes about these facts live in `private/notes/`, never here.
- `resume/`: the general resume (`resume.md` plus the built PDF/DOCX, no phone number). The PDF is public on the website: the site repo hosts a copy at its root (`Vitor_Pinheiro_Resume.pdf`). Rebuild with `uv run python tools/build_public_resume.py`, then copy the PDF there too (ask Vitor first: it publishes).
- `case-studies/<slug>.md`: public case studies for the website (Car Cyberdeck, SolvedOR, resume-as-code). Work projects stay off the site. The site lives at https://jvitorcosta.github.io (repo `jvitorcosta/jvitorcosta.github.io`); this repo writes only the case-study pages, `data/jobs.json`, sitemap and robots (`cv/site.py`). To update: `uv run python tools/build_site.py --copy-to <clone of jvitorcosta.github.io>`, then commit and push there (ask Vitor first: it publishes).
- `examples/sample-application/`: a made-up application showing `cv build` end to end.
- `tools/leak_scan.py`: run before every public commit; it reports file:line for anything private found in tracked files.

## Tailoring rules

- Every claim must trace to `main/`. Rewording, reordering and re-emphasis are fine. New metrics, tools, responsibilities, titles or dates are not.
- Markdown shape that renders well: each role as `### Company · Title` with a `Location · Start – End` line under it, then bullets. Lines that must stay separate (skill tiers, certificates) need a blank line between them or must be bullets, because single line breaks merge into one paragraph. A full resume from `main/` fits in 2 pages, so cut older or weaker bullets first.
- Keep standard section headings (SUMMARY, SKILLS, EXPERIENCE, PROJECTS, EDUCATION, CERTIFICATES, LANGUAGES), one column, no tables. Exports must stay ATS-readable.
- Language: English by default. For a Portuguese posting, translate from `main/`, set `lang: pt` in the front matter (headings switch automatically), and keep the same facts.

## Voice (cover letters and answers)

Plain and human, not "AI style": avoid colon- and dash-heavy constructions, polished punchlines and triplets. Use plain words over jargon. A casual aside is fine. Short paragraphs.

## Never store

Anything personal (phone, legal name, applications and their outcomes, salary, answers, internal notes) stays in `private/`, never in this repo. And never anywhere, not even in `private/`: CPF, RG, passport or other government ID numbers, bank details, passwords, photos of documents. When a form asks for these, Vitor fills them in himself and the folder notes "provided".

## Commits

Authored as `Vitor Pinheiro` with the GitHub noreply address (repo-local git config). Never add a `Co-Authored-By: Claude` trailer. Push to `jvitorcosta/curriculum-vitae` only when Vitor asks. Before any commit, run `uv run python tools/leak_scan.py`: nothing from `private/` and no applied-to company name may end up in a tracked file.

## Private workflow

The application workflow, answer bank, name rules and status sync live in the private repo, when present:

@private/CLAUDE.md
