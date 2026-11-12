"""Build the public website (jvitorcosta.github.io) from the case studies and main/.

Only public-safe data goes in: name, email, links, headline, case studies, job titles and dates.
Never the phone number or anything from private/ beyond those profile fields.
"""

import hashlib
import html
import json
import shutil
from pathlib import Path

import markdown
import yaml

from cv.build import split_front_matter
from cv.profile import public_profile

SITE_URL = "https://jvitorcosta.github.io"
ASSETS = Path(__file__).parent / "site_assets"
ORDER = ["car-cyberdeck", "solvedor", "resume-as-code"]
# Old project page -> new one, so links shared before a rename keep working.
REDIRECTS = {"cardeck": "car-cyberdeck"}
DESCRIPTION = "Vitor Pinheiro, AI/ML engineer in Brazil (UTC-4): ML and LLM systems for fintech. Open to remote roles."
# key, English name, Portuguese name: the same labels as the homepage (homepage/render.py).
PALETTES = (("night", "Red Lantern", "Lanterna Vermelha"), ("nu", "Nu Purple", "Roxo Nu"))
LANGS = ("en", "pt")
# Same button as the homepage; site.js updates its text and label when the language changes.
LANG_TOGGLE = '<button type="button" data-lang-toggle aria-label="EN > PT, switch language">EN > PT</button>'
# Applies a remembered palette (and, on bilingual pages, the language) before the stylesheet paints,
# so neither flashes. Same rules as the homepage's EARLY_PALETTE and site.js: stored choice, else
# the browser language. site.js does the rest once it loads.
EARLY_PALETTE = ('try{var p=localStorage.getItem("palette");'
                 f'if(/^({"|".join(k for k, *_ in PALETTES)})$/.test(p)){{'
                 'var h=document.documentElement;h.className="pal-"+p;'
                 'h.setAttribute("data-pal",p)}}catch(e){}')
EARLY_LANG = ('try{var h=document.documentElement,l=(navigator.language||"").toLowerCase().indexOf("pt")?"en":"pt";'
              'try{var s=localStorage.getItem("lang");if(s=="en"||s=="pt")l=s}catch(e){}h.lang=l}catch(e){}')
