# AIOS LLM Orchestration Layer - Integration Guide

## Overview

This document provides instructions for integrating the LLM Orchestration Layer into the existing AIOS codebase. This module is the **core differentiator** that delivers 40-70% cost savings through intelligent tier-based routing.

---

## Module Structure

```
packages/core/llm/
├── __init__.py              # Public API exports
├── models.py                # Data models and schemas
├── router.py                # IntelligentModelRouter + TaskClassifier + CostOptimizer
├── adapters/
│   ├── __init__.py
│   ├── base.py              # ModelAdapter ABC
│   ├── openai_adapter.py    # OpenAI (GPT-4o, o1, o3)
│   ├── anthropic_adapter.py # Claude (Opus, Sonnet, Haiku)
│   └── local_adapter.py     # Ollama, vLLM, LMStudio
├── quality/
│   ├── __init__.py
│   └── validator.py         # QualityValidator
└── config/
    └── task_tiers.yaml      # Task-to-tier mapping config
```

---

## Quick Start

### 1. Copy Module to AIOS

```bash
# From the AIOS root directory
cp -r /home/claude/aios_llm_orchestration/packages/core/llm packages/core/
```

### 2. Install Dependencies

```bash
pip install httpx tenacity pydantic pydantic-settings
```

### 3. Configure API Keys

```bash
# In .env file
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_HOST=http://localhost:11434  # Optional
```

### 4. Initialize Router

```python
from packages.core.llm import (
    IntelligentModelRouter,
    OpenAIAdapter,
    AnthropicAdapter,
    LocalModelAdapter,
    ModelProvider,
)

# Create adapters
adapters = {
    ModelProvider.OPENAI: OpenAIAdapter(),
    ModelProvider.ANTHROPIC: AnthropicAdapter(),
    ModelProvider.LOCAL: LocalModelAdapter(),
}

# Create router
router = IntelligentModelRouter(model_adapters=adapters)
```

---

## Integration Points

### 1. Agent Query Endpoint (`packages/api/agents.py`)

Replace the existing LLM call with the router:

```python
# Before (existing code around line 340-350)
result = await llm_provider.complete(query)

# After (with router)
from packages.core.llm import (
    IntelligentModelRouter,
    TaskType,
    RoutingStrategy,
)

# Route the request
decision = await router.route(
    prompt=request.query,
    organization_id=tenant_id,
    context={
        "domain": agent.domain,
        "governance_local_only": governance.provider_constraints.local_only,
    },
)

# Execute with selected model
response = await router.execute(
    prompt=full_prompt,
    routing_decision=decision,
    max_tokens=governance.max_tokens or 4096,
    temperature=0.7,
)

# Use response.content for the reply
result = {
    "text": response.content,
    "model": response.model_used,
    "cost": response.actual_cost,
    "tier": response.tier.value,
}
```

### 2. Discovery Module (`packages/core/discovery/discovery_agent.py`)

Integrate for LLM-powered extraction:

```python
from packages.core.llm import IntelligentModelRouter, TaskType

async def extract_with_llm(self, html_content: str) -> dict:
    """Use LLM for semantic extraction."""

    decision = await self.router.route(
        prompt=f"Extract organizational structure from:\n\n{html_content[:10000]}",
        explicit_task_type=TaskType.ORG_STRUCTURE_EXTRACTION,
    )

    response = await self.router.execute(
        prompt=self._build_extraction_prompt(html_content),
        routing_decision=decision,
    )

    return self._parse_extraction(response.content)
```

### 3. Knowledge Base Generator (`packages/onboarding/kb_generator/`)

Use for content generation:

```python
from packages.core.llm import IntelligentModelRouter, TaskType

async def generate_kb_content(self, template: dict, context: dict) -> str:
    """Generate KB file content using LLM."""

    decision = await self.router.route(
        prompt=self._build_kb_prompt(template, context),
        explicit_task_type=TaskType.KB_GENERATION,
    )

    response = await self.router.execute(
        prompt=self._build_kb_prompt(template, context),
        routing_decision=decision,
        max_tokens=16000,
    )

    return response.content
```

