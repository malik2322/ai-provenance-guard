import config
from flask import Flask, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from routes.submit import submit_bp
from routes.appeal import appeal_bp
from routes.log import log_bp

if not config.GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

# Apply rate limiting to the submit blueprint
limiter.limit(f"{config.RATE_LIMIT_MINUTE};{config.RATE_LIMIT_DAY}")(
    submit_bp
)

app.register_blueprint(submit_bp)
app.register_blueprint(appeal_bp)
app.register_blueprint(log_bp)


@app.errorhandler(429)
def rate_limit_exceeded(e):
    return jsonify({"error": "Rate limit exceeded. Try again later.", "retry_after": str(e.description)}), 429


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found."}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed."}), 405


if __name__ == "__main__":
    app.run(debug=True)
