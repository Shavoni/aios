# aiOS LLM Orchestration Layer

## Model-Agnostic Intelligence Framework

**Document Type:** Technical Specification
**Version:** 1.0
**Date:** January 2026
**Purpose:** Define how aiOS guides and constrains any LLM through its processes

---

## 1. Core Concept

aiOS is **model-agnostic**. The platform provides:

- **Intelligence Framework:** Prompts, workflows, governance rules
- **Orchestration Layer:** Routes requests, manages context, enforces policies
- **Quality Assurance:** Validates outputs regardless of source model

The underlying LLM is a **pluggable component**. Clients can choose:

- OpenAI (GPT-4o, GPT-4.5, o1, o3)
- Anthropic (Claude Opus 4.5, Sonnet 4.5)
- Google (Gemini 2.0, Gemini Ultra)
- Open Source (Llama 3, Mistral, DeepSeek)
- Local Deployments (Ollama, vLLM)
- Specialized Models (Manus, Perplexity, domain-specific)

**aiOS guides the model. The model doesn't guide aiOS.**

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              aiOS PLATFORM                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    LLM ORCHESTRATION LAYER                             │ │
│  │                                                                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │ │
│  │  │   ROUTER     │  │   PROMPT     │  │   QUALITY    │                │ │
│  │  │              │  │   ENGINE     │  │   VALIDATOR  │                │ │
│  │  │ • Model      │  │              │  │              │                │ │
│  │  │   Selection  │  │ • Template   │  │ • Output     │                │ │
│  │  │ • Cost       │  │   Injection  │  │   Validation │                │ │
│  │  │   Optimize   │  │ • Context    │  │ • Format     │                │ │
│  │  │ • Fallback   │  │   Assembly   │  │   Checking   │                │ │
│  │  │   Handling   │  │ • Mode       │  │ • Governance │                │ │
│  │  │              │  │   Switching  │  │   Compliance │                │ │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                │ │
│  │         │                 │                 │                         │ │
│  └─────────┼─────────────────┼─────────────────┼─────────────────────────┘ │
│            │                 │                 │                           │
│            ▼                 ▼                 ▼                           │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      MODEL PROVIDER ADAPTERS                           │ │
│  │                                                                        │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │ │
│  │  │ OpenAI  │ │Anthropic│ │ Google  │ │  Local  │ │ Custom  │        │ │
│  │  │         │ │         │ │         │ │         │ │         │        │ │
│  │  │ GPT-4o  │ │ Claude  │ │ Gemini  │ │ Ollama  │ │  Manus  │        │ │
│  │  │ GPT-4.5 │ │ Opus    │ │ 2.0     │ │ vLLM    │ │ Domain  │        │ │
│  │  │ o1/o3   │ │ Sonnet  │ │ Ultra   │ │ LMStudio│ │ Models  │        │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘        │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Model Tier System

### 3.1 Tier Definitions

aiOS categorizes tasks by complexity and routes to appropriate model tiers:

| Tier | Use Case | Model Examples | Cost | Latency |
|------|----------|----------------|------|---------|
| **Tier 1: Reasoning** | Complex analysis, multi-step planning, deep research | o3, Claude Opus, Gemini Ultra, Manus Deep Think | $$$ | High |
| **Tier 2: Generation** | Content creation, document drafting, KB generation | GPT-4o, Claude Sonnet, Gemini 2.0 Pro | $$ | Medium |
| **Tier 3: Conversation** | Standard chat, Q&A, simple tasks | GPT-4o-mini, Claude Haiku, Gemini Flash | $ | Low |
| **Tier 4: Classification** | Intent routing, sentiment, simple extraction | Fine-tuned models, embeddings | $ | Very Low |
| **Tier 5: Local** | Privacy-sensitive, offline, cost optimization | Llama 3, Mistral, Phi-3 | $0 | Variable |

### 3.2 Task-to-Tier Mapping

```yaml
task_routing:
  # Discovery Phase
  discovery:
    org_structure_extraction:
      tier: 2
      reasoning: "Requires good comprehension but not deep reasoning"
      fallback_tier: 3

    data_source_detection:
      tier: 3
      reasoning: "Pattern matching, structured extraction"

    template_matching:
      tier: 4
      reasoning: "Classification task"

  # Knowledge Base Generation
  knowledge_base:
    regulatory_synthesis:
      tier: 1
      reasoning: "Complex regulatory interpretation requires deep reasoning"
      required_capabilities: ["long_context", "citation"]

    faq_generation:
      tier: 2
      reasoning: "Content generation with accuracy requirements"

    content_review:
      tier: 1
      reasoning: "Quality assurance requires careful analysis"

  # Agent Runtime
  agent_runtime:
    intent_classification:
      tier: 4
      reasoning: "Fast classification for routing"
      latency_requirement: "<100ms"

    standard_query:
      tier: 3
      reasoning: "Most employee queries are straightforward"

    complex_analysis:
      tier: 2
      reasoning: "Multi-document synthesis, detailed responses"
      escalation_trigger: true

    policy_interpretation:
      tier: 1
      reasoning: "Legal/policy questions require careful reasoning"
      human_review_recommended: true
```

### 3.3 Client Model Configuration

