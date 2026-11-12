import importlib.util
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("leak_scan", ROOT / "tools" / "leak_scan.py")
leak_scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(leak_scan)

TRACKER = """# Applications

2 applications — applied: 2

| Date | Company | Role | Channel | Status | Folder |
|---|---|---|---|---|---|
| 2026-10-01 | Initech | ML Engineer | linkedin | applied | [x](applications/x/) |
| 2026-10-02 | Nubank | Engineer | direct | applied | [y](applications/y/) |
"""
NL = "\n"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_scan_reports_locations_not_terms(tmp_path):
    write(tmp_path / "a.md", "fine line" + NL + "we talked to Initech here" + NL)
    hits = leak_scan.scan(tmp_path, [tmp_path / "a.md"], ["Initech"], [])
    assert hits == ["a.md:2"]
    assert "Initech" not in " ".join(hits)


def test_private_terms_reads_tracker_companies(tmp_path):
    write(tmp_path / "private" / "tracker.md", TRACKER)
    terms = leak_scan.private_terms(tmp_path)
    assert "Initech" in terms
    assert "Nubank" not in terms  # a public employer, so it may appear


def test_private_terms_empty_without_private(tmp_path):
    assert leak_scan.private_terms(tmp_path) == []


def test_phone_matches_with_other_formatting(tmp_path):
    write(tmp_path / "private" / "profile.yaml",
          NL.join(["name: X", "email: x@example.com", "phone: '+55 92 91234-5678'", "legal_name: Real Full Name", ""]))
    write(tmp_path / "b.md", "call 5592912345678 anytime" + NL)
    terms = leak_scan.private_terms(tmp_path)
    assert "Real Full Name" in terms
    assert leak_scan.scan(tmp_path, [tmp_path / "b.md"], terms, []) == ["b.md:1"]


def test_markers_only_apply_to_content_dirs(tmp_path):
    write(tmp_path / "main" / "c.md", "see private/notes" + NL)
    write(tmp_path / "cv" / "d.py", "ROOT / 'private'  # private/ folder" + NL)
    files = [tmp_path / "main" / "c.md", tmp_path / "cv" / "d.py"]
    assert leak_scan.scan(tmp_path, files, [], [r"private/"]) == ["main/c.md:1"]


def test_allowlisted_company_is_not_a_term(tmp_path):
    # A company that is also a public name (a product on my stack, a client) is allowed only by
    # listing it in private/leak-scan-allow.txt, never because it already shows up in a scanned file.
    write(tmp_path / "private" / "tracker.md", TRACKER.replace("Initech", "Databricks"))
    write(tmp_path / "private" / "leak-scan-allow.txt", "# public names" + NL + "databricks" + NL)
    assert "Databricks" not in leak_scan.private_terms(tmp_path)


def test_company_in_the_resume_is_still_a_term(tmp_path):
    write(tmp_path / "private" / "tracker.md", TRACKER)
    write(tmp_path / "resume" / "resume.md", "- Worked with Initech." + NL)
    assert "Initech" in leak_scan.private_terms(tmp_path)


def test_companies_come_from_application_folders_too(tmp_path):
    write(tmp_path / "private" / "applications" / "2026-11-01-globex-ml" / "meta.yaml",
          NL.join(["company: Globex", "role: ML", "date: '2026-11-01'", "status: draft", ""]))
    assert "Globex" in leak_scan.private_terms(tmp_path)


def test_phone_matches_without_country_code(tmp_path):
    write(tmp_path / "b.md", "call (92) 91234-5678" + NL)
    assert leak_scan.scan(tmp_path, [tmp_path / "b.md"], ["+55 92 91234-5678"], []) == ["b.md:1"]


def test_names_match_without_accents(tmp_path):
    write(tmp_path / "b.md", "Signed, Joao  Silva Souza" + NL)
    assert leak_scan.scan(tmp_path, [tmp_path / "b.md"], ["João Silva Souza"], []) == ["b.md:1"]


def test_untracked_files_are_scanned_by_default(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    write(tmp_path / "new.md", "x" + NL)
    write(tmp_path / ".gitignore", "private/" + NL)
    write(tmp_path / "private" / "p.md", "x" + NL)
    names = {p.name for p in leak_scan.public_files(tmp_path, untracked_too=False)}
    assert "new.md" in names and "p.md" not in names


def test_docx_text_is_scanned(tmp_path):
    with zipfile.ZipFile(tmp_path / "r.docx", "w") as z:
        z.writestr("word/document.xml", "<w:t>Call 5592912345678</w:t>")
    assert leak_scan.scan(tmp_path, [tmp_path / "r.docx"], ["+55 92 91234-5678"], []) == ["r.docx"]


def test_no_private_terms_is_not_reported_as_clean(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(leak_scan, "ROOT", tmp_path)
    monkeypatch.setattr(leak_scan, "public_files", lambda root, untracked_too: [])
    monkeypatch.setattr("sys.argv", ["leak_scan"])
    assert leak_scan.main() == 0
    assert "no private terms" in capsys.readouterr().out


def test_example_profile_has_no_real_legal_name():
    text = (ROOT / "profile.example.yaml").read_text(encoding="utf-8")
    assert 'legal_name: "Your Full Legal Name"' in text