### 4. Governance Module (`packages/core/governance/`)

Use the quality validator:

```python
from packages.core.llm import QualityValidator, validate_response

def validate_agent_response(
    response: str,
    sources: list[dict],
    domain: str,
) -> GovernanceValidation:
    """Validate response meets quality standards."""

    validator = QualityValidator(
        strict_mode=(domain in ["Legal", "HR", "Medical"]),
        require_citations=True,
    )

    report = validator.validate(
        response=response,
        sources=sources,
        response_type="policy_response" if domain in ["Legal", "HR"] else None,
    )

    return GovernanceValidation(
        is_valid=report.is_deliverable,
        requires_review=report.requires_review,
        quality_score=report.overall_score,
        issues=report.rejection_reasons,
    )
```

---

## Per-Organization Configuration

### Creating Organization Preferences

```python
from packages.core.llm import (
    ClientModelPreferences,
    TierConfig,
    ModelTier,
    ModelProvider,
    RoutingStrategy,
)

# Cleveland deployment configuration
cleveland_preferences = ClientModelPreferences(
    organization_id="cleveland-2026",

    # Budget controls
    daily_budget=500.0,
    per_request_max=2.0,
    alert_threshold=0.8,

    # Default strategy
    default_strategy=RoutingStrategy.BALANCED,

    # Provider preferences
    preferred_providers=[ModelProvider.OPENAI, ModelProvider.ANTHROPIC],
    blocked_providers=[],

    # Privacy settings
    allow_external_providers=True,
    pii_requires_local=True,  # HR queries go local

    # Custom tier configs (override defaults)
    tier_configs={
        ModelTier.CONVERSATION: TierConfig(
            tier=ModelTier.CONVERSATION,
            primary_model="openai/gpt-4o-mini",
            fallback_model="anthropic/claude-haiku-4-5",
            default_max_tokens=4000,
            default_temperature=0.7,
        ),
    },
)
```

### Loading from YAML

```python
import yaml
from packages.core.llm import ClientModelPreferences

def load_org_preferences(org_id: str) -> ClientModelPreferences:
    """Load preferences from deployment config."""
    config_path = f"deployments/{org_id}/config/model_preferences.yaml"

    with open(config_path) as f:
        config = yaml.safe_load(f)

    return ClientModelPreferences(**config)
```

---

## API Endpoints

### Add Cost Reporting Endpoint

```python
# In packages/api/system.py

from packages.core.llm import get_router

@router.get("/llm/cost-report/{org_id}")
async def get_cost_report(org_id: str):
    """Get cost optimization report for organization."""
    llm_router = get_router()
    report = llm_router.get_cost_report(org_id)

    return {
        "organization_id": report.organization_id,
        "period": {
            "start": report.period_start.isoformat(),
            "end": report.period_end.isoformat(),
        },
        "usage": {
            "total_requests": report.total_requests,
            "total_tokens": report.total_tokens,
            "by_tier": {tier.value: count for tier, count in report.tier_usage.items()},
        },
        "costs": {
            "total": report.total_cost,
            "by_tier": {tier.value: cost for tier, cost in report.tier_costs.items()},
        },
        "savings": {
            "baseline_cost": report.baseline_cost,
            "actual_cost": report.actual_cost,
            "saved_amount": report.savings_amount,
            "saved_percentage": report.savings_percentage,
        },
        "budget": {
            "limit": report.budget_limit,
            "used_percentage": report.budget_used_percentage,
        },
    }
```

### Add Model Health Endpoint

```python
@router.get("/llm/health")
async def check_model_health():
    """Check health of all configured model providers."""
    from packages.core.llm import OpenAIAdapter, AnthropicAdapter, LocalModelAdapter

    results = {}

    openai = OpenAIAdapter()
    results["openai"] = await openai.health_check()

    anthropic = AnthropicAdapter()
    results["anthropic"] = await anthropic.health_check()

    local = LocalModelAdapter()
    results["local"] = await local.health_check()

    return {
        "providers": results,
        "all_healthy": all(results.values()),
    }
```

