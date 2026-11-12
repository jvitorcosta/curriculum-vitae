import re
from pathlib import Path

from cv.site import build_site

ROOT = Path(__file__).parents[1]
PROFILE = {"name": "Vitor Pinheiro", "email": "you@example.com", "phone": "+00 00 00000-0000",
           "location": "Manaus, Brazil (UTC-4, remote)",
           "links": {"linkedin": "linkedin.com/in/jvpro", "github": "github.com/jvitorcosta"}}


def test_builds_one_page_per_case_study_and_no_index(tmp_path):
    build_site(ROOT, PROFILE, tmp_path)
    assert not (tmp_path / "index.html").exists()
    for slug in ["car-cyberdeck", "solvedor", "resume-as-code"]:
        page = (tmp_path / "projects" / f"{slug}.html").read_text(encoding="utf-8")
        assert "<h1>" in page and 'href="../index.html"' in page
        assert '<html lang="en" class="pal-nu">' in page
        assert "&larr; Vitor" in page
        assert 'data-palette="pocket"' not in page
        for pal, en, pt in [("night", "Red Lantern", "Lanterna Vermelha"), ("nu", "Nu Purple", "Roxo Nu")]:
            assert (f'<button type="button" data-palette="{pal}" aria-label="{en}" '
                    f'data-aria-en="{en}" data-aria-pt="{pt}">') in page
        assert '<div class="box">' in page
        assert '<script src="../assets/site.js" defer></script>' in page


def test_exports_public_jobs_json(tmp_path):
    import json
    build_site(ROOT, PROFILE, tmp_path)
    raw = (tmp_path / "data" / "jobs.json").read_text(encoding="utf-8")
    assert raw.endswith("\n")
    jobs = json.loads(raw)
    assert jobs and all(set(j) == {"title", "company", "start", "end"} for j in jobs)
    assert "phone" not in raw and "email" not in raw and "00000-0000" not in raw
    assert all(len(j["start"].split()) == 2 for j in jobs)  # "Feb 2026"


def test_case_pages_use_shared_stylesheet(tmp_path):
    build_site(ROOT, PROFILE, tmp_path)
    for f in (tmp_path / "projects").glob("*.html"):
        text = f.read_text(encoding="utf-8")
        if "http-equiv=\"refresh\"" in text:
            continue
        assert 'href="../assets/site.css"' in text
        assert "<style" not in text


def test_never_publishes_the_phone_number(tmp_path):
    build_site(ROOT, PROFILE, tmp_path)
    for f in tmp_path.rglob("*.html"):
        assert "00000-0000" not in f.read_text(encoding="utf-8")


def test_seo_files(tmp_path):
    build_site(ROOT, PROFILE, tmp_path)
    page = (tmp_path / "projects" / "car-cyberdeck.html").read_text(encoding="utf-8")
    assert '<meta name="description"' in page
    assert '<link rel="canonical" href="https://jvitorcosta.github.io/projects/car-cyberdeck.html">' in page
    sitemap = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    assert "<loc>https://jvitorcosta.github.io/</loc>" in sitemap
    assert "https://jvitorcosta.github.io/projects/car-cyberdeck.html" in sitemap
    assert "projects/cardeck.html" not in sitemap  # the old page only redirects
    assert (tmp_path / "robots.txt").exists()
    assert (tmp_path / ".nojekyll").exists()


def test_site_links_only_the_approved_resume_pdf(tmp_path):
    # Since 2026-11-12 the general resume PDF is public on the site (Vitor's call); the site repo hosts
    # the copy. Nothing else may leak: no other PDF or Word file, and never the phone number.
    build_site(ROOT, PROFILE, tmp_path)
    for f in tmp_path.rglob("*.html"):
        text = f.read_text(encoding="utf-8")
        pdfs = re.findall(r'href="([^"]*\.(?:pdf|docx))"', text)
        assert set(pdfs) <= {"/Vitor_Pinheiro_Resume.pdf"}, f.name
        assert PROFILE["phone"] not in text
    assert not list(tmp_path.rglob("*.pdf")) and not list(tmp_path.rglob("*.docx"))


def test_favicon_and_link_preview_image(tmp_path):
    build_site(ROOT, PROFILE, tmp_path)
    for page in [tmp_path / "projects" / "car-cyberdeck.html"]:
        text = page.read_text(encoding="utf-8")
        assert 'rel="icon"' in text
        assert 'property="og:image" content="https://jvitorcosta.github.io/og-image.png"' in text
        assert 'name="twitter:card" content="summary_large_image"' in text
    assert (tmp_path / "favicon.svg").exists() and (tmp_path / "og-image.png").exists()


