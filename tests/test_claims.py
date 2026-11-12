import shutil
from pathlib import Path

import pytest

from cv.claims import find_claims, is_checked, load_banned

ROOT = Path(__file__).parents[1]
BANNED = [(r"\bembeddings?\b", "x"), (r"\bvector[- ]db\b", "x"), (r"\bpytorch\b", "x"),
          (r"\brust\b", "x"), (r"\bOBD\b", "x")]


def test_flags_positive_claims():
    found = find_claims("Built RAG with embeddings and a vector DB.\nShipped PyTorch models.", BANNED)
    assert len(found) == 3
    assert found[0].startswith('line 1: "embeddings"')
    assert found[2].startswith('line 2: "PyTorch"')


def test_negations_pass():
    assert find_claims("No vector DB on record; I have not used Rust.", BANNED) == []
    assert find_claims("Bluetooth OBD link planned for the trip meter.", BANNED) == []


def test_word_boundaries():
    assert find_claims("Trusted by the team; chunked uploads.", BANNED) == []


def test_only_resumes_and_cover_letters_are_checked():
    assert is_checked("resume/resume.md")
    assert is_checked("private/applications/2026-11-01-acme-ml/resume.md")
    assert is_checked("private/applications/2026-11-01-acme-ml/cover-letter.md")
    assert not is_checked("private/applications/2026-11-01-acme-ml/answers.md")
    assert not is_checked("answers/unique-achievement.md")
    assert not is_checked("private/answers/unique-achievement.md")
    assert not is_checked("main/experience/nubank.md")


def test_load_banned_reads_private_file(tmp_path):
    (tmp_path / "private").mkdir()
    (tmp_path / "private" / "claims-banned.toml").write_text(
        "[[banned]]\npattern = '\\bfoo\\b'\nwhy = 'foo is not on record'\n", encoding="utf-8")
    assert load_banned(tmp_path) == [(r"\bfoo\b", "foo is not on record")]


def test_load_banned_falls_back_to_example(tmp_path):
    (tmp_path / "claims-banned.example.toml").write_text(
        "[[banned]]\npattern = '\\bblockchain\\b'\nwhy = 'example'\n", encoding="utf-8")
    assert load_banned(tmp_path) == [(r"\bblockchain\b", "example")]


def test_load_banned_reports_bad_file(tmp_path):
    (tmp_path / "private").mkdir()
    (tmp_path / "private" / "claims-banned.toml").write_text("[[banned]\nbroken", encoding="utf-8")
    with pytest.raises(ValueError, match="claims-banned.toml"):
        load_banned(tmp_path)


def test_shipped_example_list_loads(tmp_path):
    # A fresh clone has no private/ folder, so the example list in the repo is what it uses.
    shutil.copy(ROOT / "claims-banned.example.toml", tmp_path / "claims-banned.example.toml")
    example = load_banned(tmp_path)
    assert example and all(pattern and why for pattern, why in example)
