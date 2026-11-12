from cv import cli


def test_new_writes_under_private(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    assert cli.main(["new", "Acme", "Engineer", "--date", "2026-01-01"]) == 0
    assert (tmp_path / "private" / "applications" / "2026-01-01-acme-engineer" / "meta.yaml").exists()
    assert not (tmp_path / "applications").exists()


def test_tracker_writes_under_private(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    cli.main(["new", "Acme", "Engineer", "--date", "2026-01-01"])
    assert cli.main(["tracker"]) == 0
    assert "Acme" in (tmp_path / "private" / "tracker.md").read_text(encoding="utf-8")
    assert not (tmp_path / "tracker.md").exists()


def test_tracker_on_fresh_clone_creates_private(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    assert cli.main(["tracker"]) == 0
    assert (tmp_path / "private" / "tracker.md").exists()


def test_build_without_profile_explains(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    cli.main(["new", "Acme", "Engineer", "--date", "2026-01-01"])
    assert cli.main(["build", str(tmp_path / "private" / "applications" / "2026-01-01-acme-engineer")]) == 1
    assert "profile.example.yaml" in capsys.readouterr().err


def test_build_reports_broken_front_matter(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    (tmp_path / "private").mkdir()
    (tmp_path / "private" / "profile.yaml").write_text("name: Vitor Pinheiro\nemail: you@example.com\n", encoding="utf-8")
    cli.main(["new", "Acme", "Engineer", "--date", "2026-01-01"])
    folder = tmp_path / "private" / "applications" / "2026-01-01-acme-engineer"
    (folder / "resume.md").write_text("---\nheadline: Engineer (ID: 3)\n---\nbody\n", encoding="utf-8")
    assert cli.main(["build", str(folder)]) == 1
    assert "resume.md" in capsys.readouterr().err


def test_root_is_repo_root_not_cwd(tmp_path, monkeypatch):
    import importlib
    from pathlib import Path
    monkeypatch.chdir(tmp_path)
    reloaded = importlib.reload(cli)
    assert reloaded.ROOT == Path(cli.__file__).resolve().parents[1]
