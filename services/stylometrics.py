import re
import math
from typing import Optional


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s.strip()]


def _sentence_length_cv(sentences: list[str]) -> float:
    """
    Coefficient of variation of sentence word counts.
    Low variance → uniform → AI-like → high score.
    Returns 0.5 if only one sentence (undefined CV).
    """
    if len(sentences) < 2:
        return 0.5

    lengths = [len(s.split()) for s in sentences]
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return 0.5

    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    std = math.sqrt(variance)
    cv = std / mean

    # cv near 0 → uniform (AI-like) → score near 1
    # cv near 1+ → variable (human-like) → score near 0
    return max(0.0, 1.0 - min(cv, 1.0))


def _type_token_ratio(words: list[str]) -> float:
    """
    Unique words / total words. Low diversity → AI-like → high score.
    Returns 0.5 for empty or very short text.
    """
    if len(words) < 5:
        return 0.5

    ttr = len(set(w.lower() for w in words)) / len(words)
    # ttr near 1 → diverse (human-like) → score near 0
    # ttr near 0 → repetitive (AI-like) → score near 1
    return 1.0 - ttr


def _avg_word_length_score(words: list[str]) -> float:
    """
    Average character length of words.
    AI text favours longer, more formal vocabulary.
    Human informal writing uses shorter, everyday words.
    Returns 0.5 for empty input.
    """
    if not words:
        return 0.5

    avg_len = sum(len(w) for w in words) / len(words)

    # avg < 4.0 → casual vocabulary → human-like → low AI score
    # avg > 6.0 → formal vocabulary → AI-like → high AI score
    if avg_len < 4.0:
        return 0.10
    elif avg_len < 4.5:
        return 0.28
    elif avg_len < 5.0:
        return 0.42
    elif avg_len < 5.5:
        return 0.58
    elif avg_len < 6.0:
        return 0.70
    else:
        return 0.82


def analyze_text(text: str) -> float:
    """
    Returns a stylometric score 0–1 where 1 = more AI-like.
    Combines three structural metrics: sentence-length CV, TTR, avg word length.
    """
    if not text or not text.strip():
        return 0.5

    words = re.findall(r'\b\w+\b', text)
    sentences = _split_sentences(text)

    score_slcv = _sentence_length_cv(sentences)
    score_ttr = _type_token_ratio(words)
    score_word_len = _avg_word_length_score(words)

    return round((score_slcv + score_ttr + score_word_len) / 3, 4)