def test_description_is_search_friendly(tmp_path):
    from cv.site import DESCRIPTION
    assert len(DESCRIPTION) <= 160
    assert "UTC-4" in DESCRIPTION and "remote" in DESCRIPTION


def test_pdf_button_leads_the_body_in_both_languages(tmp_path, monkeypatch):
    import shutil
    import cv.site as site
    root = tmp_path / "root"
    shutil.copytree(ROOT / "main" / "experience", root / "main" / "experience")
    (root / "case-studies").mkdir()
    (root / "case-studies" / "cv.md").write_text(
        "---\ntitle: CV\nsummary: s\npdf: /Vitor_Pinheiro_Resume.pdf\n---\n\nBody\n", encoding="utf-8")
    (root / "case-studies" / "cv.pt.md").write_text("---\ntitle: CV pt\n---\n\nCorpo\n", encoding="utf-8")
    (root / "case-studies" / "plain.md").write_text("---\ntitle: Plain\nsummary: s\n---\n\nBody\n", encoding="utf-8")
    monkeypatch.setattr(site, "ORDER", ["cv", "plain"])
    out = tmp_path / "out"
    build_site(root, PROFILE, out)
    page = (out / "projects" / "cv.html").read_text(encoding="utf-8")
    assert '<p><a class="btn" href="/Vitor_Pinheiro_Resume.pdf">Download my resume (PDF)</a></p>\n<p>Body</p>' in page
    assert '<p><a class="btn" href="/Vitor_Pinheiro_Resume.pdf">Baixar meu currículo (PDF)</a></p>\n<p>Corpo</p>' in page
    assert "(PDF)" not in (out / "projects" / "plain.html").read_text(encoding="utf-8")


def test_resume_case_study_offers_the_pdf():
    from cv.build import split_front_matter
    front, _ = split_front_matter((ROOT / "case-studies" / "resume-as-code.md").read_text(encoding="utf-8"))
    assert front["pdf"] == "/Vitor_Pinheiro_Resume.pdf"


def test_demo_link_rendered_when_present(tmp_path, monkeypatch):
    import shutil
    import cv.site as site
    root = tmp_path / "root"
    shutil.copytree(ROOT / "main" / "experience", root / "main" / "experience")
    (root / "case-studies").mkdir()
    (root / "case-studies" / "with-demo.md").write_text(
        "---\ntitle: With demo\nsummary: s\ndemo: https://example.streamlit.app\n---\n\nBody\n", encoding="utf-8")
    (root / "case-studies" / "no-demo.md").write_text(
        "---\ntitle: No demo\nsummary: s\n---\n\nBody\n", encoding="utf-8")
    monkeypatch.setattr(site, "ORDER", ["with-demo", "no-demo"])
    out = tmp_path / "out"
    build_site(root, PROFILE, out)
    with_demo = (out / "projects" / "with-demo.html").read_text(encoding="utf-8")
    assert 'href="https://example.streamlit.app"' in with_demo and "Try it live" in with_demo
    assert "Try it live" not in (out / "projects" / "no-demo.html").read_text(encoding="utf-8")


def _root_with_study(tmp_path, front: str, body: str = "Body\n", images: dict | None = None):
    import shutil
    root = tmp_path / "root"
    shutil.copytree(ROOT / "main" / "experience", root / "main" / "experience")
    (root / "case-studies").mkdir()
    (root / "case-studies" / "study.md").write_text(f"---\ntitle: Study\nsummary: s\n{front}---\n\n{body}",
                                                    encoding="utf-8")
    for rel, data in (images or {}).items():
        path = root / "case-studies" / "images" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return root


def test_case_study_images_are_published_next_to_the_pages(tmp_path, monkeypatch):
    import cv.site as site
    monkeypatch.setattr(site, "ORDER", ["study"])
    root = _root_with_study(tmp_path, "", "![The workspace](images/study/shot.png)\n",
                            {"study/shot.png": b"png-bytes"})
    out = tmp_path / "out"
    build_site(root, PROFILE, out)
    page = (out / "projects" / "study.html").read_text(encoding="utf-8")
    assert '<img alt="The workspace" src="images/study/shot.png"' in page
    assert (out / "projects" / "images" / "study" / "shot.png").read_bytes() == b"png-bytes"


