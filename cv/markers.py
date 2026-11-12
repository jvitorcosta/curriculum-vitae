"""Patterns that mark internal notes: they belong in private/notes/, never in the public record."""

INTERNAL_MARKERS = [
    r"\(Vitor, 20\d\d",
    r"decided 20\d\d",
    r"\bCONFLICTS\b",
    r"\bunverified\b",
    r"overlapping",
    r"\b(do not|don't) (claim|cite)\b",
    r"private/",
]
# Folders whose files are published content (as opposed to code and docs, which may name private/).
CONTENT_DIRS = ("main", "case-studies", "resume")
