"""
The contract for FNOL triage extraction.

extract.py and evaluate.py both depend on this file. It is the single
source of truth for what a triage record looks like. Change it
deliberately -- every change invalidates your cache and your gold labels.
"""

from typing import Literal
from pydantic import BaseModel, Field

ClaimType = Literal[
    "collision", "mechanical", "fire", "theft", "weather", "injury", "other"
]
Severity = Literal["low", "medium", "high"]
Routing = Literal["auto_process", "adjuster_review", "urgent_escalation"]

# Fields scored against hand labels. Free-text and model-internal fields
# (cause_of_loss, confidence, evidence_span) are excluded -- they are
# evaluated differently or not at all.
SCORED_FIELDS = [
    "claim_type",
    "severity",
    "injury_reported",
    "safety_critical",
    "routing",
]


class TriageResult(BaseModel):
    """Structured triage output for a single loss narrative."""

    claim_type: ClaimType = Field(
        description="Primary category of the loss event."
    )
    cause_of_loss: str = Field(
        max_length=120,
        description="Short phrase naming what caused the loss.",
    )
    severity: Severity = Field(
        description=(
            "high = injury, fire, rollover, total loss, or safety-critical "
            "failure. medium = damage requiring repair, no injury. "
            "low = cosmetic or minor, no injury, still operable."
        )
    )
    injury_reported: bool = Field(
        description="True only if the narrative states a person was hurt."
    )
    safety_critical: bool = Field(
        description=(
            "True if the described failure could cause loss of control, "
            "fire, or injury if it recurred."
        )
    )
    missing_info: list[str] = Field(
        default_factory=list,
        max_length=6,
        description=(
            "Facts an adjuster would need that the narrative does not "
            "provide (e.g. 'date of loss', 'other party involved')."
        ),
    )
    routing: Routing = Field(
        description=(
            "auto_process = low severity and complete information. "
            "adjuster_review = anything ambiguous or incomplete. "
            "urgent_escalation = injury or safety-critical."
        )
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Probability a trained adjuster would agree with your severity "
            "and routing. Below 0.5 when key facts are missing."
        ),
    )
    evidence_span: str = Field(
        default="",
        description=(
            "Text copied VERBATIM from the narrative supporting the "
            "severity call. Empty string if no single span supports it."
        ),
    )


def normalize(text: str) -> str:
    """Whitespace- and case-insensitive form, for grounding checks."""
    return " ".join(text.lower().split())


def is_grounded(result: TriageResult, narrative: str) -> bool | None:
    """
    Is evidence_span actually present in the source text?

    Returns None when the model declined to cite a span (not a failure --
    excluded from the grounding rate so an empty span can't inflate it).
    """
    if not result.evidence_span.strip():
        return None
    return normalize(result.evidence_span) in normalize(narrative)
