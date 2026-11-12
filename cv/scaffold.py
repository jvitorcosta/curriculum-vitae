"""Create a new application folder."""

from pathlib import Path

import yaml

from cv.meta import AppMeta, save_meta
from cv.slug import slugify


def new_application(root: Path, company: str, role: str, date: str, channel: str = "", url: str = "") -> Path:
    folder = root / "applications" / f"{date}-{slugify(company)}-{slugify(role, fallback='role')}"
    folder.mkdir(parents=True, exist_ok=False)
    job = f"# {role} at {company}\n\n"
    if url:
        job += f"URL: {url}\n\n"
    (folder / "job.md").write_text(job, encoding="utf-8")
    front = yaml.safe_dump({"headline": role, "lang": "en"}, allow_unicode=True, sort_keys=False)
    (folder / "resume.md").write_text(f"---\n{front}---\n\n", encoding="utf-8")
    (folder / "cover-letter.md").write_text("", encoding="utf-8")
    (folder / "answers.md").write_text("", encoding="utf-8")
    meta = AppMeta(company=company, role=role, date=date, channel=channel, url=url,
                   history=[{"status": "draft", "date": date}])
    save_meta(folder / "meta.yaml", meta)
    return folder
