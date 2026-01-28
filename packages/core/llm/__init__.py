"""LLM Orchestration Layer for aiOS.

Model-agnostic intelligence framework that:
- Routes requests to optimal models based on task complexity
- Provides cost optimization (40-70% savings target)
- Ensures quality through validation and retry
- Supports multiple providers: OpenAI, Anthropic, Google, Local

Key principle: aiOS guides the model. The model doesn't guide aiOS.
"""

from packages.core.llm.types import (
    ModelTier,
    Task,
    TaskType,
    ModelResponse,
    RoutingDecision,
    ExecutionResult,
    ValidationResult,
    QualityScore,
    calculate_cost,
    TASK_TIER_CONFIG,
)
from packages.core.llm.router import (
    IntelligentModelRouter,
    get_model_router,
)
from packages.core.llm.adapters import (
    ModelAdapter,
    OpenAIAdapter,
    AnthropicAdapter,
    LocalModelAdapter,
    ModelRegistry,
    get_adapter,
    get_model_registry,
)
from packages.core.llm.cost_optimizer import (
    CostOptimizer,
    CostTracker,
    ResponseCache,
    CacheEntry,
    OrgBudget,
)
from packages.core.llm.quality import (
    OutputValidator,
    QualityScorer,
    ConfigurableValidator,
    TaskSpecificValidator,
    ScoreResult,
)
from packages.core.llm.prompts import (
    PromptTemplate,
    PromptEngine,
)

__all__ = [
    # Types
    "ModelTier",
    "Task",
    "TaskType",
    "ModelResponse",
    "RoutingDecision",
    "ExecutionResult",
    "ValidationResult",
    "QualityScore",
    "calculate_cost",
    "TASK_TIER_CONFIG",
    # Router
    "IntelligentModelRouter",
    "get_model_router",
    # Adapters
    "ModelAdapter",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "LocalModelAdapter",
    "ModelRegistry",
    "get_adapter",
    "get_model_registry",
    # Cost
    "CostOptimizer",
    "CostTracker",
    "ResponseCache",
    "CacheEntry",
    "OrgBudget",
    # Quality
    "OutputValidator",
    "QualityScorer",
    "ConfigurableValidator",
    "TaskSpecificValidator",
    "ScoreResult",
    # Prompts
    "PromptTemplate",
    "PromptEngine",
]
