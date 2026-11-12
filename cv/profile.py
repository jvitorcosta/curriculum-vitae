"""The contact profile for export headers: private/profile.yaml, else the public example.

A fresh clone has no private/ folder, so it builds with profile.example.yaml.
"""

from pathlib import Path

import yaml

REQUIRED = ("name", "email")
PRIVATE_FIELDS = ("phone", "legal_name")


def load_profile(root: Path) -> dict:
    """The full profile, phone included: only for application exports Vitor sends himself."""
    path = root / "private" / "profile.yaml"
    if not path.exists():
        path = root / "profile.example.yaml"
    if not path.exists():
        raise ValueError(f"No {root / 'private' / 'profile.yaml'}. Copy profile.example.yaml there and fill it in.")
    profile = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    missing = [key for key in REQUIRED if not profile.get(key)]
    if missing:
        raise ValueError(f"{path} is missing: {', '.join(missing)}")
    return profile


def require_private_profile(root: Path) -> dict:
    """The full profile, refusing the example: for builds that overwrite tracked, published files."""
    if not (root / "private" / "profile.yaml").exists():
        raise ValueError(f"No {root / 'private' / 'profile.yaml'}: the public resume would be rebuilt with "
                         "the example contact details. Run this only in a checkout that has private/.")
    return load_profile(root)


def public_profile(root: Path) -> dict:
    """The profile without phone and legal name, for anything published."""
    profile = load_profile(root)
    for key in PRIVATE_FIELDS:
        profile.pop(key, None)
    return profile
