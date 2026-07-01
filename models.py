from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DetectionResult:
    stylometric_score: float
    llm_score: Optional[float] = None
    llm_available: bool = True


@dataclass
class ContentSubmission:
    content_id: str
    creator_id: str
    text: str
    timestamp: str
    attribution: str          # "likely_ai" | "likely_human" | "uncertain"
    confidence: float
    llm_score: Optional[float]
    stylometric_score: float
    label: str
    status: str = "classified"
    llm_available: bool = True


@dataclass
class AppealRecord:
    appeal_id: str
    content_id: str
    creator_reasoning: str
    timestamp: str
    original_attribution: str
    original_confidence: float


@dataclass
class AuditLogEntry:
    entry_id: str
    event_type: str           # "classification" | "appeal"
    content_id: str
    creator_id: str
    timestamp: str
    attribution: str
    confidence: float
    stylometric_score: float
    label: str
    status: str
    llm_score: Optional[float] = None
    llm_available: bool = True
    appeal_reasoning: Optional[str] = None
