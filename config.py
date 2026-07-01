import os
from dotenv import load_dotenv

load_dotenv()

# --- Groq ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"

# --- Detection signal weights ---
LLM_WEIGHT = 0.6
STYLO_WEIGHT = 0.4

# --- Attribution thresholds ---
# Asymmetric: wider uncertain zone gives human creators benefit of the doubt.
AI_THRESHOLD = 0.70      # combined_score > this → likely_ai
HUMAN_THRESHOLD = 0.35   # combined_score < this → likely_human
# 0.35–0.70 → uncertain

# --- Rate limiting ---
RATE_LIMIT_MINUTE = "10 per minute"
RATE_LIMIT_DAY = "100 per day"

# --- Storage paths ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SUBMISSIONS_FILE = os.path.join(DATA_DIR, "submissions.json")
AUDIT_LOG_FILE = os.path.join(DATA_DIR, "audit_log.json")
