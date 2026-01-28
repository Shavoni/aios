# aiOS Developer Handoff Document

**Version:** 1.0.0
**Date:** January 2026
**Author:** Claude Code (Opus 4.5)
**Project Lead:** Shavoni, CEO/CTO DEF1LIVE LLC

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Core Modules](#core-modules)
4. [API Reference](#api-reference)
5. [HAAIS Governance Framework](#haais-governance-framework)
6. [Onboarding Pipeline](#onboarding-pipeline)
7. [Platform Adapters](#platform-adapters)
8. [Knowledge Base Generation](#knowledge-base-generation)
9. [Development Setup](#development-setup)
10. [Pending Work](#pending-work)
11. [Testing](#testing)
12. [Deployment](#deployment)

---

## 1. Project Overview

**aiOS (AI Operating System)** is an enterprise platform that automates the discovery, configuration, and deployment of HAAIS-governed AI agents for municipalities. The initial deployment target is the City of Cleveland with 8,000+ city employees.

### What It Does

1. **Auto-Discovery**: Crawls any municipal website to extract organizational structure, departments, executives, and data portals
2. **Knowledge Base Generation**: Creates 15-20 deep knowledge base files per agent with regulatory templates and city-specific content
3. **HAAIS-Compliant Instructions**: Generates agent instructions following the Human Assisted AI Services framework
4. **Multi-Platform Deployment**: Exports agents to Copilot Studio, ChatGPT, Azure OpenAI, N8N, and Vertex AI
5. **Runtime Governance**: Centralized policy control that propagates to all deployed agents instantly

### Key Value Propositions

- **40-70% cost savings** through intelligent LLM routing
- **Zero-hallucination architecture** via knowledge base grounding
- **Policy compliance** through three-tier HAAIS governance
- **Rapid deployment** - onboard any municipality in hours, not months

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React)                          │
│                     localhost:3000 / localhost:3001                 │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                             │
│                         localhost:8000                              │
├─────────────────────────────────────────────────────────────────────┤
│  /agents/*     │  /governance/*  │  /onboarding/*  │  /system/*    │
│  /analytics/*  │  /sessions/*    │  /hitl/*        │  /ask         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │  Agents   │   │Governance │   │ Knowledge │
            │  Manager  │   │  Manager  │   │  Manager  │
            └───────────┘   └───────────┘   └───────────┘
                    │               │               │
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │data/agents│   │data/gov   │   │data/kb    │
            │   .json   │   │policies   │   │ (vector)  │
            └───────────┘   └───────────┘   └───────────┘
```

### Directory Structure

```
aiOS/
├── packages/
│   ├── api/                    # FastAPI endpoints
│   │   ├── __init__.py         # Main app, routers
│   │   ├── agents.py           # Agent CRUD + query
│   │   ├── governance.py       # Governance management
│   │   ├── onboarding.py       # Onboarding endpoints
│   │   ├── analytics.py        # Usage analytics
│   │   ├── sessions.py         # Chat sessions
│   │   ├── hitl.py             # Human-in-the-loop
│   │   └── system.py           # System configuration
│   │
│   ├── core/                   # Core business logic
│   │   ├── agents/             # Agent management
│   │   ├── governance/         # HAAIS governance
│   │   │   ├── __init__.py     # Policy evaluation
│   │   │   └── manager.py      # Centralized manager
│   │   ├── knowledge/          # Knowledge base + RAG
│   │   ├── concierge/          # Intent routing
│   │   ├── router/             # LLM routing
│   │   └── schemas/            # Pydantic models
│   │
│   ├── onboarding/             # Municipal onboarding
│   │   ├── discovery.py        # Website crawling
│   │   ├── catalog.py          # Data portal extraction
│   │   ├── config.py           # Onboarding config
│   │   ├── manifest.py         # Deployment manifests
│   │   ├── deploy.py           # Deployment orchestration
│   │   ├── instruction_builder.py  # HAAIS instructions
│   │   ├── platforms/          # Platform adapters
│   │   │   ├── base.py         # Abstract adapter
│   │   │   ├── copilot.py      # Copilot Studio
│   │   │   ├── chatgpt.py      # ChatGPT/OpenAI
│   │   │   ├── azure.py        # Azure OpenAI
│   │   │   ├── n8n.py          # N8N workflows
│   │   │   └── vertex.py       # Google Vertex AI
│   │   └── kb_generator/       # Knowledge base generation
│   │       ├── generator.py    # Main generator
│   │       ├── templates.py    # Regulatory/domain templates
│   │       └── structures.py   # KB data structures
│   │
│   └── frontend/               # React frontend
│
├── data/                       # Persistent data
│   ├── agents.json             # Agent configurations
│   └── governance_policies.json # Governance rules
│
└── docs/                       # Documentation
```

---

## 3. Core Modules

### 3.1 Agent Manager (`packages/core/agents/`)

Manages the lifecycle of AI agents:

```python
from packages.core.agents import get_agent_manager, AgentConfig

manager = get_agent_manager()

# Create agent
agent = AgentConfig(
    id="public-health",
    name="Public Health Agent",
    domain="Public Health",
    system_prompt="...",
    capabilities=["health inspections", "disease reporting"],
    guardrails=["No medical diagnoses", "Escalate emergencies"],
)
manager.create_agent(agent)

# Query agent (governance is applied automatically)
# See API endpoint: POST /agents/{agent_id}/query
```

### 3.2 Governance Manager (`packages/core/governance/manager.py`)

Centralized governance with three scopes:

```python
from packages.core.governance import get_governance_manager

gov = get_governance_manager()

# Global prohibition (affects ALL agents)
gov.add_prohibited_topic("Park Authority")

# Domain prohibition (affects all agents in domain)
gov.add_domain_prohibition("Public Health", "medical diagnoses")

# Agent prohibition (affects one agent only)
gov.add_agent_prohibition("public-health", "vaccine mandates")

# Evaluate a query
decision = gov.evaluate_for_agent(
    query="Tell me about Park Authority",
    agent_id="public-utilities",
    domain="Public Utilities"
)
# Returns: GovernanceDecision with hitl_mode, escalation_reason, etc.
```

### 3.3 Knowledge Manager (`packages/core/knowledge/`)

Handles document storage and RAG (Retrieval Augmented Generation):

```python
from packages.core.knowledge import get_knowledge_manager

km = get_knowledge_manager()

# Add document
doc = km.add_document(
    agent_id="public-health",
    filename="health_inspection_procedures.md",
    content=b"..."
)

# Query knowledge base (used automatically during agent queries)
results = km.query(agent_id="public-health", query="inspection procedures", n_results=5)
```

### 3.4 Concierge Router (`packages/core/concierge/`)

Routes citizen requests to the appropriate agent:

```python
from packages.core.concierge import route_to_agent

result = route_to_agent("I need to report a pothole on my street")
# Returns: RoutingResult with primary_agent_id, confidence, alternatives
```

---

## 4. API Reference

### Agent Endpoints (`/agents`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agents` | List all agents |
| GET | `/agents/{id}` | Get agent by ID |
| POST | `/agents` | Create new agent |
| PUT | `/agents/{id}` | Update agent |
| DELETE | `/agents/{id}` | Delete agent |
| POST | `/agents/{id}/query` | Query agent with RAG + governance |
| POST | `/agents/{id}/enable` | Enable agent |
| POST | `/agents/{id}/disable` | Disable agent |

### Knowledge Endpoints (`/agents/{id}/knowledge`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agents/{id}/knowledge` | List documents |
| POST | `/agents/{id}/knowledge` | Upload document |
| DELETE | `/agents/{id}/knowledge/{doc_id}` | Delete document |
| GET | `/agents/{id}/knowledge/{doc_id}/download` | Download document |

### Governance Endpoints (`/governance`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/governance/prohibited-topics` | Add prohibition |
| DELETE | `/governance/prohibited-topics` | Remove prohibition |
| GET | `/governance/prohibited-topics` | List all prohibitions |
| POST | `/governance/rules` | Add policy rule |
| DELETE | `/governance/rules/{id}` | Remove rule |
| GET | `/governance/rules` | List all rules |
| POST | `/governance/test` | Test governance evaluation |
| POST | `/governance/reload` | Reload from disk |

### Onboarding Endpoints (`/onboarding`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/onboarding/discover` | Start discovery for municipality |
| GET | `/onboarding/discover/{job_id}` | Get discovery status |
| POST | `/onboarding/catalog/{portal_url}` | Extract data catalog |
| POST | `/onboarding/manifest` | Generate deployment manifest |
| POST | `/onboarding/deploy` | Start deployment |
| GET | `/onboarding/deploy/{job_id}` | Get deployment status |
| POST | `/onboarding/generate-kb` | Generate knowledge base |
| POST | `/onboarding/generate-instructions` | Generate instructions |
| POST | `/onboarding/generate-platform` | Generate for platform |
| GET | `/onboarding/platforms` | List available platforms |
| POST | `/onboarding/compare-platforms` | Compare platform outputs |

---

## 5. HAAIS Governance Framework

### Three Pillars

1. **Human Governance**: Humans set policies, AI executes within bounds
2. **Assistance not Automation**: AI assists decisions, doesn't make them
3. **Services not Tools**: AI provides services with accountability

### Three Tiers

| Tier | Name | Priority | Scope |
|------|------|----------|-------|
| 1 | Constitutional | Highest | Foundational principles |
| 2 | Organizational | Medium | Organization-wide policies |
| 3 | Operational | Lowest | Department-specific rules |

### HITL Modes

| Mode | Behavior |
|------|----------|
| INFORM | Agent responds directly |
| DRAFT | Response requires human review before delivery |
| ESCALATE | Request escalated to human, agent cannot respond |

### Policy Rules Structure

```json
{
  "id": "const-001",
  "name": "PII Protection",
  "conditions": [
    {"field": "risk.contains", "operator": "eq", "value": "PII"}
  ],
  "action": {
    "hitl_mode": "ESCALATE",
    "escalation_reason": "Request involves PII"
  },
  "priority": 100
}
```

### Risk Signals

Automatically detected in queries:
- `PII` - Social security, credit cards, passwords
- `FINANCIAL` - Salary, budget, contracts
- `LEGAL` - Lawsuits, attorney matters
- `PERSONNEL` - Terminations, performance reviews

---

## 6. Onboarding Pipeline

### Step 1: Discovery

```python
from packages.onboarding import DiscoveryEngine

engine = DiscoveryEngine()
result = await engine.discover("https://clevelandohio.gov")

# Returns:
# - departments: List of discovered departments
# - executives: Mayor, directors, etc.
# - data_portals: Open data portal URLs
# - org_structure: Hierarchical structure
```

### Step 2: Catalog Extraction

```python
from packages.onboarding import CatalogExtractor

extractor = CatalogExtractor()
catalog = await extractor.extract("https://data.clevelandohio.gov")

# Returns datasets with metadata, update frequencies, formats
```

### Step 3: Knowledge Base Generation

```python
from packages.onboarding import generate_knowledge_base, GeneratorConfig

config = GeneratorConfig(
    municipality_name="City of Cleveland",
    domain="public_health",
    director_name="Dr. David Margolius",
    director_title="Director of Public Health",
)

kb = generate_knowledge_base(config)
# Returns 15-20 structured markdown files
```

### Step 4: Instruction Building

```python
from packages.onboarding import build_instructions, InstructionConfig

config = InstructionConfig(
    agent_name="Cleveland Public Health Agent",
    domain="Public Health",
    knowledge_base=kb,
    platform="copilot",  # Adapts to platform constraints
)

instructions = build_instructions(config)
# Returns HAAIS-compliant 8-section instruction document
```

### Step 5: Platform Export

```python
from packages.onboarding import generate_for_platform

output = generate_for_platform(
    platform="copilot",
    instructions=instructions,
    knowledge_base=kb,
)

# Returns platform-specific deployment package
```

---

## 7. Platform Adapters

### Supported Platforms

| Platform | Constraint | Primary Use |
|----------|-----------|-------------|
| Copilot Studio | 6K chars | Cleveland M365 deployment |
| ChatGPT | 8K chars | Custom GPT marketplace |
| Azure OpenAI | 256K tokens | Enterprise deployments |
| N8N | 32K chars | Workflow automation |
| Vertex AI | 8K chars | Google Cloud deployments |

### Adapter Interface

```python
from packages.onboarding.platforms import PlatformAdapter

class CopilotAdapter(PlatformAdapter):
    def adapt_instructions(self, instructions: str) -> str:
        # Compress to fit 6K limit

    def format_knowledge_base(self, kb: KnowledgeBase) -> dict:
        # Format for Copilot dataverse

    def generate_deployment_package(self) -> AgentOutput:
        # Create deployment-ready package
```

---

## 8. Knowledge Base Generation

### File Structure (per agent)

Each agent gets 15-20 files organized as:

```
agent_knowledge_base/
├── 00_GOVERNANCE_AND_COMPLIANCE.md       # HAAIS governance
├── 01_REGULATORY_hipaa_compliance.md     # Regulatory quick refs
├── 01_REGULATORY_cdc_guidelines.md
├── 02_DEPARTMENT_overview.md             # Domain files
├── 03_PROCEDURES_inspections.md
├── 04_POLICIES_reporting.md
├── 05_FORMS_applications.md
├── 06_CONTACTS_directory.md
├── 07_FAQS_common_questions.md
├── 08_EMERGENCY_protocols.md
├── 09_RESOURCES_external.md
├── 10_TRAINING_materials.md
├── 11_METRICS_performance.md
├── 12_UPDATES_recent_changes.md
└── ... (additional domain-specific files)
```

### KB File Format

```markdown
# [Title]

**Version:** 1.0 | **Classification:** INTERNAL | **HAAIS Tier:** Tier 2

## PURPOSE
[Why this document exists]

## APPLICABILITY
[Who/what this applies to]

## CONTENT
[Main content organized by sections]

## RELATED FILES
- [Cross-references to other KB files]

## ESCALATION CONTACTS
- [Human contacts for escalation]

---
*HAAIS Classification: Tier 2 - Organizational | Last Updated: [Date]*
```

---

## 9. Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- Git

### Installation

```bash
# Clone repository
git clone https://github.com/def1live/aiOS.git
cd aiOS

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd packages/frontend
npm install
cd ../..

# Set environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Running

```bash
# Start backend
uvicorn packages.api:app --reload --port 8000

# Start frontend (separate terminal)
cd packages/frontend
npm run dev
```

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional
OPENAI_API_KEY=sk-...
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_KEY=...
```

---

## 10. Pending Work

> **Reference:** See `docs/IMPLEMENTATION_STATUS.md` for detailed roadmap alignment
> **Reference:** See `docs/AIOS_TECHNICAL_ROADMAP.md` for full architecture spec

### Roadmap Phase 1: Foundation (HIGH PRIORITY)

1. **LLM-Powered Discovery Agent**
   - Location: `packages/core/discovery/discovery_agent.py` (CREATE)
   - Current: Rule-based extraction in `packages/onboarding/discovery.py`
   - Needed: LLM semantic parsing, confidence scores per extraction
   - Output: `OrganizationProfile` JSON matching roadmap spec

2. **Template Matcher**
   - Location: `packages/core/discovery/template_matcher.py` (CREATE)
   - Task: Fuzzy matching of discovered departments to templates
   - Algorithm: Similarity scoring on name, roles, responsibilities
   - Output: Top-3 matches with confidence and reasoning

3. **HITL Customization Endpoints**
   - Location: `packages/api/onboarding.py`
   - Add: `POST /discover/{id}/customize`
   - Add: `GET /discover/{id}/preview`
   - Add: `POST /discover/{id}/approve-and-deploy`

4. **HITL Checklist UI**
   - Location: `packages/frontend/`
   - React component for interactive approval workflow
   - Show discovered structure with confidence indicators
   - Allow add/remove/rename of departments and agents

### Roadmap Phase 2: Auto-Generation (MEDIUM PRIORITY)

5. **Deployment Package Structure**
   - Create `deployments/{org_id}/` directory hierarchy
   - Generate: `manifest/`, `policies/`, `knowledge/`, `auth/`
   - Follow roadmap spec for file structure

6. **YAML Policy Generation**
   - Convert JSON policies to YAML format
   - Generate: `constitutional.yaml`, `department_defaults.yaml`, `sensitivity_tiers.yaml`

7. **Department Registry**
   - Create hierarchical `departments.json`
   - Include parent/child relationships
   - Support multi-level org structures

### Roadmap Phase 3: Enterprise Integration (MEDIUM PRIORITY)

8. **Multi-Tenant Isolation**
   - Add `org_id` and `tenant_id` to all queries
   - Scope knowledge bases per tenant
   - Isolate governance policies per organization

9. **Azure Provisioning Automation**
   - Auto-create Azure OpenAI resources
   - Generate service accounts
   - Configure API keys per deployment

10. **Training Material Generation**
    - Auto-generate onboarding documentation
    - Create admin dashboard templates
    - Generate user guides per department

### Roadmap Phase 4: Polish & Scale (LOWER PRIORITY)

11. **Performance Optimization**
    - Discovery caching
    - Parallel KB generation
    - Batch API operations

12. **Security Audit**
    - Penetration testing
    - OWASP compliance check
    - Data encryption at rest

13. **Customer Pilot Program**
    - Cleveland deployment validation
    - Feedback collection system
    - Iterative improvements

### Supporting Work

14. **Audit Logging**
    - Log all governance decisions
    - Track policy changes with timestamps
    - Discovery decision audit trail

15. **Analytics Dashboard**
    - Query volume by agent
    - Governance trigger frequency
    - Cost tracking per department

---

## 11. Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=packages --cov-report=html

# Run specific module
pytest packages/core/governance/test_manager.py
```

### Test Categories

| Category | Location | Purpose |
|----------|----------|---------|
| Unit | `tests/unit/` | Individual function tests |
| Integration | `tests/integration/` | API endpoint tests |
| E2E | `tests/e2e/` | Full workflow tests |

### Key Test Scenarios

1. **Governance Tests**
   - Prohibited topic blocking (global, domain, agent)
   - HITL mode escalation
   - Policy rule evaluation

2. **Agent Tests**
   - CRUD operations
   - Query with RAG
   - Knowledge base operations

3. **Onboarding Tests**
   - Discovery parsing
   - KB generation completeness
   - Platform export validation

---

## 12. Deployment

### Production Checklist

- [ ] Set production environment variables
- [ ] Configure CORS for production domains
- [ ] Enable HTTPS
- [ ] Set up database backups (if using persistent DB)
- [ ] Configure logging to external service
- [ ] Set up monitoring/alerting
- [ ] Review and test governance policies
- [ ] Validate all agent knowledge bases

### Docker Deployment

```dockerfile
# Dockerfile example
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY packages/ packages/
COPY data/ data/

EXPOSE 8000
CMD ["uvicorn", "packages.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Cloud Deployment Options

| Provider | Service | Notes |
|----------|---------|-------|
| AWS | ECS/Fargate | Recommended for production |
| Azure | Container Apps | Good for M365 integration |
| GCP | Cloud Run | Auto-scaling support |

---

## Contact

- **Project Lead**: Shavoni (CEO/CTO DEF1LIVE LLC)
- **Repository**: Internal GitHub
- **Documentation**: `/docs` directory

---

*This document was generated as part of the aiOS development handoff. Last updated: January 2026.*
