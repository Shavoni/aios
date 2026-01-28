# aiOS Documentation Index

> **Project**: Cleveland Civic AI Gateway (aiOS)
> **Owner**: DEF1LIVE LLC / Shavoni
> **Target**: 8,000 City of Cleveland employees
> **Status**: Active Development

---

## Quick Start for New Claude Code Sessions

**Read these documents in order**:

1. **[ROUTING_ARCHITECTURE.md](./ROUTING_ARCHITECTURE.md)** - Core routing system, critical issues, and fixes required
2. **[DEPLOYMENT_TEMPLATES.md](./DEPLOYMENT_TEMPLATES.md)** - Multi-tenant deployment, reset, and cloning
3. **[UI_DEVELOPMENT_GUIDE.md](./UI_DEVELOPMENT_GUIDE.md)** - Frontend development and UI customization guide

**For questions about UI capabilities**:
- **[QUICK_START_UI.md](./QUICK_START_UI.md)** - Quick answer: "Can AIOS help me build professional UIs?"

---

## System Overview

```
aiOS (Cleveland Civic AI Gateway)
│
├── packages/
│   ├── api/                 # FastAPI endpoints
│   │   ├── __init__.py      # Main API (/ask, /classify, /risks)
│   │   ├── agents.py        # Agent CRUD & query endpoints
│   │   └── system.py        # System management endpoints
│   │
│   ├── core/
│   │   ├── agents/          # Agent management
│   │   ├── concierge/       # Intent classification & routing
│   │   ├── governance/      # Policy evaluation engine
│   │   ├── router/          # LLM provider routing
│   │   └── simulation/      # Testing & simulation
│   │
│   └── kb/                  # Knowledge base (deleted - needs rebuild)
│
├── data/
│   └── agents.json          # Agent configurations (9 agents)
│
├── tests/                   # Test suite
│
└── docs/                    # This documentation
```

---

## Critical Issues (Action Required)

