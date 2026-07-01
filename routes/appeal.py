from flask import Blueprint, request, jsonify

from services.appeals import submit_appeal, ContentNotFoundError

appeal_bp = Blueprint("appeal", __name__)


@appeal_bp.route("/appeal", methods=["POST"])
def appeal():
    data = request.get_json(silent=True) or {}

    content_id = data.get("content_id", "").strip()
    creator_reasoning = data.get("creator_reasoning", "").strip()

    if not content_id:
        return jsonify({"error": "Missing required field: content_id"}), 400
    if not creator_reasoning:
        return jsonify({"error": "Missing required field: creator_reasoning"}), 400

    try:
        appeal_record, submission = submit_appeal(content_id, creator_reasoning)
        return jsonify({
            "appeal_id": appeal_record.appeal_id,
            "content_id": content_id,
            "status": "under_review",
            "original_attribution": appeal_record.original_attribution,
            "message": (
                "Your appeal has been received and the content is now under review. "
                "A human reviewer will assess your submission alongside your reasoning."
            ),
        }), 200

    except ContentNotFoundError:
        return jsonify({"error": "Content ID not found."}), 404
    except Exception:
        return jsonify({"error": "Appeal submission failed. Please try again."}), 500
