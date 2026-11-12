"""Build the public website into site/ (git-ignored) or straight into a clone of jvitorcosta.github.io.

Run: uv run python tools/build_site.py [--copy-to <local clone of jvitorcosta/jvitorcosta.github.io>]
Then commit and push in that clone (ask Vitor first: it publishes).
"""

import argparse
from pathlib import Path

from cv.site import build_site, load_public_profile

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--copy-to", type=Path, help="write the site into this folder instead of site/")
    args = parser.parse_args()
    out = args.copy_to or ROOT / "site"
    written = build_site(ROOT, load_public_profile(ROOT), out)
    print(f"Built {len(written)} files into {out}")


if __name__ == "__main__":
    main()