def test_cover_image_shown_under_the_title(tmp_path, monkeypatch):
    import cv.site as site
    monkeypatch.setattr(site, "ORDER", ["study"])
    root = _root_with_study(tmp_path, "cover: images/study/cover.png\ncover_alt: The chart\n",
                            images={"study/cover.png": b"x"})
    out = tmp_path / "out"
    build_site(root, PROFILE, out)
    page = (out / "projects" / "study.html").read_text(encoding="utf-8")
    assert '<figure class="cover"><img src="images/study/cover.png" alt="The chart"' in page
    assert page.index("<h1>") < page.index('class="cover"') < page.index("Body")


def test_embed_loads_only_on_click(tmp_path, monkeypatch):
    import cv.site as site
    monkeypatch.setattr(site, "ORDER", ["study"])
    root = _root_with_study(tmp_path, "embed: https://example.streamlit.app/?embed=true\n")
    out = tmp_path / "out"
    build_site(root, PROFILE, out)
    page = (out / "projects" / "study.html").read_text(encoding="utf-8")
    assert 'data-src="https://example.streamlit.app/?embed=true"' in page
    assert "<iframe" not in page.split("<script")[0]  # no iframe until the button is clicked
    assert "Run it here" in page


def test_pages_without_embed_have_no_script(tmp_path):
    build_site(ROOT, PROFILE, tmp_path)
    page = (tmp_path / "projects" / "car-cyberdeck.html").read_text(encoding="utf-8")
    assert ".embed button" not in page  # the only inline script is the early palette/language one
    assert page.count("<script>") == 1 and page.index("<script>") < page.index("</head>")


def test_renamed_project_page_redirects_to_the_new_one(tmp_path):
    build_site(ROOT, PROFILE, tmp_path)
    old = (tmp_path / "projects" / "cardeck.html").read_text(encoding="utf-8")
    assert '<meta http-equiv="refresh" content="0; url=car-cyberdeck.html">' in old
    assert '<link rel="canonical" href="https://jvitorcosta.github.io/projects/car-cyberdeck.html">' in old
    assert '<meta name="robots" content="noindex">' in old


def test_case_pages_load_no_third_party_fonts(tmp_path):
    # Fonts are self-hosted by the site's shared stylesheet (../assets/site.css).
    build_site(ROOT, PROFILE, tmp_path)
    for page in tmp_path.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        assert "fonts.googleapis.com" not in html
        assert "fonts.gstatic.com" not in html


SLUGS = ["car-cyberdeck", "solvedor", "resume-as-code"]
TOGGLE = '<button type="button" data-lang-toggle aria-label="EN > PT, switch language">EN > PT</button>'


def _head_and_body(page: str) -> tuple[str, str]:
    head, body = page.split("</head>", 1)
    return head, body


def test_case_pages_have_english_and_portuguese(tmp_path):
    from cv.build import split_front_matter
    build_site(ROOT, PROFILE, tmp_path)
    for slug in SLUGS:
        en, _ = split_front_matter((ROOT / "case-studies" / f"{slug}.md").read_text(encoding="utf-8"))
        pt, _ = split_front_matter((ROOT / "case-studies" / f"{slug}.pt.md").read_text(encoding="utf-8"))
        page = (tmp_path / "projects" / f"{slug}.html").read_text(encoding="utf-8")
        _, body = _head_and_body(page)
        # Each language has a block above the shared app box and one below it.
        assert body.count('<div lang="en">') == 2 and body.count('<div lang="pt">') == 2
        en_block = body.split('<div lang="en">', 1)[1].split('<div lang="pt">', 1)[0]
        pt_block = body.split('<div lang="pt">', 1)[1].split('</div>', 1)[0]
        assert en["title"] in en_block and en["role"] in en_block
        assert pt["title"] in pt_block and pt["role"] in pt_block
        assert pt["title"] != en["title"]


def test_case_page_ui_strings_are_translated(tmp_path):
    build_site(ROOT, PROFILE, tmp_path)
    page = (tmp_path / "projects" / "solvedor.html").read_text(encoding="utf-8")
    pt_block = "".join(part.split("</div>", 1)[0] for part in page.split('<div lang="pt">')[1:])
    assert '<span lang="pt">Rodar aqui</span>' in page
    assert "Ver o código no GitHub" in pt_block and "View the code on GitHub" not in pt_block
    assert "Região viável" in pt_block  # translated cover alt text
    assert "&larr; Vitor" in page


