import json
import os
from dataclasses import asdict
from typing import Optional

import config
from models import ContentSubmission


def _ensure_data_dir() -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)


def _load_all() -> dict:
    _ensure_data_dir()
    if not os.path.exists(config.SUBMISSIONS_FILE):
        return {}
    with open(config.SUBMISSIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_all(data: dict) -> None:
    _ensure_data_dir()
    with open(config.SUBMISSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def save_submission(submission: ContentSubmission) -> None:
    data = _load_all()
    data[submission.content_id] = asdict(submission)
    _save_all(data)


def get_submission(content_id: str) -> Optional[ContentSubmission]:
    data = _load_all()
    raw = data.get(content_id)
    if raw is None:
        return None
    return ContentSubmission(**raw)


def update_submission_status(content_id: str, status: str) -> bool:
    """Returns False if content_id does not exist."""
    data = _load_all()
    if content_id not in data:
        return False
    data[content_id]["status"] = status
    _save_all(data)
    return True
