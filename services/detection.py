from models import DetectionResult
from services.groq_client import classify_text
from services.stylometrics import analyze_text


def run_pipeline(text: str) -> DetectionResult:
    """
    Runs both detection signals and returns a DetectionResult.
    If the Groq API is unavailable, llm_score is None and llm_available is False.
    """
    llm_score = classify_text(text)
    stylo_score = analyze_text(text)

    return DetectionResult(
        stylometric_score=stylo_score,
        llm_score=llm_score,
        llm_available=(llm_score is not None),
    )