def test_case_pages_have_the_language_toggle(tmp_path):
    build_site(ROOT, PROFILE, tmp_path)
    for slug in SLUGS:
        page = (tmp_path / "projects" / f"{slug}.html").read_text(encoding="utf-8")
        header = page.split('<header class="top">', 1)[1].split("</header>", 1)[0]
        assert TOGGLE in header


def test_early_script_sets_palette_and_language_before_the_stylesheet(tmp_path):
    build_site(ROOT, PROFILE, tmp_path)
    for slug in SLUGS:
        page = (tmp_path / "projects" / f"{slug}.html").read_text(encoding="utf-8")
        head, _ = _head_and_body(page)
        assert '<html lang="en" class="pal-nu">' in page  # no-JS default
        script = head.split("<script>", 1)[1].split("</script>", 1)[0]
        assert head.index("<script>") < head.index('rel="stylesheet"')
        assert "try{" in script and "catch(e){}" in script
        assert 'localStorage.getItem("palette")' in script
        assert 'localStorage.getItem("lang")' in script and ".lang=" in script
        # One URL per page: the head stays English.
        assert '<link rel="canonical" href="https://jvitorcosta.github.io/projects/' + slug + '.html">' in head
        assert 'lang="pt"' not in head


def test_page_without_translation_shows_english_in_any_language(tmp_path, monkeypatch):
    import cv.site as site
    monkeypatch.setattr(site, "ORDER", ["study"])
    root = _root_with_study(tmp_path, "embed: https://example.streamlit.app/?embed=true\n",
                            "English only body\n")
    out = tmp_path / "out"
    build_site(root, PROFILE, out)
    page = (out / "projects" / "study.html").read_text(encoding="utf-8")
    head, body = _head_and_body(page)
    # No lang attribute in the body, so site.css never hides the English text.
    assert "lang=" not in body
    assert "English only body" in body and "Run it here" in body
    assert "data-lang-toggle" not in body
    assert ".lang=" not in head  # <html lang> stays "en" for an English-only page


def test_portuguese_file_is_used_when_present(tmp_path, monkeypatch):
    import cv.site as site
    monkeypatch.setattr(site, "ORDER", ["study"])
    root = _root_with_study(tmp_path, "role: Side project, 2026\nlink: https://github.com/x/y\n",
                            "English body\n")
    (root / "case-studies" / "study.pt.md").write_text(
        "---\ntitle: Estudo\nsummary: r\nrole: Projeto pessoal, 2026\n---\n\nCorpo em português\n",
        encoding="utf-8")
    out = tmp_path / "out"
    build_site(root, PROFILE, out)
    page = (out / "projects" / "study.html").read_text(encoding="utf-8")
    pt_block = page.split('<div lang="pt">', 1)[1]
    assert "<h1>Estudo</h1>" in pt_block and "Projeto pessoal, 2026" in pt_block
    assert "Corpo em português" in pt_block
    assert 'href="https://github.com/x/y"' in pt_block  # links come from the English file
    assert "<title>Study | Vitor Pinheiro</title>" in page
    assert not (out / "projects" / "study.pt.html").exists()
    assert "study.pt" not in (out / "sitemap.xml").read_text(encoding="utf-8")


def test_portuguese_pages_never_publish_the_phone_or_google_fonts(tmp_path):
    build_site(ROOT, PROFILE, tmp_path)
    for slug in SLUGS:
        page = (tmp_path / "projects" / f"{slug}.html").read_text(encoding="utf-8")
        assert "00000-0000" not in page
        assert "fonts.googleapis.com" not in page and "fonts.gstatic.com" not in page



def test_bilingual_page_has_one_embed(tmp_path, monkeypatch):
    # One app box shared by both languages, so switching language never offers a second load.
    import cv.site as site
    monkeypatch.setattr(site, "ORDER", ["study"])
    root = _root_with_study(tmp_path, "embed: https://example.streamlit.app/?embed=true\n", "English body\n")
    (root / "case-studies" / "study.pt.md").write_text(
        "---\ntitle: Estudo\nsummary: r\n---\n\nCorpo em português\n", encoding="utf-8")
    out = tmp_path / "out"
    build_site(root, PROFILE, out)
    page = (out / "projects" / "study.html").read_text(encoding="utf-8")
    assert page.count('class="embed"') == 1
    assert '<span lang="en">Run it here</span><span lang="pt">Rodar aqui</span>' in page
    assert "English body" in page and "Corpo em português" in page


