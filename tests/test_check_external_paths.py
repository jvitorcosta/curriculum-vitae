import importlib.util
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("check_external_paths", ROOT / "tools" / "check_external_paths.py")
cep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cep)


def test_paths_are_cut_at_the_first_placeholder():
    text = "Write to `D:\\dev\\projects\\curriculum-vitae\\private\\applications\\<folder>\\job.md`, then curriculum-vitae/main/skills.md."
    assert cep.repo_paths(text) == ["private/applications", "main/skills.md"]


def test_missing_paths_are_reported_with_their_skill(tmp_path):
    (tmp_path / "repo" / "main").mkdir(parents=True)
    skill = tmp_path / "skills" / "demo" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("Read curriculum-vitae/main/ and curriculum-vitae/answers/topic.md.\n", encoding="utf-8")
    assert cep.missing(tmp_path / "repo", [skill]) == [f"{skill}: answers/topic.md"]
