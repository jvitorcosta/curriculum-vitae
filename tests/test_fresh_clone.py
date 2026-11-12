"""A fresh clone has no private/ folder and must still test and build, so anyone can try the repo."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from cv.build import build_outputs, pdf_text
from cv.claims import find_claims, load_banned
from cv.profile import load_profile

ROOT = Path(__file__).parents[1]
SAMPLE = ROOT / "examples" / "sample-application"
IN_CLONE = "CV_FRESH_CLONE_TEST" in os.environ


@pytest.mark.skipif(IN_CLONE, reason="already running inside the fresh clone")
def test_fresh_clone_runs(tmp_path):
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(ROOT), str(clone)], check=True)
    assert not (clone / "private").exists()
    env = {**os.environ, "CV_FRESH_CLONE_TEST": "1"}
    run = subprocess.run(["uv", "run", "--python", "3.12", "pytest", "-q", "-p", "no:cacheprovider"],
                         cwd=clone, env=env, capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-2000:]

    if not (shutil.which("pandoc") and shutil.which("typst")):
        pytest.skip("pandoc or Typst missing, so the build half is skipped")
    sample = clone / "examples" / "sample-application"
    outputs = build_outputs(sample, load_profile(clone), clone / "templates")
    pdf = next(p for p in outputs if p.suffix == ".pdf")
    assert "Example_Labs" in pdf.name
    assert "Machine learning engineer" in pdf_text(pdf)


def test_private_is_ignored():
    for path in ("private/anything", "private/.git/HEAD"):
        assert subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT).returncode == 0, path


def test_sample_application_passes_claims_check():
    for name in ("resume.md",):
        text = (SAMPLE / name).read_text(encoding="utf-8")
        assert find_claims(text, load_banned(ROOT)) == []
    assert "Example Labs" in (SAMPLE / "meta.yaml").read_text(encoding="utf-8")
