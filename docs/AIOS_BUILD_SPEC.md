# AIOS Build Specification — Source of Truth

> This document contains the original instructions and specifications used to build the AIOS (AI Operating System) governance framework. It serves as the guiding light for all future development.

---

## Table of Contents

1. [Overview & Philosophy](#1-overview--philosophy)
2. [Architecture Principles](#2-architecture-principles)
3. [Mandatory Pipeline](#3-mandatory-pipeline)
4. [HITL Modes](#4-hitl-modes)
5. [Policy-as-Code](#5-policy-as-code)
6. [Module Specifications](#6-module-specifications)
7. [Engineering Quality Rules](#7-engineering-quality-rules)
8. [API Endpoints](#8-api-endpoints)
9. [CGI Compliance Checklist](#9-cgi-compliance-checklist)
10. [Future Milestones](#10-future-milestones)

---

## 1. Overview & Philosophy

AIOS is a **white-label, governed AI Operating System** for safe, scalable AI adoption.

### What AIOS Is NOT
- AIOS is **NOT a chatbot**
- It is an operating system that enforces governance, human-in-the-loop (HITL), auditability, and source-of-truth behavior across all AI interactions

### Core Guarantees
- Policy-as-code governance
- Human-in-the-loop (HITL) modes
- Auditability
- Knowledge citations + source hierarchy
- White-label deployment packs (tenant configs)

---

## 2. Architecture Principles

### Mandatory Capabilities
- Policy-as-code (YAML/JSON) driving Governance decisions
- **Simulation Mode**: runs the same pipeline but NEVER executes tools; produces full audit traces
- **Audit logging**: every request must produce a structured AuditEvent with policy triggers, citations, actions
- Knowledge plane must support citations and source hierarchy
- White-label deployments: NO tenant/client specifics in core code. Use `deployments/*` packs.

### Module Structure
```
packages/core/
├── concierge/      # Intent + risk signals + recommended agent
├── governance/     # Policy evaluation -> HITL mode + constraints
├── schemas/        # Typed data models
├── simulation/     # Batch runner with "no tool execution" guard
├── agents/         # Base agent class + registry (future)
├── router/         # Provider-agnostic LLM interface (future)
├── knowledge/      # Ingestion + retrieval + citations (future)
└── audit/          # Structured logs + persistence (future)
```

---

## 3. Mandatory Pipeline

Every request follows the same pipeline:

```
1) Concierge
   - Input: UserRequest + UserContext
   - Output: Intent + RiskSignals + RecommendedAgentId(s)

2) Governance Kernel
   - Input: Intent + RiskSignals + UserContext + PolicySet
   - Output: GovernanceDecision (HITL mode + constraints + policy triggers)

3) Agent Execution
   - Input: GovernanceDecision + AgentConfig + KnowledgeContext (+ Tools if allowed)
   - Output: AgentResult (response + citations + actions + recommended approvals)

4) Audit
   - Input: full DecisionTrace
   - Output: persisted AuditEvent (structured, queryable)
```

---

## 4. HITL Modes

Human-in-the-loop modes are **non-bypassable**:

| Mode | Description | Tools Allowed |
|------|-------------|---------------|
| **INFORM** | Information only | No |
| **DRAFT** | Drafts content; approval required before external use | No |
| **EXECUTE** | Tools may be allowed; requires role-based authorization | Yes (with auth) |
| **ESCALATE** | No AI action; routed to human queue | No |

---

## 5. Policy-as-Code

### Evaluation Order
1. **Constitutional rules** (immutable, highest priority)
2. **Organization rules** (default)
3. **Department rules** (based on Intent.domain)

Default is safest: **INFORM**

### GovernanceDecision Must Include
- `hitl_mode`
- `tools_allowed`
- `approval_required`
- `escalation_reason` (if any)
- `policy_trigger_ids`
- `provider_constraints` (e.g., local-only)

### Example Policy Structure
```yaml
version: "1.0"

constitutional_rules:
  - id: public_comms_draft
    description: "Public-facing communications must be drafted for approval."
    when:
      any:
        - intent.audience == "public"
        - risk.contains("PUBLIC_STATEMENT")
    then:
      hitl_mode: "DRAFT"
      tools_allowed: false
      approval_required: true

  - id: pii_local_only
    description: "PII triggers local-only provider constraint."
    when:
      any:
        - risk.contains("PII")
    then:
      provider_constraints:
        local_only: true

  - id: contract_interpretation_escalate
    description: "Contract/legal interpretation escalates."
    when:
      any:
        - risk.contains("LEGAL_CONTRACT")
    then:
      hitl_mode: "ESCALATE"
      tools_allowed: false
      approval_required: true

organization_rules:
  default:
    hitl_mode: "INFORM"
    tools_allowed: false
    approval_required: false

department_rules:
  Comms:
    defaults:
      hitl_mode: "DRAFT"
      tools_allowed: false
      approval_required: true
```

---

## 6. Module Specifications

### 6.1 Concierge Module

**Location**: `packages/core/concierge/`

**Functions**:
- `classify_intent(text: str) -> Intent`
- `detect_risks(text: str) -> RiskSignals`

**Intent Output**:
- `domain`: e.g., "HR", "Procurement", "Comms", "Legal", "Finance", "General"
- `task`: e.g., "draft_statement", "contract_review", "answer_question"
- `audience`: "internal" | "public"
- `impact`: "low" | "medium" | "high"
- `confidence`: 0.0 - 1.0

**Risk Signals to Detect**:
- `PII` - Personal identifiable information
- `LEGAL_CONTRACT` - Contract/legal interpretation
- `PUBLIC_STATEMENT` - Public-facing communications
- `FINANCIAL` - Financial transactions/data

### 6.2 Governance Module

**Location**: `packages/core/governance/`

**Functions**:
- `evaluate_governance(intent, risk, ctx, policy_set) -> GovernanceDecision`
- `PolicyLoader.load_from_dict(raw) -> PolicySet`

**Rule Conditions Supported**:
- `risk.contains("X")`
- `intent.domain/task/audience/impact` comparisons
- `ctx.department/role` comparisons

**Precedence**: Constitutional > Organization > Department

### 6.3 Simulation Module

**Location**: `packages/core/simulation/`

**Functions**:
- `SimulationRunner.simulate_single(...) -> SimulationResult`
- `SimulationRunner.simulate_batch(...) -> BatchSimulationResult`

**Guarantees**:
- MUST NEVER execute tools
- Produces full audit traces
- Deterministic outputs for same inputs
- Supports batch evaluation for procurement/security confidence

### 6.4 Schemas Module

**Location**: `packages/core/schemas/models.py`

**Core Models**:
- `HITLMode` - Enum: INFORM, DRAFT, ESCALATE
- `Intent` - Classification result
- `RiskSignals` - Detected risk markers
- `UserContext` - Request metadata (tenant, user, role, department)
- `ProviderConstraints` - AI provider restrictions
- `GovernanceDecision` - Policy enforcement outcome

---

## 7. Engineering Quality Rules

### CGI-Grade Requirements
- ✅ Typed schemas and explicit interfaces for all core objects
- ✅ Unit tests for Governance and Simulation logic
- ✅ No hidden global state; deterministic behavior for simulation
- ✅ Clear separation between core (`packages/core`) and deployments (`deployments/*`)
- ✅ Every security-relevant decision must be explainable and logged
- ✅ mypy strict mode compliance
- ✅ ruff lint compliance
- ✅ >80% test coverage target

### Code Style
- Python 3.11+
- Line length: 100 characters
- Type annotations on all functions
- Pydantic models for data validation
- `from __future__ import annotations` in all files

---

## 8. API Endpoints

### Current Implementation

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/classify` | Intent classification |
| POST | `/risks` | Risk detection |
| POST | `/governance/evaluate` | Full governance evaluation |
| POST | `/policies` | Load policies |
| GET | `/policies` | Get current policies |
| POST | `/simulate` | Single simulation |
| POST | `/simulate/batch` | Batch simulation |

### Running the API
```bash
# Option 1: Using the run script
python run_api.py

# Option 2: Using uvicorn directly
uvicorn packages.api:app --reload --port 8000
```

### OpenAPI Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 9. CGI Compliance Checklist

### Security & Compliance Baseline
- ✅ No secrets in repo (`.env` only)
- ✅ RBAC-ready user context in every request
- ✅ Policy-as-code versioning
- ✅ Audit trail is structured + exportable
- ✅ Simulation mode for procurement/risk confidence
- ✅ Deterministic behavior for tests + demos
- ✅ Vendor-neutral router interface (future)
- ✅ Deployment packs separate tenant logic

### Enterprise Sanity Checks
- [ ] You cannot bypass governance
- [ ] Simulation mode blocks tools
- [ ] Every request produces an audit object
- [ ] Policies load from configuration
- [ ] No tenant-specific hard-coding in core

---

## 10. Future Milestones

### Enterprise Hardening (Next Steps)
1. **Postgres persistence** for audit logs (SQLAlchemy + Alembic migrations)
2. **Auth** (JWT/OIDC integration ready)
3. **Rate limiting** + request size limits
4. **Structured logging** (structlog) + correlation IDs
5. **Router adapters** (Claude/OpenAI/local) with policy-based constraints
6. **Knowledge plane** with citations + hierarchy
7. **Docker Compose** (api + postgres + qdrant)

### Agent Integration (Requires API Keys)
- Claude API integration for intelligent responses
- Agent registry loaded from deployment packs
- Tool execution with governance constraints
- Citation generation from knowledge plane

---

## Appendix A: Original Build Commands

```bash
# Bootstrap the repo
mkdir aios && cd aios
git init

# Create folders
mkdir -p packages/core/{concierge,governance,schemas,simulation}
mkdir -p deployments/default docs infra tests

# Python tooling
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Dependencies
pip install fastapi uvicorn pydantic pydantic-settings python-dotenv \
            sqlalchemy psycopg[binary] alembic \
            structlog httpx tenacity \
            pytest pytest-asyncio ruff mypy

pip freeze > requirements.txt
```

---

## Appendix B: Configuration Files

### pyproject.toml
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E","F","I","B","UP","N","A","C4","SIM","RUF"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_ignores = true
disallow_any_generics = true
no_implicit_optional = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### .gitignore
```
.venv
__pycache__/
*.pyc
.env
.DS_Store
```

---

## Appendix C: Test Commands

```bash
# Run all tests
python -m pytest tests/ -v

# Type checking
python -m mypy packages/ --strict

# Linting
python -m ruff check packages/

# Run API server
python run_api.py
```

---

*Document created: 2026-01-22*
*Last updated: 2026-01-22*
*Version: 1.0.0*
