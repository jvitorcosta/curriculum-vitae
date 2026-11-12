"""ASCII-safe names for folders and export files."""

import re
import unicodedata

MAX_SLUG = 40


def _ascii(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text)
    return "".join(c for c in folded if not unicodedata.combining(c)).encode("ascii", "ignore").decode()


def slugify(text: str, fallback: str = "company") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", _ascii(text).lower()).strip("-")
    if len(slug) > MAX_SLUG:
        cut = slug[: MAX_SLUG + 1]
        slug = cut[: cut.rfind("-")] if "-" in cut else slug[:MAX_SLUG]
    return slug or fallback


def filename_part(text: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", _ascii(text))
    return "_".join(words) or "Company"
