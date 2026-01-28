"""Core types for the LLM Orchestration Layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ModelTier(int, Enum):
    """Model tiers based on capability and cost.

    Tier 1: Deep reasoning (o3, Claude Opus, Gemini Ultra)
    Tier 2: Content generation (GPT-4o, Claude Sonnet)
    Tier 3: Conversation (GPT-4o-mini, Claude Haiku)
    Tier 4: Classification (fine-tuned, embeddings)
    Tier 5: Local (Llama, Mistral, offline)
    """
    REASONING = 1
    GENERATION = 2
    CONVERSATION = 3
    CLASSIFICATION = 4
    LOCAL = 5


class TaskType(str, Enum):
    """Types of tasks the LLM orchestration handles."""

    # Discovery tasks
    ORG_STRUCTURE_EXTRACTION = "org_structure_extraction"
    DATA_SOURCE_DETECTION = "data_source_detection"
    TEMPLATE_MATCHING = "template_matching"

    # Knowledge base tasks
    REGULATORY_SYNTHESIS = "regulatory_synthesis"
    KB_GENERATION = "kb_generation"
    FAQ_GENERATION = "faq_generation"
    CONTENT_REVIEW = "content_review"

    # Agent runtime tasks
    INTENT_CLASSIFICATION = "intent_classification"
    STANDARD_QUERY = "standard_query"
    COMPLEX_ANALYSIS = "complex_analysis"
    POLICY_INTERPRETATION = "policy_interpretation"

    # Governance tasks
    SEMANTIC_VALIDATION = "semantic_validation"
    RISK_ASSESSMENT = "risk_assessment"

    # General
    GENERAL = "general"


# Task to Tier mapping with metadata
TASK_TIER_CONFIG: dict[TaskType, dict[str, Any]] = {
    # Discovery
    TaskType.ORG_STRUCTURE_EXTRACTION: {
        "tier": ModelTier.GENERATION,
        "fallback_tier": ModelTier.CONVERSATION,
        "max_latency_ms": 30000,
        "requires_json": True,
    },
    TaskType.DATA_SOURCE_DETECTION: {
        "tier": ModelTier.CONVERSATION,
        "fallback_tier": ModelTier.LOCAL,
        "max_latency_ms": 10000,
    },
    TaskType.TEMPLATE_MATCHING: {
        "tier": ModelTier.CLASSIFICATION,
        "fallback_tier": ModelTier.CONVERSATION,
        "max_latency_ms": 2000,
    },

    # Knowledge base
    TaskType.REGULATORY_SYNTHESIS: {
        "tier": ModelTier.REASONING,
        "fallback_tier": ModelTier.GENERATION,
        "max_latency_ms": 60000,
        "high_stakes": True,
    },
    TaskType.KB_GENERATION: {
        "tier": ModelTier.GENERATION,
        "fallback_tier": ModelTier.CONVERSATION,
        "max_latency_ms": 30000,
    },
    TaskType.FAQ_GENERATION: {
        "tier": ModelTier.GENERATION,
        "fallback_tier": ModelTier.CONVERSATION,
        "max_latency_ms": 20000,
    },
    TaskType.CONTENT_REVIEW: {
        "tier": ModelTier.REASONING,
        "fallback_tier": ModelTier.GENERATION,
        "max_latency_ms": 30000,
        "high_stakes": True,
    },

    # Agent runtime
    TaskType.INTENT_CLASSIFICATION: {
        "tier": ModelTier.CLASSIFICATION,
        "fallback_tier": ModelTier.CONVERSATION,
        "max_latency_ms": 500,
        "requires_low_latency": True,
    },
    TaskType.STANDARD_QUERY: {
        "tier": ModelTier.CONVERSATION,
        "fallback_tier": ModelTier.LOCAL,
        "max_latency_ms": 5000,
    },
    TaskType.COMPLEX_ANALYSIS: {
        "tier": ModelTier.GENERATION,
        "fallback_tier": ModelTier.REASONING,
        "max_latency_ms": 15000,
    },
    TaskType.POLICY_INTERPRETATION: {
        "tier": ModelTier.REASONING,
        "fallback_tier": ModelTier.GENERATION,
        "max_latency_ms": 20000,
        "high_stakes": True,
        "human_review_recommended": True,
    },

    # Governance
    TaskType.SEMANTIC_VALIDATION: {
        "tier": ModelTier.GENERATION,
        "fallback_tier": ModelTier.CONVERSATION,
        "max_latency_ms": 5000,
    },
    TaskType.RISK_ASSESSMENT: {
        "tier": ModelTier.REASONING,
        "fallback_tier": ModelTier.GENERATION,
        "max_latency_ms": 10000,
        "high_stakes": True,
    },

    # General
    TaskType.GENERAL: {
        "tier": ModelTier.CONVERSATION,
        "fallback_tier": ModelTier.LOCAL,
        "max_latency_ms": 10000,
    },
}


class Task(BaseModel):
    """A task to be executed by an LLM."""

    task_type: TaskType = Field(default=TaskType.GENERAL)
    prompt: str = Field(default="")
    context_length: int = Field(default=0, description="Length of context in characters")
    max_tokens: int = Field(default=4000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    # Task characteristics
    requires_reasoning: bool = Field(default=False)
    requires_generation: bool = Field(default=False)
    requires_json: bool = Field(default=False)
    requires_low_latency: bool = Field(default=False)
    high_stakes: bool = Field(default=False)
    can_batch: bool = Field(default=False)
    requires_immediate: bool = Field(default=True)

    # Quality requirements
    quality_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    max_retries: int = Field(default=2)

    # Metadata
    organization_id: str | None = Field(default=None)
    department: str | None = Field(default=None)
    request_id: str | None = Field(default=None)

    def get_tier_config(self) -> dict[str, Any]:
        """Get the tier configuration for this task type."""
        return TASK_TIER_CONFIG.get(self.task_type, TASK_TIER_CONFIG[TaskType.GENERAL])

    def get_default_tier(self) -> ModelTier:
        """Get the default tier for this task."""
        config = self.get_tier_config()
        return config.get("tier", ModelTier.CONVERSATION)

    def get_fallback_tier(self) -> ModelTier:
        """Get the fallback tier for this task."""
        config = self.get_tier_config()
        return config.get("fallback_tier", ModelTier.LOCAL)


class ModelResponse(BaseModel):
    """Response from an LLM."""

    content: str = Field(description="Generated content")
    model: str = Field(description="Model that generated this response")
    provider: str = Field(default="unknown")

    # Usage statistics
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)

    # Performance
    latency_ms: float = Field(default=0.0)

    # Metadata
    finish_reason: str = Field(default="stop")
    request_id: str | None = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def usage(self) -> dict[str, int]:
        """Get usage as a dictionary."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