```yaml
# deployments/{org_id}/config/model_preferences.yaml

model_preferences:
  organization_id: "cle-2026"

  tier_assignments:
    tier_1_reasoning:
      primary: "openai/o3"
      fallback: "anthropic/claude-opus-4-5"
      max_tokens: 32000
      temperature: 0.2

    tier_2_generation:
      primary: "openai/gpt-4o"
      fallback: "anthropic/claude-sonnet-4-5"
      max_tokens: 16000
      temperature: 0.4

    tier_3_conversation:
      primary: "openai/gpt-4o-mini"
      fallback: "anthropic/claude-haiku"
      max_tokens: 4000
      temperature: 0.7

    tier_4_classification:
      primary: "openai/gpt-4o-mini"
      fallback: "local/llama-3-8b"
      max_tokens: 500
      temperature: 0

    tier_5_local:
      primary: "local/llama-3-70b"
      fallback: "local/mistral-7b"
      max_tokens: 4000
      temperature: 0.5

  cost_limits:
    daily_budget: 500.00
    per_request_max: 2.00
    alert_threshold: 0.80
```

---

## 4. Prompt Engineering Framework

### 4.1 Base Template Class

```python
class PromptTemplate:
    """
    Base class for aiOS prompt templates.

    Templates are model-agnostic - they define WHAT the model should do,
    not HOW (which varies by model architecture).
    """

    def __init__(
        self,
        template_id: str,
        purpose: str,
        required_context: list[str],
        output_format: str,
        quality_criteria: list[str]
    ):
        self.template_id = template_id
        self.purpose = purpose
        self.required_context = required_context
        self.output_format = output_format
        self.quality_criteria = quality_criteria

    def render(self, context: dict, model_adapter: ModelAdapter) -> str:
        """Render prompt with model-specific optimizations."""
        base_prompt = self._render_base(context)
        return model_adapter.optimize_prompt(base_prompt, self)
```

### 4.2 Key Prompt Templates

- **DiscoveryExtractionPrompt**: Extract organizational structure from web content
- **KnowledgeBaseGenerationPrompt**: Generate KB document content
- **GovernanceJudgePrompt**: Validate AI response against policies

---

## 5. Model-Specific Adapters

### 5.1 Adapter Interface

```python
class ModelAdapter(ABC):
    """Base class for model-specific adapters."""

    @abstractmethod
    def optimize_prompt(self, prompt: str, template: PromptTemplate) -> str:
        """Optimize prompt for this specific model."""
        pass

    @abstractmethod
    async def complete(self, prompt: str, max_tokens: int, temperature: float, **kwargs) -> ModelResponse:
        """Execute completion with this model."""
        pass

    @abstractmethod
    def parse_response(self, response: str, expected_format: str) -> dict:
        """Parse model response into expected format."""
        pass
```

### 5.2 Implemented Adapters

- **OpenAIAdapter**: GPT-4o, o1, o3 (handles reasoning model differences)
- **AnthropicAdapter**: Claude Opus, Sonnet, Haiku
- **LocalModelAdapter**: Ollama, vLLM, LMStudio

---

## 6. Intelligent Model Router

```python
class IntelligentModelRouter:
    """
    Routes requests to the optimal model based on:
    - Task complexity
    - Cost constraints
    - Latency requirements
    - Client preferences
    - Model availability
    """

    async def route(self, task: Task, context: RequestContext) -> RoutingDecision:
        # 1. Determine task tier
        tier = self._classify_task_tier(task)

        # 2. Get client's preferred models for this tier
        preferences = await self._get_client_preferences(context.organization_id, tier)

        # 3. Check cost budget
        budget_status = await self.cost_tracker.check_budget(context.organization_id, ...)

        # 4. Check model availability and performance
        primary_status = await self._check_model_health(preferences.primary)

        # 5. Check latency requirements
        # 6. Return optimal routing decision
```

---

## 7. Cost Optimization

**Target: 40-70% cost reduction vs naive model usage**

Strategies:
1. **Caching**: Cache similar request responses
2. **Tier Downgrading**: Use cheaper models when quality allows
3. **Prompt Compression**: Summarize context before expensive calls
4. **Batching**: Batch similar requests for background tasks

---

## 8. Quality Assurance Layer

```python
class OutputValidator:
    """Validate LLM outputs regardless of source model."""

    async def validate(self, response: ModelResponse, template: PromptTemplate, context: RequestContext) -> ValidationResult:
        # 1. Format validation
        # 2. Quality scoring
        # 3. Completeness check
        # 4. Consistency check

    async def validate_and_retry(self, response, template, context, adapter, max_retries=2) -> ValidatedResponse:
        # Validate and retry with feedback if quality insufficient
```

---

## 9. Philosophy Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                    aiOS GUIDES THE MODEL                                     │
│                    THE MODEL DOESN'T GUIDE aiOS                              │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   aiOS PROVIDES:                                                            │
│   • Prompt Templates (what to do)                                           │
│   • Governance Rules (what NOT to do)                                       │
│   • Quality Criteria (how good it must be)                                  │
│   • Routing Logic (which model to use)                                      │
│   • Output Validation (verify it's correct)                                 │
│   • HITL Checkpoints (humans approve everything)                            │
│                                                                              │
│   LLM PROVIDES:                                                             │
│   • Language Understanding                                                  │
│   • Content Generation                                                      │
│   • Reasoning Capability                                                    │
│   • Knowledge Retrieval                                                     │
│   (These are CAPABILITIES aiOS orchestrates, not DECISIONS)                 │
│                                                                              │
│   HUMAN PROVIDES:                                                           │
│   • Final Approval (nothing deploys without human sign-off)                 │
│   • Quality Verification (SMEs validate AI-generated content)              │
│   • Policy Decisions (governance rules are human-defined)                   │
│   • Edge Case Handling (escalations go to humans)                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

KEY INSIGHT:
- The LLM is a powerful but undirected capability
- aiOS provides the direction, structure, and guardrails
- Humans provide the judgment and accountability
- Together: Governed, reliable, scalable AI services
```

---

**Document Version:** 1.0
**Last Updated:** January 2026
**Next Review:** Upon implementation of Phase 1
