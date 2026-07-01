import uuid
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from models import ContentSubmission
from services.detection import run_pipeline
from services.confidence import score
from services.labels import generate_label
from services.audit import log_classification
from storage.store import save_submission

submit_bp = Blueprint("submit", __name__)


@submit_bp.route("/submit", methods=["POST"])
def submit():
    data = request.get_json(silent=True) or {}

    text = data.get("text", "").strip()
    creator_id = data.get("creator_id", "").strip()

    if not text:
        return jsonify({"error": "Missing required field: text"}), 400
    if not creator_id:
        return jsonify({"error": "Missing required field: creator_id"}), 400

    try:
        detection = run_pipeline(text)
        attribution, confidence = score(detection)
        label = generate_label(attribution, confidence)

        content_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        submission = ContentSubmission(
            content_id=content_id,
            creator_id=creator_id,
            text=text,
            timestamp=timestamp,
            attribution=attribution,
            confidence=confidence,
            llm_score=detection.llm_score,
            stylometric_score=detection.stylometric_score,
            label=label,
            status="classified",
            llm_available=detection.llm_available,
        )

        save_submission(submission)
        log_classification(submission)

        return jsonify({
            "content_id": content_id,
            "attribution": attribution,
            "confidence": confidence,
            "label": label,
            "signals": {
                "llm_score": detection.llm_score,
                "stylometric_score": detection.stylometric_score,
                "llm_available": detection.llm_available,
            },
            "status": "classified",
            "timestamp": timestamp,
        }), 200

    except Exception:
        return jsonify({"error": "Classification failed. Please try again."}), 500
