def generate_label(attribution: str, confidence: float) -> str:
    """
    Maps attribution + confidence to one of three verbatim transparency label variants.
    {pct} is replaced with round(confidence * 100).
    """
    pct = round(confidence * 100)

    if attribution == "likely_ai":
        return (
            f"This content was likely generated with AI assistance. "
            f"Our analysis detected patterns consistent with AI-generated writing "
            f"with {pct}% confidence. If you are the creator and believe this is "
            f"incorrect, you can submit an appeal for human review."
        )

    if attribution == "likely_human":
        return (
            f"This content appears to be human-written. Our analysis found natural "
            f"variation in writing style consistent with human authorship, with {pct}% "
            f"confidence. No attribution concern has been flagged."
        )

    # uncertain
    return (
        f"Our system could not confidently determine whether this content is "
        f"human-written or AI-generated ({pct}% confidence). The content has not "
        f"been flagged. If you are the creator and have concerns, you may submit "
        f"an appeal for human review."
    )
