# aiOS Routing Architecture Specification

> **Document Purpose**: Professional handoff document for understanding and fixing the routing system
> **Last Audit**: 2026-01-30
> **Status**: PARTIALLY FIXED - See status updates below

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Current State Analysis](#2-current-state-analysis)
3. [Critical Issues & Fixes Required](#3-critical-issues--fixes-required)
4. [Domain Mapping Specification](#4-domain-mapping-specification)
5. [Agent Configuration Reference](#5-agent-configuration-reference)
6. [API Endpoint Routing](#6-api-endpoint-routing)
7. [Governance Integration](#7-governance-integration)
8. [Implementation Tasks](#8-implementation-tasks)

---

## 1. Architecture Overview

### Two-Tier Routing System

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                                 │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    TIER 1: LLM PROVIDER ROUTER                       │
│                    packages/core/router/__init__.py                  │
│                                                                      │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│   │   Claude    │    │   OpenAI    │    │  Local LLM  │            │
│   │  (Default)  │    │   (GPT-4o)  │    │  (Fallback) │            │
│   └─────────────┘    └─────────────┘    └─────────────┘            │
│                                                                      │
│   Selection Logic:                                                   │
│   - settings.llm_provider == "openai" → OpenAI                      │
│   - governance.local_only == true → Block external                  │
│   - No API key → Rule-based fallback                                │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    TIER 2: CONCIERGE ROUTER                          │
│                    packages/core/concierge/classifier.py             │
│                                                                      │
│   Intent Classification → Domain Assignment → Agent Selection        │
│                                                                      │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│   │  Comms   │   │  Legal   │   │    HR    │   │ Finance  │        │
│   └──────────┘   └──────────┘   └──────────┘   └──────────┘        │
│        │              │              │              │                │
│        ▼              ▼              ▼              ▼                │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│   │   ???    │   │   ???    │   │    hr    │   │ finance  │        │
│   │ (BROKEN) │   │ (BROKEN) │   │  agent   │   │  agent   │        │
│   └──────────┘   └──────────┘   └──────────┘   └──────────┘        │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    GOVERNANCE LAYER                                  │
│                    packages/core/governance/__init__.py              │
│                                                                      │
│   HITL Modes:                                                        │
│   - INFORM (0): Default, no approval needed                         │
│   - DRAFT (1): Response requires approval before sending            │
│   - ESCALATE (2): Human review required, blocks response            │
│                                                                      │
│   Provider Constraints:                                              │
│   - local_only: Block all external LLM providers                    │
│   - allowed_providers: Whitelist                                    │
│   - blocked_providers: Blacklist                                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Current State Analysis

### 2.1 Intent Classifier (WORKING)

**File**: `packages/core/concierge/classifier.py`

| Domain | Pattern Triggers (Lines 34-92) | Confidence Scoring |
|--------|-------------------------------|-------------------|
| Comms | "public statement", "press release", "public announcement" | Pattern: +0.4, Keyword: +0.15 |
| Legal | "contract review", "NDA", "agreement", "legal review" | Pattern: +0.4, Keyword: +0.15 |
| HR | "employee info", "employee lookup" | Pattern: +0.4, Keyword: +0.15 |
| Finance | "financial report", "quarterly report" | Pattern: +0.4, Keyword: +0.15 |
| General | Default fallback | When all scores < 0.2 |

### 2.2 Risk Detector (WORKING)

**File**: `packages/core/concierge/classifier.py` (Lines 95-132)

| Signal | Triggers |
|--------|----------|
| PII | SSN, address, salary, personal info |
| LEGAL_CONTRACT | NDA, contract, agreement |
| PUBLIC_STATEMENT | Public statements, press releases |
| FINANCIAL | Wire transfers, payments, invoices |

### 2.3 Agent Configuration (WORKING)

**File**: `data/agents.json`

| Agent ID | Domain | Status | Real Person |
|----------|--------|--------|-------------|
| concierge | Router | active | Cleveland Civic AI Concierge |
| hr | HR | active | Matthew J. Cole |
| finance | Finance | active | Ayesha Bell Hardaway |
| building | Building | active | Sally Martin O'Toole |
| 311 | 311 | active | Kate Connor Warren |
| public-health | PublicHealth | active | Dr. David Margolius |
| gcp | Regional | active | Freddy Collier |
| public-safety | PublicSafety | active | Chief of Police |
| strategy | Strategy | inactive | Dr. Elizabeth Crowe, PhD |

### 2.4 Simulation Agent Map (BROKEN)

**File**: `packages/core/simulation/__init__.py` (Lines 20-26)

```python
# CURRENT (BROKEN) - References non-existent agents
AGENT_MAP = {
    "Comms": "communications_agent",      # DOES NOT EXIST
    "Legal": "legal_agent",               # DOES NOT EXIST
    "HR": "hr_agent",                     # WRONG ID (should be "hr")
    "Finance": "finance_agent",           # WRONG ID (should be "finance")
    "General": "research_agent",          # DOES NOT EXIST
}
```

---

## 3. Critical Issues & Fixes Required

### ISSUE #1: Agent Map Mismatch [RESOLVED]

**Problem**: `AGENT_MAP` in simulation module references agents that don't exist.

**Location**: `packages/core/simulation/__init__.py:20-26`

**Status**: ✅ FIXED - Agent map now uses correct agent IDs

**Fix Required**:
```python
# CORRECTED AGENT_MAP
AGENT_MAP = {
    "Comms": "311",              # 311 handles public communications
    "Legal": "concierge",        # No dedicated legal agent - escalate to concierge
    "HR": "hr",                  # Correct agent ID
    "Finance": "finance",        # Correct agent ID
    "General": "concierge",      # Concierge handles general queries
    "PublicHealth": "public-health",
    "Building": "building",
    "PublicSafety": "public-safety",
    "Regional": "gcp",
}
```

**Alternative Fix**: Auto-generate from agents.json:
```python
def get_agent_map() -> dict[str, str]:
    """Generate agent map dynamically from configuration."""
    from packages.core.agents import AgentManager
    manager = AgentManager()
    return {
        agent.domain: agent.id
        for agent in manager.list_agents()
        if not agent.is_router
    }
```

---

### ISSUE #2: No Agent Selection in /ask Endpoint [HIGH PRIORITY]

**Problem**: The `/ask` endpoint classifies intent and applies governance but never routes to an agent.

**Location**: `packages/api/__init__.py:288-335`

**Current Flow**:
1. Classify intent ✓
2. Detect risks ✓
3. Evaluate governance ✓
4. Generate response ✓
5. Select and route to agent ✗ MISSING

**Fix Required**: Add agent selection logic after governance evaluation:

```python
# After line 320, add:
from packages.core.agents import AgentManager

agent_manager = AgentManager()
selected_agent = None

# Map intent domain to agent
domain_to_agent = {
    "Comms": "311",
    "Legal": "concierge",  # Escalate - no dedicated legal
    "HR": "hr",
    "Finance": "finance",
    "General": "concierge",
}

agent_id = domain_to_agent.get(intent.domain, "concierge")
selected_agent = agent_manager.get_agent(agent_id)

# Include in response
return AskResponse(
    response=result.get("text", ""),
    intent=intent,
    risk_signals=risks,
    hitl_mode=governance.hitl_mode.value,
    requires_approval=governance.approval_required,
    model_used=result.get("model", "rule-based"),
    governance_triggers=governance.policy_trigger_ids,
    routed_to_agent=agent_id,  # NEW FIELD
    agent_name=selected_agent.name if selected_agent else None,  # NEW FIELD
)
```

---

### ISSUE #3: Governance Not Applied to Agent Queries [MEDIUM PRIORITY]

**Problem**: Direct agent queries bypass governance evaluation.

**Location**: `packages/api/agents.py:371`

```python
# Current code (line 371)
return AgentQueryResponse(
    ...
    hitl_mode="INFORM",  # TODO: Apply governance  <-- THIS TODO
)
```

**Fix Required**:
```python
# Before building response, evaluate governance
from packages.core.governance import GovernanceEngine

governance_engine = GovernanceEngine()
user_context = UserContext(
    department=request.department or "unknown",
    role=request.role or "employee",
    clearance_level=request.clearance_level or "standard"
)

# Classify the query intent
intent = classify_intent(request.query)
risks = detect_risks(request.query)

governance = governance_engine.evaluate(
    intent=intent,
    risk_signals=risks,
    user=user_context
)

# Apply governance to response
if governance.hitl_mode.value == "ESCALATE":
    return AgentQueryResponse(
        agent_id=agent_id,
        response="[ESCALATED] This query requires human review.",
        sources=[],
        hitl_mode="ESCALATE",
        escalation_reason=governance.escalation_reason
    )
```

---

### ISSUE #4: Intent Domains Don't Match Agent Domains [MEDIUM PRIORITY]

**Problem**: Intent classifier outputs different domain names than agents use.

**Classifier Domains** (classifier.py):
- Comms, Legal, HR, Finance, General

**Agent Domains** (agents.json):
- HR, Finance, Building, 311, PublicHealth, PublicSafety, Regional, Strategy, Router

**Fix Options**:

**Option A**: Expand classifier to recognize all agent domains
```python
# Add to INTENT_PATTERNS in classifier.py
INTENT_PATTERNS = {
    ...
    "Building": [
        r"building\s*permit",
        r"construction",
        r"zoning",
        r"property\s*inspection",
    ],
    "311": [
        r"report\s*(a\s*)?(pothole|issue|problem)",
        r"city\s*service",
        r"trash|garbage|recycling",
        r"street\s*light",
    ],
    "PublicHealth": [
        r"health\s*(department|inspection)",
        r"vaccination",
        r"disease|outbreak",
        r"restaurant\s*inspection",
    ],
    "PublicSafety": [
        r"police|fire|emergency",
        r"safety\s*concern",
        r"crime\s*report",
    ],
}
```

**Option B**: Create a domain mapping layer (recommended)
```python
# New file: packages/core/routing/domain_mapper.py

INTENT_TO_AGENT_DOMAIN = {
    # Classifier outputs → Agent domains
    "Comms": "311",
    "Legal": "Router",  # Escalate to Concierge
    "HR": "HR",
    "Finance": "Finance",
    "General": "Router",

    # Direct mappings (if classifier expanded)
    "Building": "Building",
    "311": "311",
    "PublicHealth": "PublicHealth",
    "PublicSafety": "PublicSafety",
    "Regional": "Regional",
}

def map_intent_to_agent(intent_domain: str) -> str:
    """Map classifier intent domain to agent ID."""
    agent_domain = INTENT_TO_AGENT_DOMAIN.get(intent_domain, "Router")

    from packages.core.agents import AgentManager
    manager = AgentManager()

    for agent in manager.list_agents():
        if agent.domain == agent_domain and not agent.is_router:
            return agent.id

    # Fallback to concierge
    return "concierge"
```

---

## 4. Domain Mapping Specification

### Complete Domain → Agent Mapping

| User Intent | Classifier Domain | Agent Domain | Agent ID | Handler |
|-------------|-------------------|--------------|----------|---------|
| Public statements, press releases | Comms | 311 | 311 | Kate Connor Warren |
| Contract review, NDAs | Legal | Router | concierge | Concierge (escalate) |
| Employee info, benefits | HR | HR | hr | Matthew J. Cole |
| Financial reports, budgets | Finance | Finance | finance | Ayesha Bell Hardaway |
| Building permits, zoning | Building | Building | building | Sally Martin O'Toole |
| Potholes, city services | 311 | 311 | 311 | Kate Connor Warren |
| Health inspections, vaccinations | PublicHealth | PublicHealth | public-health | Dr. David Margolius |
| Police, fire, emergencies | PublicSafety | PublicSafety | public-safety | Chief of Police |
| Regional planning | Regional | Regional | gcp | Freddy Collier |
| General questions | General | Router | concierge | Concierge |

### Routing Decision Tree

```
User Query
    │
    ├─► Contains "permit", "zoning", "construction"?
    │       └─► Route to: building
    │
    ├─► Contains "pothole", "trash", "street light"?
    │       └─► Route to: 311
    │
    ├─► Contains "employee", "benefits", "HR"?
    │       └─► Route to: hr
    │
    ├─► Contains "budget", "financial", "invoice"?
    │       └─► Route to: finance
    │
    ├─► Contains "health", "vaccination", "inspection"?
    │       └─► Route to: public-health
    │
    ├─► Contains "police", "fire", "emergency"?
    │       └─► Route to: public-safety
    │
    ├─► Contains "regional", "planning", "development"?
    │       └─► Route to: gcp
    │
    ├─► Contains "contract", "NDA", "legal"?
    │       └─► Route to: concierge (ESCALATE - no legal agent)
    │
    └─► Default
            └─► Route to: concierge
```

---

## 5. Agent Configuration Reference

### Agent Schema

```json
{
  "id": "string (unique identifier)",
  "name": "string (display name)",
  "department": "string (city department)",
  "domain": "string (routing domain)",
  "title": "string (job title)",
  "description": "string (agent description)",
  "system_prompt": "string (AI instructions)",
  "is_router": "boolean (true for concierge only)",
  "status": "string (active|inactive)",
  "escalation_path": "string (who to escalate to)",
  "knowledge_sources": ["array of knowledge doc IDs"]
}
```

### Adding New Agents Checklist

1. Add agent entry to `data/agents.json`
2. Update `INTENT_PATTERNS` in `packages/core/concierge/classifier.py`
3. Update domain mapping in routing layer
4. Regenerate Concierge system prompt via `/system/regenerate-concierge`
5. Add integration tests for new routing path

---

## 6. API Endpoint Routing

### Request Flow

```
POST /ask
    │
    ├─► packages/api/__init__.py:288-335
    │       │
    │       ├─► classify_intent() → Intent
    │       ├─► detect_risks() → list[str]
    │       ├─► governance.evaluate() → GovernanceDecision
    │       ├─► [MISSING] select_agent() → Agent
    │       └─► router.generate_response() → Response
    │
    └─► Returns: AskResponse

POST /agents/{agent_id}/query
    │
    ├─► packages/api/agents.py:307-372
    │       │
    │       ├─► Get agent by ID
    │       ├─► Retrieve knowledge documents
    │       ├─► Build augmented prompt
    │       ├─► [MISSING] governance.evaluate()
    │       └─► LLM query with RAG context
    │
    └─► Returns: AgentQueryResponse
```

### Endpoint Reference

| Endpoint | Method | Purpose | File:Lines |
|----------|--------|---------|------------|
| `/ask` | POST | Full routing pipeline | `__init__.py:288-335` |
| `/classify` | POST | Intent only | `__init__.py:179-185` |
| `/risks` | POST | Risk detection only | `__init__.py:188-194` |
| `/governance/evaluate` | POST | Governance only | `__init__.py:202-217` |
| `/agents` | GET | List all agents | `agents.py:106-111` |
| `/agents/{id}` | GET | Get single agent | `agents.py:114-124` |
| `/agents/{id}/query` | POST | Query with RAG | `agents.py:307-372` |

---

## 7. Governance Integration

### Policy Evaluation Priority

1. **Constitutional Rules** (+10000 priority)
   - Cannot be overridden
   - Apply to all requests

2. **Organization Rules** (+5000 priority)
   - City-wide policies
   - Department can't override

3. **Department Rules** (custom priority)
   - Department-specific policies
   - Lowest priority

### HITL Mode Triggers

| Trigger | Risk Signal | HITL Mode | Action |
|---------|-------------|-----------|--------|
| Public statement | PUBLIC_STATEMENT | DRAFT | Require approval |
| Legal contract | LEGAL_CONTRACT | ESCALATE | Human review |
| PII request | PII | ESCALATE + local_only | Block external, review |
| Financial > $10k | FINANCIAL | DRAFT | Require approval |

### Provider Constraints

```python
class ProviderConstraints:
    local_only: bool = False      # Block external LLMs
    allowed_providers: list[str]  # Whitelist
    blocked_providers: list[str]  # Blacklist
```

---

## 8. Implementation Tasks

### Phase 1: Critical Fixes (Blocking)

- [ ] **Task 1.1**: Fix AGENT_MAP in `packages/core/simulation/__init__.py`
  - Update hardcoded map to match actual agent IDs
  - Add unit test to verify map matches agents.json

- [ ] **Task 1.2**: Add agent selection to `/ask` endpoint
  - Create domain mapper utility
  - Integrate into ask endpoint
  - Add `routed_to_agent` field to AskResponse

- [ ] **Task 1.3**: Apply governance to agent queries
  - Remove TODO comment
  - Implement governance evaluation
  - Handle ESCALATE mode properly

### Phase 2: Domain Expansion (Enhancement)

- [ ] **Task 2.1**: Expand intent classifier patterns
  - Add Building, 311, PublicHealth, PublicSafety, Regional patterns
  - Update scoring weights
  - Add integration tests

- [ ] **Task 2.2**: Create domain mapping module
  - New file: `packages/core/routing/domain_mapper.py`
  - Centralize all domain → agent mappings
  - Add validation that all domains have agents

### Phase 3: Documentation (Maintenance)

- [ ] **Task 3.1**: Generate API documentation
  - OpenAPI spec for all endpoints
  - Request/response examples

- [ ] **Task 3.2**: Create routing flowchart
  - Visual decision tree
  - Mermaid diagram for README

- [ ] **Task 3.3**: Write governance policy guide
  - Policy format specification
  - Example policies for common scenarios

---

## Appendix: File Reference

| Purpose | File Path | Key Lines |
|---------|-----------|-----------|
| Intent Classification | `packages/core/concierge/classifier.py` | 34-92, 168-182 |
| Risk Detection | `packages/core/concierge/classifier.py` | 95-132, 191-213 |
| Agent Manager | `packages/core/agents/__init__.py` | 185-235 |
| LLM Router | `packages/core/router/__init__.py` | 49-53, 59-89 |
| Governance Engine | `packages/core/governance/__init__.py` | 79-83, 156-191 |
| Simulation | `packages/core/simulation/__init__.py` | 20-26, 73 |
| Main API | `packages/api/__init__.py` | 288-335 |
| Agents API | `packages/api/agents.py` | 307-372 |
| System API | `packages/api/system.py` | 32-112 |
| Agent Config | `data/agents.json` | Full file |

---

*Document generated by Claude Code audit on 2026-01-25*
