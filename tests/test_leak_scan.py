import importlib.util
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


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_scan_reports_locations_not_terms(tmp_path):
    write(tmp_path / "a.md", "fine line\nwe talked to Initech here\n")
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
    write(tmp_path / "private" / "profile.yaml", "name: X\nemail: x@example.com\nphone: '+55 92 91234-5678'\nlegal_name: Real Full Name\n")
    write(tmp_path / "b.md", "call 5592912345678 anytime\n")
    terms = leak_scan.private_terms(tmp_path)
    assert "Real Full Name" in terms
    assert leak_scan.scan(tmp_path, [tmp_path / "b.md"], terms, []) == ["b.md:1"]


def test_markers_only_apply_to_content_dirs(tmp_path):
    write(tmp_path / "main" / "c.md", "see private/notes\n")
    write(tmp_path / "cv" / "d.py", "ROOT / 'private'  # private/ folder\n")
    files = [tmp_path / "main" / "c.md", tmp_path / "cv" / "d.py"]
    assert leak_scan.scan(tmp_path, files, [], [r"private/"]) == ["main/c.md:1"]


def test_company_that_is_also_a_listed_tool_is_not_a_term(tmp_path):
    # Applying to a company whose product is on my public stack (say, Databricks) must not flag the stack.
    write(tmp_path / "private" / "tracker.md", TRACKER.replace("Initech", "Databricks"))
    write(tmp_path / "main" / "skills.md", "- **Data:** Spark, Databricks, Delta Lake\n")
    assert "Databricks" not in leak_scan.private_terms(tmp_path)


def test_example_profile_has_no_real_legal_name():
    text = (ROOT / "profile.example.yaml").read_text(encoding="utf-8")
    assert 'legal_name: "Your Full Legal Name"' in text


def test_company_named_on_the_published_resume_is_not_a_term(tmp_path):
    # A name already on the public resume or certificates (a client, a certificate issuer) leaks nothing.
    write(tmp_path / "private" / "tracker.md", TRACKER.replace("Initech", "Globex"))
    write(tmp_path / "resume" / "resume.md", "- Planned demand with Globex, the national supplier.\n")
    assert "Globex" not in leak_scan.private_terms(tmp_path)
