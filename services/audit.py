import json
import os
import uuid
from datetime import datetime, timezone
from dataclasses import asdict

import config
from models import ContentSubmission, AppealRecord, AuditLogEntry


def _ensure_data_dir() -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)


def _load_log() -> list:
    _ensure_data_dir()
    if not os.path.exists(config.AUDIT_LOG_FILE):
        return []
    with open(config.AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _append_entry(entry: AuditLogEntry) -> None:
    entries = _load_log()
    entries.append(asdict(entry))
    _ensure_data_dir()
    with open(config.AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def log_classification(submission: ContentSubmission) -> None:
    entry = AuditLogEntry(
        entry_id=str(uuid.uuid4()),
        event_type="classification",
        content_id=submission.content_id,
        creator_id=submission.creator_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        attribution=submission.attribution,
        confidence=submission.confidence,
        llm_score=submission.llm_score,
        stylometric_score=submission.stylometric_score,
        label=submission.label,
        status=submission.status,
        llm_available=submission.llm_available,
        appeal_reasoning=None,
    )
    _append_entry(entry)


def log_appeal(submission: ContentSubmission, appeal: AppealRecord) -> None:
    entry = AuditLogEntry(
        entry_id=str(uuid.uuid4()),
        event_type="appeal",
        content_id=submission.content_id,
        creator_id=submission.creator_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        attribution=submission.attribution,
        confidence=submission.confidence,
        llm_score=submission.llm_score,
        stylometric_score=submission.stylometric_score,
        label=submission.label,
        status="under_review",
        llm_available=submission.llm_available,
        appeal_reasoning=appeal.creator_reasoning,
    )
    _append_entry(entry)


def get_log(limit: int = 50) -> list[dict]:
    entries = _load_log()
    return list(reversed(entries))[:limit]