# Hand-written UI text of the case pages, in both languages.
UI = {
    "en": {"run": "Run it here",
           "run_help": "Loads the live app on this page. If nobody has used it for a while, "
                       "it takes about 30 seconds to wake up.",
           "demo": "Try it live", "code": "View the code on GitHub",
           "pdf": "Download my resume (PDF)"},
    "pt": {"run": "Rodar aqui",
           "run_help": "Carrega o app ao vivo nesta página. Se ninguém usou ele faz um tempo, "
                       "ele leva uns 30 segundos pra acordar.",
           "demo": "Testar ao vivo", "code": "Ver o código no GitHub",
           "pdf": "Baixar meu currículo (PDF)"},
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# Markdown for privacy.html: the privacy link on the consent screen of my personal Google OAuth app.
PRIVACY = """\
This page covers **gws-cli**, a small Google OAuth app I use only on my own computer, with my own
Google account. It is not offered to anyone else.

- **What it accesses:** files it creates itself in my Google Drive (backups of my own documents)
  and my own Google Sheets.
- **What it stores:** its sign-in token stays on my computer, encrypted. Nothing is sent anywhere
  except Google's own APIs.
- **What it shares:** nothing. No data is collected, sold or shared with anyone.

This website itself has no cookies, analytics or tracking.
"""


def _aria(en: str, pt: str) -> str:
    return f'aria-label="{en}" data-aria-en="{en}" data-aria-pt="{pt}"'


def _header(bilingual: bool, up: str = "../") -> str:
    dots = "".join(f'<button type="button" data-palette="{key}" {_aria(en, pt)}></button>\n'
                   for key, en, pt in PALETTES)
    toggle = f"\n{LANG_TOGGLE}" if bilingual else ""
    return (f'<header class="top">\n<a href="{up}index.html">&larr; Vitor</a>\n'
            f'<span class="palettes" role="group" {_aria("Colours", "Cores")}>\n{dots}</span>{toggle}\n</header>')


def _asset_href(out: Path, name: str, up: str = "../") -> str:
    """Link to the site's assets/<name>, versioned by its content when it is there to hash.
    Line endings are normalized first, the same as the homepage's content_version(), so a
    Windows (CRLF) checkout gives the same version as the LF one GitHub builds from."""
    asset = out / "assets" / name
    if not asset.is_file():
        return f"{up}assets/{name}"
    data = asset.read_bytes().replace(b"\r\n", b"\n")
    return f"{up}assets/{name}?v={hashlib.sha256(data).hexdigest()[:8]}"


def _page(title: str, description: str, path: str, body: str, extra_head: str = "",
          bilingual: bool = False, css_href: str = "../assets/site.css", up: str = "../",
          js_href: str | None = None) -> str:
    """One page of the site. `up` is the way back to the site root: "../" from projects/, "" at the root."""
    url = f"{SITE_URL}/{path}" if path else f"{SITE_URL}/"
    early = EARLY_PALETTE + (EARLY_LANG if bilingual else "")
    return f"""<!doctype html>
<html lang="en" class="pal-nu">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:url" content="{url}">
<meta property="og:type" content="website">
<meta property="og:image" content="{SITE_URL}/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<script>{early}</script>
<link rel="stylesheet" href="{css_href}">
{extra_head}
</head>
<body>
{_header(bilingual, up)}
<main>
{body}
</main>
<script src="{js_href or f'{up}assets/site.js'}" defer></script>
</body>
</html>
"""


def _date(value) -> str:
    text = str(value)
    if len(text) >= 7 and text[4] == "-":
        return f"{MONTHS[int(text[5:7]) - 1]} {text[:4]}"
    return text


def _jobs(root: Path) -> list[dict]:
    jobs = []
    for f in (root / "main" / "experience").glob("*.md"):
        front, _ = split_front_matter(f.read_text(encoding="utf-8"))
        title = (front.get("titles") or [front.get("title", "")])[0]
        jobs.append({"company": front["company"], "title": title,
                     "start": str(front["start"]), "end": str(front["end"])})
    return sorted(jobs, key=lambda j: j["start"], reverse=True)


def _case_studies(root: Path) -> list[dict]:
    studies = []
    for slug in ORDER:
        front, body = split_front_matter((root / "case-studies" / f"{slug}.md").read_text(encoding="utf-8"))
        study = {"slug": slug, **front, "html": markdown.markdown(body), "pt": None}
        # <slug>.pt.md holds the translated text fields and body; links, images and embeds
        # come from the English file, so the two can't drift apart.
        pt_file = root / "case-studies" / f"{slug}.pt.md"
        if pt_file.exists():
            pt_front, pt_body = split_front_matter(pt_file.read_text(encoding="utf-8"))
            study["pt"] = {**front, **pt_front, "html": markdown.markdown(pt_body)}
        studies.append(study)
    return studies


# Loads the live app only when asked: a sleeping Streamlit app would otherwise greet every visitor.
EMBED_SCRIPT = """<script>
document.querySelectorAll(".embed button").forEach(b => b.addEventListener("click", () => {
  const box = b.closest(".embed"), frame = document.createElement("iframe");
  frame.src = box.dataset.src; frame.title = box.dataset.title;
  box.replaceChildren(frame);
}));
</script>"""


def _cover(s: dict) -> str:
    if not s.get("cover"):
        return ""
    return (f'<figure class="cover"><img src="{html.escape(s["cover"])}" '
            f'alt="{html.escape(s.get("cover_alt", ""))}"></figure>\n')


def _embed(s: dict, langs: list[str]) -> str:
    """The live-app box, once per page; with two languages its labels carry lang spans."""
    if not s.get("embed"):
        return ""

    def text(key: str) -> str:
        if len(langs) == 1:
            return html.escape(UI[langs[0]][key])
        return "".join(f'<span lang="{lang}">{html.escape(UI[lang][key])}</span>' for lang in langs)

    return (f'<div class="embed" data-src="{html.escape(s["embed"])}" data-title="{html.escape(s["title"])}">'
            f'<button type="button" class="btn">{text("run")}</button>'
            f'<small>{text("run_help")}</small></div>\n')


def _top(s: dict) -> str:
    """One language's title, meta line and cover: everything above the live app."""
    return f'<h1>{html.escape(s["title"])}</h1>\n<p class="meta">{html.escape(s.get("role", ""))}</p>\n{_cover(s)}'


def _rest(s: dict, lang: str) -> str:
    """One language's body and links: everything below the live app."""
    ui = UI[lang]
    link = f'<p><a href="{html.escape(s["link"])}">{html.escape(ui["code"])}</a></p>' if s.get("link") else ""
    if s.get("demo"):
        link = f'<p><a class="btn" href="{html.escape(s["demo"])}">{html.escape(ui["demo"])}</a></p>\n' + link
    # A downloadable file (the resume PDF) leads the body, so readers don't scroll to find it.
    pdf = f'<p><a class="btn" href="{html.escape(s["pdf"])}">{html.escape(ui["pdf"])}</a></p>\n' if s.get("pdf") else ""
    return f'{pdf}{s["html"]}\n{link}\n'


def build_site(root: Path, profile: dict, out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    (out / "projects").mkdir(exist_ok=True)
    studies = _case_studies(root)
    written: list[Path] = []

    for s in studies:
        bilingual = s["pt"] is not None
        if bilingual:
            # site.css shows only the blocks matching <html lang>; the live app box is shared.
            texts = {"en": s, "pt": s["pt"]}
            content = ("".join(f'<div lang="{lang}">\n{_top(texts[lang])}</div>\n' for lang in LANGS)
                       + _embed(s, LANGS)
                       + "".join(f'<div lang="{lang}">\n{_rest(texts[lang], lang)}</div>\n' for lang in LANGS))
        else:
            # No translation: no lang attribute, so the English stays visible in either language.
            content = _top(s) + _embed(s, ["en"]) + _rest(s, "en")
        body = f'<div class="box">\n<article>\n{content}</article>\n</div>'
        if s.get("embed"):
            body += "\n" + EMBED_SCRIPT
        path = out / "projects" / f"{s['slug']}.html"
        # Title, description, canonical and og tags stay English: one URL per page.
        path.write_text(_page(f"{s['title']} | {profile['name']}", s.get("summary", DESCRIPTION),
                              f"projects/{s['slug']}.html", body, bilingual=bilingual,
                              css_href=_asset_href(out, "site.css"),
                              js_href=_asset_href(out, "site.js")), encoding="utf-8")
        written.append(path)

    for old, new in REDIRECTS.items():
        target = f"{SITE_URL}/projects/{new}.html"
        path = out / "projects" / f"{old}.html"
        path.write_text(
            '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f'<meta http-equiv="refresh" content="0; url={new}.html">\n'
            f'<link rel="canonical" href="{target}">\n'
            '<meta name="robots" content="noindex">\n'
            f'<title>Moved</title>\n</head>\n<body><p>Moved to <a href="{new}.html">{new}</a>.</p></body>\n</html>\n',
            encoding="utf-8")
        written.append(path)

    data = out / "data"
    data.mkdir(exist_ok=True)
    jobs_json = data / "jobs.json"
    public_jobs = [{"title": j["title"], "company": j["company"], "start": _date(j["start"]), "end": _date(j["end"])}
                   for j in _jobs(root)]
    jobs_json.write_text(json.dumps(public_jobs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    written.append(jobs_json)

    privacy = out / "privacy.html"
    email = html.escape(profile.get("email", ""))
    body = (f'<div class="box">\n<article>\n<h1>Privacy</h1>\n{markdown.markdown(PRIVACY)}\n'
            f'<p class="meta">Questions: <a href="mailto:{email}">{email}</a></p>\n</article>\n</div>')
    privacy.write_text(_page(f"Privacy | {profile['name']}", "Privacy policy for my personal Google OAuth app.",
                             "privacy.html", body, css_href=_asset_href(out, "site.css", ""),
                             js_href=_asset_href(out, "site.js", ""), up=""), encoding="utf-8")
    written.append(privacy)

    urls = ([f"{SITE_URL}/"] + [f"{SITE_URL}/projects/{s['slug']}.html" for s in studies]
            + [f"{SITE_URL}/privacy.html"])
    sitemap = out / "sitemap.xml"
    sitemap.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                       + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    robots = out / "robots.txt"
    robots.write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    images = root / "case-studies" / "images"
    if images.is_dir():
        shutil.copytree(images, out / "projects" / "images", dirs_exist_ok=True)
        written += [p for p in (out / "projects" / "images").rglob("*") if p.is_file()]
    for asset in ("favicon.svg", "og-image.png"):
        shutil.copy(ASSETS / asset, out / asset)
        written.append(out / asset)
    written += [sitemap, robots]
    return written


def load_public_profile(root: Path) -> dict:
    return public_profile(root)
