# HAAIS AIOS - Claude Code Context

## Project Overview

HAAIS AIOS (Human-Assisted AI Services - AI Operating System) is an enterprise AI governance platform designed for regulated environments like government, healthcare, and enterprise operations.

**Owner**: DEF1LIVE LLC / HAAIS
**Primary Client**: City of Cleveland (8,000 employees)
**Status**: Enterprise-ready with P0 security controls implemented

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       FRONTEND (Next.js)                      │
│  web/src/app/ - Chat, Agents, Analytics, Settings, etc.      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      API GATEWAY (FastAPI)                    │
│  packages/api/ - REST endpoints, middleware, security        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        CORE SERVICES                          │
│  packages/core/ - Agents, Governance, Knowledge, Grounding   │
│  packages/auth/ - OIDC/SAML authentication                   │
│  packages/authz/ - RBAC/ABAC authorization                   │
│  packages/audit/ - Immutable audit logging                   │
└─────────────────────────────────────────────────────────────┘
```

## Key Directories

```
aiOS/
├── packages/
│   ├── api/           # FastAPI endpoints
│   ├── core/          # Business logic
│   │   ├── agents.py       # Agent management
│   │   ├── governance/     # Policy engine
│   │   ├── grounding.py    # Source attribution
│   │   └── knowledge.py    # RAG pipeline
│   ├── auth/          # Enterprise authentication
│   ├── authz/         # Authorization engine
│   └── audit/         # Immutable audit logs
├── web/               # Next.js frontend
│   └── src/app/       # App router pages
├── data/              # Local data storage
├── migrations/        # SQL migrations
├── docs/              # Documentation
└── tests/             # Test suites
```

## Running the Application

```bash
# Start API server
python run_api.py

# Start frontend (separate terminal)
cd web && npm run dev
```

**URLs:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Key Concepts

### 1. Grounded AI
Every AI response includes source attribution:
- `grounding_score`: 0.0-1.0 confidence metric
- `source_citations`: Links to authoritative documents
- `authority_basis`: Legal/policy backing (e.g., "HR Policy §4.2")

### 2. HITL (Human-in-the-Loop)
Four modes controlling AI autonomy:
- **INFORM**: Respond immediately
- **DRAFT**: Save for human review
- **EXECUTE**: Require manager approval
- **ESCALATE**: Human takes over

### 3. Multi-Tenancy
Complete tenant isolation via:
- PostgreSQL Row-Level Security (RLS)
- X-Tenant-ID header (dev) or JWT claims (prod)
- Per-tenant governance policies

### 4. Enterprise Security (P0)
- **Authentication**: OIDC/SAML SSO (packages/auth/)
- **Authorization**: RBAC + ABAC (packages/authz/)
- **Audit**: Hash-chained immutable logs (packages/audit/)
- **Grounding Enforcement**: Block unverified responses

## Environment Variables

Key settings in `.env`:

```bash
# LLM Provider
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Auth (production)
AIOS_AUTH_MODE=production
AIOS_OIDC_ISSUER=https://login.example.com
AIOS_OIDC_CLIENT_ID=...

# Auth (development)
AIOS_AUTH_MODE=development
AIOS_ALLOW_HEADER_AUTH=true

# Grounding
AIOS_GROUNDING_ENABLED=true
AIOS_GROUNDING_MIN_SCORE=0.5
```

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_enterprise_security.py

# Run with coverage
pytest --cov=packages
```

## Common Tasks

### Add New Agent
1. POST to `/agents` with config
2. Upload knowledge docs to `/agents/{id}/knowledge`
3. Test via `/agents/{id}/query`

### Configure Governance
1. Edit policies in governance manager
2. Set HITL modes per domain
3. Configure risk signals

### Enable Production Auth
1. Set `AIOS_AUTH_MODE=production`
2. Configure OIDC issuer/client
3. Run RLS migrations
4. Remove `AIOS_ALLOW_HEADER_AUTH`

## Documentation

- `docs/USER_MANUAL.md` - End user guide
- `docs/OPERATIONS_MANUAL.md` - Admin guide
- `docs/GROUNDED_AI.md` - Grounding architecture
- `docs/ENTERPRISE_HARDENING_STRATEGY.md` - Security roadmap
- `docs/compliance/COMPLIANCE_POSITIONING.md` - SOC2/HIPAA/GDPR mapping

## Contact

**Developer**: Shavoni (CEO/CTO, DEF1LIVE LLC)
**Project**: Cleveland API Gateway / HAAIS AIOS
