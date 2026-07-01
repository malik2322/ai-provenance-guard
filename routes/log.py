from flask import Blueprint, request, jsonify

from services.audit import get_log

log_bp = Blueprint("log", __name__)


@log_bp.route("/log", methods=["GET"])
def audit_log():
    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        limit = 50

    entries = get_log(limit=limit)
    return jsonify({"entries": entries, "count": len(entries)}), 200