def test_case_page_stylesheet_is_versioned_when_the_site_css_is_there(tmp_path):
    # Without a version, phones keep an old site.css after a style change.
    import hashlib
    out = tmp_path / "out"
    (out / "assets").mkdir(parents=True)
    (out / "assets" / "site.css").write_text("body{}", encoding="utf-8")
    build_site(ROOT, PROFILE, out)
    page = (out / "projects" / "solvedor.html").read_text(encoding="utf-8")
    digest = hashlib.sha256(b"body{}").hexdigest()[:8]
    assert f'<link rel="stylesheet" href="../assets/site.css?v={digest}">' in page


def test_case_page_stylesheet_is_plain_without_the_site_css(tmp_path):
    build_site(ROOT, PROFILE, tmp_path)
    page = (tmp_path / "projects" / "solvedor.html").read_text(encoding="utf-8")
    assert '<link rel="stylesheet" href="../assets/site.css">' in page


def test_privacy_page_for_the_google_oauth_app(tmp_path):
    # The consent screen of my personal Google OAuth app links to /privacy.html.
    build_site(ROOT, PROFILE, tmp_path)
    page = (tmp_path / "privacy.html").read_text(encoding="utf-8")
    assert "<h1>Privacy</h1>" in page and "gws-cli" in page
    assert '<link rel="canonical" href="https://jvitorcosta.github.io/privacy.html">' in page
    assert "https://jvitorcosta.github.io/privacy.html" in (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    assert "mailto:you@example.com" in page


def test_privacy_page_links_resolve_from_the_site_root(tmp_path):
    # It sits next to index.html, not in projects/, so no "../" links.
    build_site(ROOT, PROFILE, tmp_path)
    page = (tmp_path / "privacy.html").read_text(encoding="utf-8")
    assert 'href="assets/site.css"' in page and 'src="assets/site.js"' in page
    assert '<a href="index.html">&larr; Vitor</a>' in page
    assert "../" not in page


def test_og_image_page_escapes_the_intro_and_uses_the_site_avatar(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("og_image", ROOT / "tools" / "og_image.py")
    og = importlib.util.module_from_spec(spec); spec.loader.exec_module(og)
    page = og.og_html(tmp_path, "Engineer <from> Manaus")
    assert "Engineer &lt;from&gt; Manaus" in page
    assert f"{tmp_path.resolve().as_uri()}/assets/avatar.png" in page
    assert "<p>Software engineer<br>Manaus, Brazil.</p>" in og.og_html(tmp_path, "Software engineer · Manaus, Brazil.")


def test_script_is_versioned_like_the_stylesheet(tmp_path):
    # Without a version, phones keep an old site.js after a change (a Spotify fix, say).
    import hashlib
    out = tmp_path / "site"
    (out / "assets").mkdir(parents=True)
    (out / "assets" / "site.css").write_text("body{}", encoding="utf-8")
    (out / "assets" / "site.js").write_text("var x;", encoding="utf-8")
    build_site(ROOT, PROFILE, out)
    digest = hashlib.sha256(b"var x;").hexdigest()[:8]
    case = (out / "projects" / "solvedor.html").read_text(encoding="utf-8")
    assert f'<script src="../assets/site.js?v={digest}" defer></script>' in case
    privacy = (out / "privacy.html").read_text(encoding="utf-8")
    assert f'<script src="assets/site.js?v={digest}" defer></script>' in privacy


def test_asset_version_ignores_line_endings(tmp_path):
    # This site is built on Windows (CRLF checkout), the homepage on GitHub (LF):
    # both must give the same ?v= for the same file, matching homepage.markup.content_version.
    import hashlib
    out = tmp_path / "site"
    (out / "assets").mkdir(parents=True)
    (out / "assets" / "site.css").write_bytes(b"a {}\r\nb {}\r\n")
    build_site(ROOT, PROFILE, out)
    page = (out / "projects" / "solvedor.html").read_text(encoding="utf-8")
    digest = hashlib.sha256(b"a {}\nb {}\n").hexdigest()[:8]
    assert f'href="../assets/site.css?v={digest}"' in page
