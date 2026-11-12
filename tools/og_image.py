"""Render the link-preview image (cv/site_assets/og-image.png) in the homepage's trainer-card style.

Run: uv run python tools/og_image.py --site <local clone of jvitorcosta.github.io> --intro "<trainer card intro>"
Uses headless Chrome, so the pixel and body fonts come out exactly as on the site.
Keep --intro in step with `intro` in the site's data/strings.toml ([en]).
"""

import argparse
import html
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "cv" / "site_assets" / "og-image.png"
WINDOWS_CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


def og_html(site: Path, intro: str) -> str:
    """The 1200x630 page that becomes the image; colours are the Nu Purple palette with the oat card.

    A " · " in the intro becomes a line break, so the dot never starts a wrapped line.
    """
    base = site.resolve().as_uri()
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:P;src:url({base}/assets/fonts/press-start-2p-latin.woff2)}}
@font-face{{font-family:I;src:url({base}/assets/fonts/inter-latin.woff2);font-weight:100 900}}
html,body{{margin:0;width:1200px;height:630px;background:#820ad1;overflow:hidden}}
.card{{position:absolute;left:70px;top:70px;width:1060px;height:490px;box-sizing:border-box;background:#f7f0e1;
border:8px solid #2a0845;box-shadow:16px 16px 0 #4a0478;padding:64px 70px;display:flex;gap:60px;align-items:center;color:#2a0845}}
.ava{{width:288px;height:288px;flex:none;image-rendering:pixelated;background:#e9dcc2;border:6px solid #2a0845;padding:12px;box-sizing:border-box}}
.lv{{font:400 24px P;margin:0 0 20px;color:#820ad1}}
h1{{font:400 64px P;margin:0 0 30px;letter-spacing:2px}}
p{{font:500 36px/1.35 I;margin:0 0 34px;text-wrap:balance}}
.url{{font:400 22px P;color:#820ad1}}
</style></head><body><div class="card"><img class="ava" src="{base}/assets/avatar.png" alt=""><div>
<div class="lv">&#9654; TRAINER CARD</div><h1>VITOR</h1><p>{'<br>'.join(html.escape(part) for part in intro.split(' · '))}</p>
<div class="url">jvitorcosta.github.io</div></div></div></body></html>"""


def find_chrome(given: Path | None) -> Path:
    for candidate in (given, os.environ.get("CHROME"), WINDOWS_CHROME):
        if candidate and Path(candidate).exists():
            return Path(candidate)
    raise SystemExit("Chrome not found: pass --chrome or set CHROME")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--site", type=Path, required=True, help="local clone of jvitorcosta.github.io")
    parser.add_argument("--intro", required=True, help="the trainer card intro, in English")
    parser.add_argument("--chrome", type=Path, help="path to the Chrome executable")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "og.html"
        page.write_text(og_html(args.site, args.intro), encoding="utf-8")
        subprocess.run([str(find_chrome(args.chrome)), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--allow-file-access-from-files", "--window-size=1200,630",
                        f"--screenshot={args.out.resolve()}", page.as_uri()],
                       check=True, capture_output=True)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
