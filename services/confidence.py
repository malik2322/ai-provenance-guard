import config
from models import DetectionResult


def score(result: DetectionResult) -> tuple[str, float]:
    """
    Combines signal scores into (attribution, confidence).

    attribution: "likely_ai" | "likely_human" | "uncertain"
    confidence:  0-1 float representing strength of the determination

    Falls back to stylometrics-only if LLM was unavailable.
    """
    if result.llm_available and result.llm_score is not None:
        combined = (config.LLM_WEIGHT * result.llm_score
                    + config.STYLO_WEIGHT * result.stylometric_score)
    else:
        combined = result.stylometric_score

    combined = round(combined, 4)

    if combined > config.AI_THRESHOLD:
        attribution = "likely_ai"
        confidence = combined
    elif combined < config.HUMAN_THRESHOLD:
        attribution = "likely_human"
        confidence = 1.0 - combined
    else:
        attribution = "uncertain"
        # Reflect how far from the centre of the uncertain zone the score sits.
        # 0.525 is the midpoint of [0.35, 0.70].
        confidence = 0.5 + abs(combined - 0.525)

    return attribution, round(confidence, 4)
