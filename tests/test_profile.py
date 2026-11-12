import pytest

from cv.profile import load_profile, public_profile

EXAMPLE = "name: Example Person\nemail: example@example.com\nphone: '+00 0000-0000'\n"
PRIVATE = "name: Real Person\nemail: real@example.com\nphone: '+11 1111-1111'\nlegal_name: Real Full Name\n"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_load_profile_prefers_private(tmp_path):
    write(tmp_path / "profile.example.yaml", EXAMPLE)
    write(tmp_path / "private" / "profile.yaml", PRIVATE)
    assert load_profile(tmp_path)["name"] == "Real Person"


def test_load_profile_without_private_profile(tmp_path):
    write(tmp_path / "profile.example.yaml", EXAMPLE)
    (tmp_path / "private").mkdir()
    assert load_profile(tmp_path)["name"] == "Example Person"


def test_public_profile_drops_phone_and_legal_name(tmp_path):
    write(tmp_path / "profile.example.yaml", EXAMPLE)
    write(tmp_path / "private" / "profile.yaml", PRIVATE)
    profile = public_profile(tmp_path)
    assert "phone" not in profile and "legal_name" not in profile
    assert profile["email"] == "real@example.com"


def test_load_profile_requires_name_and_email(tmp_path):
    write(tmp_path / "profile.example.yaml", "name: Only A Name\n")
    with pytest.raises(ValueError, match="email"):
        load_profile(tmp_path)


def test_load_profile_without_any_profile_explains(tmp_path):
    with pytest.raises(ValueError, match="profile.example.yaml"):
        load_profile(tmp_path)


def test_require_private_profile_refuses_the_example(tmp_path):
    import pytest
    from cv.profile import require_private_profile
    (tmp_path / "profile.example.yaml").write_text("name: X\nemail: you@example.com\n", encoding="utf-8")
    with pytest.raises(ValueError, match="profile.yaml"):
        require_private_profile(tmp_path)
