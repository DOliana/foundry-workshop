"""Pydantic schemas used by Functions and agents.

These define the structured contracts for:
  * IntakeFacts — what the intake agent extracts from documents/conversation
  * AssessmentMemo — the Initial Assessment Memo that the orchestrator drafts
                     and persists after HITL approval
  * RequestLogEntry — governance log entry written at every conversation start
  * ReviewerNotification — payload routed to reviewer-inbox queue
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceReference(BaseModel):
    """Pointer to evidence — file in sample-docs/ or transcript turn."""

    kind: Literal["document", "transcript", "ledger"] = "document"
    document_id: str | None = None
    excerpt: str | None = None
    page: int | None = None


class Person(BaseModel):
    name: str
    role: str | None = None
    organization: str | None = None
    relevance: str | None = None


class LegalNormReference(BaseModel):
    norm: str = Field(description="e.g. '§ 334 StGB i. V. m. IntBestG'")
    elements_of_offence: str | None = None
    risk_class: Literal["directly relevant", "indirectly relevant", "unclear"] = "unclear"
    confidence: Confidence = Confidence.MEDIUM


class NextStep(BaseModel):
    step: str
    owner: str | None = None
    due_by: str | None = None
    status: Literal["open", "in progress", "done", "blocked"] = "open"


class IntakeFacts(BaseModel):
    """Structured facts extracted from intake documents / conversation."""

    case_id: str
    client_name: str
    engagement_id: str | None = None
    summary: str
    triggering_event: str
    persons: list[Person] = Field(default_factory=list)
    documented_facts: list[str] = Field(default_factory=list)
    unconfirmed_claims: list[str] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    captured_at: datetime = Field(default_factory=datetime.utcnow)


class MaterialityAssessment(BaseModel):
    direct_effects: str
    indirect_effects: str
    materiality_judgement: Literal["material", "potentially material", "not material"]


class Escalation(BaseModel):
    recipient: str
    function: str
    informed_on: str | None = None
    form: str | None = None


class AssessmentMemo(BaseModel):
    """Initial Assessment Memo — output of the orchestrator workflow."""

    case_id: str
    memo_version: str = "1.0"
    drafted_at: datetime = Field(default_factory=datetime.utcnow)
    header: dict[str, str]
    intake: IntakeFacts
    legal_assessment: list[LegalNormReference]
    materiality: MaterialityAssessment
    next_steps: list[NextStep]
    escalations: list[Escalation]
    drafted_by_agent: str = "noclar-orchestrator"
    approved_by: str | None = None
    approved_at: datetime | None = None


class RequestLogEntry(BaseModel):
    """Governance-required log written at the start of every conversation.

    NOTE: Per workshop governance requirement, this is written *before* any
    user content is processed by the agent.
    """

    conversation_id: str
    user_principal: str | None = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    channel: Literal["chat", "voice", "api"] = "chat"
    locale: str = "en-US"
    intent: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class ReviewerNotification(BaseModel):
    """Payload routed to the reviewer-inbox queue when HITL approval is needed."""

    conversation_id: str
    case_id: str
    memo_blob_path: str
    drafted_at: datetime
    requested_reviewer: str | None = None
    summary: str
