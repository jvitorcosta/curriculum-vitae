import re
from pathlib import Path

from cv.markers import INTERNAL_MARKERS

ROOT = Path(__file__).parents[1]


def test_main_has_no_internal_notes():
    hits = []
    for path in sorted((ROOT / "main").rglob("*.md")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if any(re.search(m, line, re.IGNORECASE) for m in INTERNAL_MARKERS):
                hits.append(f"{path.relative_to(ROOT).as_posix()}:{number}")
    assert not hits, "internal notes in main/ (move them to private/notes/): " + ", ".join(hits)
