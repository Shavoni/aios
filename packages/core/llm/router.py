"""Intelligent Model Router for aiOS.

Routes requests to the optimal model based on:
- Task complexity and type
- Cost constraints
- Latency requirements
- Client preferences
- Model availability
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from packages.core.llm.types import (
    Task,
    TaskType,
    ModelTier,
    ModelResponse,
    RoutingDecision,
    ExecutionResult,
    ValidationResult,
    calculate_cost,
    TASK_TIER_CONFIG,
)
from packages.core.llm.adapters.registry import get_model_registry, ModelRegistry
from packages.core.llm.adapters.base import ModelAdapter


class IntelligentModelRouter:
    """Routes requests to the optimal model based on multiple factors.

    The router considers:
    1. Task type and complexity
    2. Organization preferences
    3. Cost budget
    4. Latency requirements
    5. Model availability and health
    """

    _instance: IntelligentModelRouter | None = None

    def __init__(
        self,
        registry: ModelRegistry | None = None,
        cost_tracker: Any | None = None,
        performance_monitor: Any | None = None,
    ):
        self._registry = registry or get_model_registry()
        self._cost_tracker = cost_tracker
        self._performance_monitor = performance_monitor
        self._model_health_cache: dict[str, dict[str, Any]] = {}
        self._health_cache_ttl = 60  # seconds

    @classmethod
    def get_instance(cls) -> IntelligentModelRouter:
        """Get singleton router instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    async def route(
        self,
        task: Task,
    ) -> RoutingDecision:
        """Determine optimal model for this task.

        Args:
            task: Task to route

        Returns:
            RoutingDecision with selected model and metadata
        """
        # 1. Determine task tier from task type
        tier = self._classify_tier(task)

        # 2. Get available models for this tier (respecting org preferences)
        models = self._registry.get_tier_models(tier, task.organization_id)

        if not models:
            # Fall back to next tier
            fallback_tier = task.get_fallback_tier()
            models = self._registry.get_tier_models(fallback_tier, task.organization_id)
            tier = fallback_tier

        if not models:
            raise RuntimeError(f"No models available for tier {tier}")

        # 3. Check cost budget if tracker available
        primary_model = models[0]
        over_budget = False

        if self._cost_tracker and task.organization_id:
            estimated_cost = self._estimate_cost(task, primary_model)
            budget_ok = await self._cost_tracker.check_budget(
                org_id=task.organization_id,
                estimated_cost=estimated_cost,
            )
            if not budget_ok:
                over_budget = True
                # Try to downgrade tier
                downgraded_tier = self._downgrade_tier(tier)
                if downgraded_tier != tier:
                    downgraded_models = self._registry.get_tier_models(
                        downgraded_tier, task.organization_id
                    )
                    if downgraded_models:
                        models = downgraded_models
                        tier = downgraded_tier
                        primary_model = models[0]

        # 4. Check model health
        health = await self._check_model_health(primary_model)

        fallback_used = False
        if not health.get("healthy", False):
            # Use fallback model
            if len(models) > 1:
                primary_model = models[1]
                fallback_used = True
            else:
                # No fallback available
                pass

        # 5. Build routing decision
        provider = primary_model.split("/")[0] if "/" in primary_model else "unknown"

        return RoutingDecision(
            selected_model=primary_model,
            selected_tier=tier,
            provider=provider,
            reason="optimal_match" if not fallback_used else "primary_unavailable",
            fallback_used=fallback_used,
            original_preference=models[0] if fallback_used else None,
            estimated_cost=self._estimate_cost(task, primary_model),
            estimated_latency_ms=health.get("latency_ms", 0),
            over_budget=over_budget,
        )

    def _classify_tier(self, task: Task) -> ModelTier:
        """Classify task into appropriate model tier."""
        # Check explicit task type mapping first
        config = TASK_TIER_CONFIG.get(task.task_type)
        if config:
            return config["tier"]

        # Heuristic classification based on task properties
        if task.requires_reasoning or task.high_stakes:
            return ModelTier.REASONING

        if task.requires_generation or task.context_length > 50000:
            return ModelTier.GENERATION

        if task.requires_low_latency:
            return ModelTier.CLASSIFICATION

        if task.requires_json and task.context_length < 5000:
            return ModelTier.CLASSIFICATION

        return ModelTier.CONVERSATION

    def _downgrade_tier(self, tier: ModelTier) -> ModelTier:
        """Get a cheaper tier."""
        tier_order = [
            ModelTier.REASONING,
            ModelTier.GENERATION,
            ModelTier.CONVERSATION,
            ModelTier.CLASSIFICATION,
            ModelTier.LOCAL,
        ]
        try:
            idx = tier_order.index(tier)
            if idx < len(tier_order) - 1:
                return tier_order[idx + 1]
        except ValueError:
            pass
        return tier

    def _estimate_cost(self, task: Task, model: str) -> float:
        """Estimate cost for a task with a specific model."""
        # Rough estimate based on context and expected output
        estimated_input_tokens = task.context_length // 4
        estimated_output_tokens = task.max_tokens // 2
        return calculate_cost(model, estimated_input_tokens, estimated_output_tokens)

    async def _check_model_health(self, model_id: str) -> dict[str, Any]:
        """Check model health with caching."""
        now = time.time()

        # Check cache
        if model_id in self._model_health_cache:
            cached = self._model_health_cache[model_id]
            if now - cached.get("timestamp", 0) < self._health_cache_ttl:
                return cached

        # Check health
        health = await self._registry.check_model_health(model_id)
        health["timestamp"] = now
        self._model_health_cache[model_id] = health

        return health

    async def execute(
        self,
        task: Task,
        prompt: str,
        system_prompt: str | None = None,
    ) -> ExecutionResult:
        """Route and execute a task.

        Args:
            task: Task to execute
            prompt: The prompt to send
            system_prompt: Optional system prompt

        Returns:
            ExecutionResult with response and metadata
        """
        start_time = time.time()

        # Route to optimal model
        routing = await self.route(task)

        # Get adapter
        adapter = self._registry.get_adapter(routing.selected_model)

        # Execute with retry logic
        response = None
        retries = 0
        retry_reasons = []
        last_error = None

        while retries <= task.max_retries:
            try:
                response = await adapter.complete(
                    prompt=prompt,
                    max_tokens=task.max_tokens,
                    temperature=task.temperature,
                    system_prompt=system_prompt,
                    response_format={"type": "json_object"} if task.requires_json else None,
                )
                break

            except Exception as e:
                last_error = str(e)
                retry_reasons.append(f"Attempt {retries + 1}: {last_error}")
                retries += 1

                if retries <= task.max_retries:
                    # Try fallback model on retry
                    fallback = self._registry.get_fallback_model(
                        routing.selected_tier, task.organization_id
                    )
                    if fallback and fallback != routing.selected_model:
                        adapter = self._registry.get_adapter(fallback)
                        routing.fallback_used = True
                        routing.selected_model = fallback

                await asyncio.sleep(0.5 * retries)  # Backoff

        total_latency = (time.time() - start_time) * 1000

        if response is None:
            return ExecutionResult(
                success=False,
                response=None,
                routing=routing,
                error=last_error,
                error_code="execution_failed",
                retries=retries,
                retry_reasons=retry_reasons,
                total_latency_ms=total_latency,
            )

        # Calculate actual cost
        actual_cost = calculate_cost(
            routing.selected_model,
            response.prompt_tokens,
            response.completion_tokens,
        )

        # Track cost if tracker available
        if self._cost_tracker and task.organization_id:
            await self._cost_tracker.record(
                org_id=task.organization_id,
                model=routing.selected_model,
                cost=actual_cost,
            )

        return ExecutionResult(
            success=True,
            response=response,
            routing=routing,
            actual_cost=actual_cost,
            retries=retries,
            retry_reasons=retry_reasons if retry_reasons else [],
            fallback_used=routing.fallback_used,
            total_latency_ms=total_latency,
        )

    async def execute_with_validation(
        self,
        task: Task,
        prompt: str,
        system_prompt: str | None = None,
        validator: Any | None = None,
    ) -> ExecutionResult:
        """Execute with output validation and retry on quality failure.

        Args:
            task: Task to execute
            prompt: The prompt
            system_prompt: Optional system prompt
            validator: Optional OutputValidator instance

        Returns:
            ExecutionResult with validation info
        """
        result = await self.execute(task, prompt, system_prompt)

        if not result.success or not result.response:
            return result

        # Validate if validator provided
        if validator:
            validation = await validator.validate(
                response=result.response,
                task=task,
            )

            result.validation = validation

            # Retry if quality too low
            if not validation.valid or validation.overall_quality < task.quality_threshold:
                result.quality_warning = True

                if result.retries < task.max_retries:
                    # Build feedback prompt for retry
                    feedback_prompt = self._build_feedback_prompt(
                        original_prompt=prompt,
                        response=result.response.content,
                        validation=validation,
                    )

                    retry_result = await self.execute(
                        task=task,
                        prompt=feedback_prompt,
                        system_prompt=system_prompt,
                    )

                    if retry_result.success and retry_result.response:
                        retry_result.retries = result.retries + 1
                        retry_result.retry_reasons = result.retry_reasons + ["quality_below_threshold"]
                        return retry_result

        return result

    def _build_feedback_prompt(
        self,
        original_prompt: str,
        response: str,
        validation: ValidationResult,
    ) -> str:
        """Build a feedback prompt for quality retry."""
        issues = []
        if validation.format_errors:
            issues.extend(validation.format_errors)
        if validation.missing_fields:
            issues.append(f"Missing fields: {', '.join(validation.missing_fields)}")
        if validation.failed_criteria:
            issues.append(f"Failed criteria: {', '.join(validation.failed_criteria)}")

        issues_text = "\n".join(f"- {issue}" for issue in issues)

        return f"""Your previous response had some issues that need correction.

ORIGINAL REQUEST:
{original_prompt}

YOUR PREVIOUS RESPONSE:
{response}

ISSUES TO FIX:
{issues_text}

Please provide a corrected response that addresses these issues.
Make sure to follow the exact output format requested."""


def get_model_router() -> IntelligentModelRouter:
    """Get the singleton model router."""
    return IntelligentModelRouter.get_instance()