class RoutingDecision(BaseModel):
    """Decision from the intelligent router."""

    selected_model: str = Field(description="Model ID to use")
    selected_tier: ModelTier = Field(description="Tier of selected model")
    provider: str = Field(description="Provider name")

    reason: str = Field(default="optimal_match")
    fallback_used: bool = Field(default=False)
    original_preference: str | None = Field(default=None)

    estimated_cost: float = Field(default=0.0)
    estimated_latency_ms: float = Field(default=0.0)

    # Warnings
    over_budget: bool = Field(default=False)
    quality_warning: bool = Field(default=False)


@dataclass
class QualityScore:
    """Quality score for a response."""

    criterion: str
    score: float
    threshold: float
    passed: bool = field(init=False)
    details: str = ""

    def __post_init__(self):
        self.passed = self.score >= self.threshold


class ValidationResult(BaseModel):
    """Result of validating an LLM output."""

    valid: bool = Field(description="Whether output passed validation")
    overall_quality: float = Field(default=1.0, ge=0.0, le=1.0)

    format_valid: bool = Field(default=True)
    format_errors: list[str] = Field(default_factory=list)

    quality_scores: dict[str, float] = Field(default_factory=dict)
    failed_criteria: list[str] = Field(default_factory=list)

    completeness_score: float = Field(default=1.0)
    missing_fields: list[str] = Field(default_factory=list)

    warnings: list[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    """Result of executing a task through the orchestration layer."""

    success: bool = Field(description="Whether execution succeeded")
    response: ModelResponse | None = Field(default=None)
    routing: RoutingDecision | None = Field(default=None)
    validation: ValidationResult | None = Field(default=None)

    # Cost tracking
    actual_cost: float = Field(default=0.0)
    cost_saved: float = Field(default=0.0, description="Cost saved through optimization")

    # Retry information
    retries: int = Field(default=0)
    retry_reasons: list[str] = Field(default_factory=list)

    # Warnings
    quality_warning: bool = Field(default=False)
    fallback_used: bool = Field(default=False)
    cache_hit: bool = Field(default=False)

    # Timing
    total_latency_ms: float = Field(default=0.0)

    # Error information
    error: str | None = Field(default=None)
    error_code: str | None = Field(default=None)


# Model pricing per 1M tokens (approximate, update as needed)
MODEL_PRICING: dict[str, dict[str, float]] = {
    # OpenAI
    "openai/o3": {"input": 15.0, "output": 60.0},
    "openai/o1": {"input": 15.0, "output": 60.0},
    "openai/gpt-4o": {"input": 2.5, "output": 10.0},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "openai/gpt-4-turbo": {"input": 10.0, "output": 30.0},

    # Anthropic
    "anthropic/claude-opus-4-5": {"input": 15.0, "output": 75.0},
    "anthropic/claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "anthropic/claude-haiku": {"input": 0.25, "output": 1.25},

    # Google
    "google/gemini-ultra": {"input": 10.0, "output": 30.0},
    "google/gemini-2-pro": {"input": 1.25, "output": 5.0},
    "google/gemini-flash": {"input": 0.075, "output": 0.30},

    # Local (no cost)
    "local/llama-3-70b": {"input": 0.0, "output": 0.0},
    "local/llama-3-8b": {"input": 0.0, "output": 0.0},
    "local/mistral-7b": {"input": 0.0, "output": 0.0},
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate cost for a model call."""
    pricing = MODEL_PRICING.get(model, {"input": 1.0, "output": 2.0})
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost
