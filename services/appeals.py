import uuid
from datetime import datetime, timezone

from models import AppealRecord, ContentSubmission
from storage import store
from services import audit


class ContentNotFoundError(Exception):
    pass


def submit_appeal(content_id: str, creator_reasoning: str) -> tuple[AppealRecord, ContentSubmission]:
    """
    Validates that content_id exists, updates its status to under_review,
    logs the appeal, and returns (AppealRecord, updated ContentSubmission).
    Raises ContentNotFoundError if content_id is unknown.
    """
    submission = store.get_submission(content_id)
    if submission is None:
        raise ContentNotFoundError(content_id)

    appeal = AppealRecord(
        appeal_id=str(uuid.uuid4()),
        content_id=content_id,
        creator_reasoning=creator_reasoning,
        timestamp=datetime.now(timezone.utc).isoformat(),
        original_attribution=submission.attribution,
        original_confidence=submission.confidence,
    )

    store.update_submission_status(content_id, "under_review")
    submission.status = "under_review"

    audit.log_appeal(submission, appeal)

    return appeal, submission