| Priority | Issue | Location | Doc Reference |
|----------|-------|----------|---------------|
| HIGH | AGENT_MAP references non-existent agents | `simulation/__init__.py:20-26` | [ROUTING_ARCHITECTURE.md#issue-1](./ROUTING_ARCHITECTURE.md#issue-1-agent-map-mismatch-high-priority) |
| HIGH | `/ask` endpoint never routes to agents | `api/__init__.py:288-335` | [ROUTING_ARCHITECTURE.md#issue-2](./ROUTING_ARCHITECTURE.md#issue-2-no-agent-selection-in-ask-endpoint-high-priority) |
| MEDIUM | Governance skipped in agent queries | `api/agents.py:371` | [ROUTING_ARCHITECTURE.md#issue-3](./ROUTING_ARCHITECTURE.md#issue-3-governance-not-applied-to-agent-queries-medium-priority) |
| MEDIUM | Intent domains don't match agent domains | classifier.py vs agents.json | [ROUTING_ARCHITECTURE.md#issue-4](./ROUTING_ARCHITECTURE.md#issue-4-intent-domains-dont-match-agent-domains-medium-priority) |

---

## Key Files Reference

### Configuration
| File | Purpose |
|------|---------|
| `data/agents.json` | All 9 agent definitions |
| `config/environment.json` | Instance settings (to be created) |
| `config/branding.json` | UI/branding (to be created) |

### Core Logic
| File | Purpose | Key Lines |
|------|---------|-----------|
| `packages/core/concierge/classifier.py` | Intent classification | 34-92 (patterns), 168-182 (scoring) |
| `packages/core/governance/__init__.py` | Policy evaluation | 156-191 |
| `packages/core/router/__init__.py` | LLM provider routing | 49-53 |
| `packages/core/agents/__init__.py` | Agent management | 185-235 |

### API Endpoints
| File | Purpose | Key Lines |
|------|---------|-----------|
| `packages/api/__init__.py` | Main API | 288-335 (/ask) |
| `packages/api/agents.py` | Agent API | 307-372 (/agents/{id}/query) |
| `packages/api/system.py` | System API | 32-112 (concierge generation) |

---

## Configured Agents

| ID | Name | Domain | Status |
|----|------|--------|--------|
| concierge | Cleveland Civic AI Concierge | Router | active |
| hr | Matthew J. Cole | HR | active |
| finance | Ayesha Bell Hardaway | Finance | active |
| building | Sally Martin O'Toole | Building | active |
| 311 | Kate Connor Warren | 311 | active |
| public-health | Dr. David Margolius | PublicHealth | active |
| public-safety | Chief of Police | PublicSafety | active |
| gcp | Freddy Collier | Regional | active |
| strategy | Dr. Elizabeth Crowe, PhD | Strategy | inactive |

---

## Implementation Roadmap

### Phase 1: Fix Critical Routing Issues
- [ ] Fix AGENT_MAP in simulation module
- [ ] Add agent selection to /ask endpoint
- [ ] Apply governance to agent queries
- [ ] Map intent domains to agent domains

### Phase 2: Template System
- [ ] Create template directory structure
- [ ] Implement export/import functionality
- [ ] Build CLI tools

### Phase 3: Multi-Tenant Support
- [ ] Create TenantContext class
- [ ] Add tenant middleware
- [ ] Update endpoints for tenant awareness

### Phase 4: Knowledge Base Rebuild
- [ ] Rebuild kb package (was deleted)
- [ ] Implement document ingestion
- [ ] Add RAG query system

---

## Commands for Common Tasks

```bash
# Start the API server
uvicorn packages.api:app --reload

# Run tests
pytest tests/

# Export current state as template (to be implemented)
python -m aios template export --name "cleveland-v1"

# Reset to clean state (to be implemented)
python -m aios reset --full --confirm

# Initialize for new city (to be implemented)
python -m aios init --template generic-city
```

---

## Documentation Library

### Getting Started
- **[README.md](../README.md)** - Project overview and quick start
- **[UI_DEVELOPMENT_GUIDE.md](./UI_DEVELOPMENT_GUIDE.md)** - Frontend development, component library, and customization

### Architecture & Design
- **[HAAIS_AIOS_OVERVIEW.md](./HAAIS_AIOS_OVERVIEW.md)** - High-level system overview
- **[ROUTING_ARCHITECTURE.md](./ROUTING_ARCHITECTURE.md)** - Core routing system and critical issues
- **[GOVERNANCE_ARCHITECTURE.md](./GOVERNANCE_ARCHITECTURE.md)** - Governance system review and gaps analysis
- **[GOVERNANCE_STRENGTHENING.md](./GOVERNANCE_STRENGTHENING.md)** - How to strengthen governance for cross-agent consistency
- **[CROSS_DEPARTMENT_CONTINUITY.md](./CROSS_DEPARTMENT_CONTINUITY.md)** - Cross-agent knowledge and conflict detection analysis
- **[LLM_ORCHESTRATION_LAYER.md](./LLM_ORCHESTRATION_LAYER.md)** - LLM routing and provider management
- **[ENTERPRISE_DISCOVERY_ARCHITECTURE.md](./ENTERPRISE_DISCOVERY_ARCHITECTURE.md)** - Auto-discovery system

### Deployment & Operations
- **[DEPLOYMENT_TEMPLATES.md](./DEPLOYMENT_TEMPLATES.md)** - Multi-tenant deployment and templates
- **[CGI_DEPLOYMENT_GUIDE.md](./CGI_DEPLOYMENT_GUIDE.md)** - Production deployment guide
- **[TENANCY_MODEL.md](./TENANCY_MODEL.md)** - Multi-tenant architecture

### Development
- **[DEVELOPER_HANDOFF.md](./DEVELOPER_HANDOFF.md)** - Comprehensive developer guide
- **[AIOS_BUILD_SPEC.md](./AIOS_BUILD_SPEC.md)** - Build specifications
- **[IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)** - Current implementation status
- **[AIOS_TECHNICAL_ROADMAP.md](./AIOS_TECHNICAL_ROADMAP.md)** - Future roadmap

### Features
- **[ONBOARDING_SPEC.md](./ONBOARDING_SPEC.md)** - Agent onboarding system
- **[KNOWLEDGE_LAYER_SPEC.md](../KNOWLEDGE_LAYER_SPEC.md)** - Knowledge base architecture
- **[ENTERPRISE_REVIEW_PACK.md](../ENTERPRISE_REVIEW_PACK.md)** - Enterprise features

### Executive
- **[EXECUTIVE_SUMMARY.md](./EXECUTIVE_SUMMARY.md)** - Executive overview
- **[PHOENIX_OVERVIEW.md](./PHOENIX_OVERVIEW.md)** - Phoenix project overview

---

## Contact & Context

- **Developer**: Shavoni (CEO/CTO, DEF1LIVE LLC)
- **Project**: Cleveland API Gateway
- **Partners**: CGI, Mayor Justin Bibb
- **Target Users**: 8,000 city employees
- **Cost Savings Goal**: 40-70% via intelligent routing

---

*Last updated: 2026-01-25*