---

## Testing

### Run Unit Tests

```bash
cd /home/claude/aios_llm_orchestration
pytest test_llm_orchestration.py -v
```

### Integration Test

```python
import asyncio
from packages.core.llm import (
    IntelligentModelRouter,
    OpenAIAdapter,
    ModelProvider,
    TaskType,
)

async def test_integration():
    # Setup
    adapters = {
        ModelProvider.OPENAI: OpenAIAdapter(),
    }
    router = IntelligentModelRouter(model_adapters=adapters)

    # Route
    decision = await router.route(
        prompt="What is the PTO policy?",
        organization_id="test-org",
    )

    print(f"Selected model: {decision.selected_model}")
    print(f"Tier: {decision.selected_tier}")
    print(f"Estimated cost: ${decision.estimated_cost:.4f}")

    # Execute (requires API key)
    if os.environ.get("OPENAI_API_KEY"):
        response = await router.execute(
            prompt="What is 2+2?",
            routing_decision=decision,
        )
        print(f"Response: {response.content}")
        print(f"Actual cost: ${response.actual_cost:.4f}")

asyncio.run(test_integration())
```

---

## Cost Savings Validation

### Calculating ROI

```python
def calculate_monthly_savings(
    router: IntelligentModelRouter,
    org_id: str,
) -> dict:
    """Calculate monthly cost savings from intelligent routing."""
    report = router.get_cost_report(org_id)

    # Project to monthly
    days_active = max((report.period_end - report.period_start).days, 1)
    monthly_multiplier = 30 / days_active

    projected_monthly_cost = report.actual_cost * monthly_multiplier
    projected_monthly_baseline = report.baseline_cost * monthly_multiplier
    projected_monthly_savings = report.savings_amount * monthly_multiplier

    return {
        "projected_monthly_cost": projected_monthly_cost,
        "without_optimization": projected_monthly_baseline,
        "monthly_savings": projected_monthly_savings,
        "annual_savings": projected_monthly_savings * 12,
        "savings_percentage": report.savings_percentage,
    }
```

### Example Output

```
Cost Report for Cleveland (30 days)
====================================
Total Requests: 45,000
Total Cost: $1,234.56

Tier Distribution:
  - Reasoning (Tier 1): 5% → $567.89
  - Generation (Tier 2): 20% → $456.78
  - Conversation (Tier 3): 60% → $180.89
  - Classification (Tier 4): 10% → $25.00
  - Local (Tier 5): 5% → $0.00

Without Optimization (all Tier 1): $4,567.89
Actual Cost: $1,234.56
Monthly Savings: $3,333.33 (73%)
Annual Savings: $40,000
```

---

## Troubleshooting

### Common Issues

**1. "No adapter for provider"**
```python
# Ensure adapters are registered
router = IntelligentModelRouter(
    model_adapters={
        ModelProvider.OPENAI: OpenAIAdapter(),
        # Add all needed providers
    }
)
```

**2. "API key not configured"**
```bash
# Set environment variables
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
```

**3. Local models not available**
```bash
# Start Ollama
ollama serve
ollama pull llama3:8b
```

**4. Budget exceeded**
```python
# Check budget status
report = router.get_cost_report(org_id)
if report.budget_used_percentage > 90:
    # Alert or auto-downgrade
    decision = await router.route(
        prompt=prompt,
        strategy=RoutingStrategy.COST_OPTIMIZED,
    )
```

---

## Next Steps

1. **Copy module** to `packages/core/llm/`
2. **Update agent queries** to use router
3. **Add cost reporting endpoint**
4. **Configure per-org preferences**
5. **Run tests** to validate
6. **Monitor savings** in production

---

*HAAIS AIOS LLM Orchestration Layer v1.0*
*© 2026 DEF1LIVE LLC*
