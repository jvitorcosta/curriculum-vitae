"""Per-application metadata stored in meta.yaml."""

from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

STATUSES = ("draft", "applied", "screening", "interview", "offer", "rejected", "withdrawn", "ghosted")
REQUIRED = ("company", "role", "date", "status")


class MetaError(Exception):
    def __init__(self, path: Path, reason: str):
        super().__init__(f"{path}: {reason}")
        self.path = path
        self.reason = reason


@dataclass
class AppMeta:
    company: str
    role: str
    date: str
    channel: str = ""
    url: str = ""
    status: str = "draft"
    history: list[dict] = field(default_factory=list)
    notes: str = ""


def load_meta(path: Path) -> AppMeta:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        raise MetaError(path, f"unreadable ({e})") from e
    if not isinstance(data, dict):
        raise MetaError(path, "not a YAML mapping")
    missing = [k for k in REQUIRED if not data.get(k)]
    if missing:
        raise MetaError(path, "missing " + ", ".join(missing))
    if data["status"] not in STATUSES:
        raise MetaError(path, f"unknown status '{data['status']}'")
    data["history"] = [{**h, "date": str(h.get("date", ""))} for h in (data.get("history") or []) if isinstance(h, dict)]
    known = AppMeta.__dataclass_fields__
    text_fields = {"company", "role", "date", "channel", "url", "status", "notes"}
    return AppMeta(**{k: (str(v) if k in text_fields else v) for k, v in data.items() if k in known})


def save_meta(path: Path, meta: AppMeta) -> None:
    path.write_text(yaml.safe_dump(asdict(meta), sort_keys=False, allow_unicode=True), encoding="utf-8")


def set_status(meta: AppMeta, status: str, date: str, note: str = "") -> AppMeta:
    if status not in STATUSES:
        raise ValueError(f"unknown status '{status}', expected one of: {', '.join(STATUSES)}")
    meta.status = status
    entry = {"status": status, "date": date}
    if note:
        entry["note"] = note
    meta.history.append(entry)
    return meta
