"""Module for holding the data-models for interacting with AI Agents."""

from enum import StrEnum, auto
from typing import NamedTuple

from pydantic import BaseModel

from data_models.mail_models import MailMessage


class MsgTier(StrEnum):
    """Enumerator for message tiers."""

    TIER_1_SOVEREIGN = auto()
    TIER_2_HIGH_SIGNAL = auto()
    TIER_3_GENERAL = auto()
    TIER_4_NOISE = auto()


class AIResponse(BaseModel):
    """Response model for the AI models."""

    tier: MsgTier
    score: int
    summary: str
    action_required: bool
    reasoning: str


class EmailCategorization(NamedTuple):
    """Binding the AI Responses to their original requests."""

    email: MailMessage
    result: AIResponse
