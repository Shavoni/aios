# HAAIS OS Knowledge Layer - Source of Truth

**Created:** 2026-01-23
**Author:** Shavoni (HAAIS) + Claude
**Status:** Implementation Phase

---

## Purpose

This document captures the architectural decisions and implementation state for the Governed Knowledge Layer addition to HAAIS OS. Use this as the reference to avoid drift or hallucination during development.

---

## Problem Statement

OpenAI Custom GPTs have built-in voice capabilities but are limited to:
- 20 files max
- 512MB storage
- No multi-tenant isolation
- No sensitivity controls
- No audit logging

Cleveland's citywide AI deployment requires:
- Unlimited document storage
- Department-scoped access (HR can't see Finance docs)
- Sensitivity tiers (public < internal < confidential < restricted < privileged)
- Full audit trail for compliance
- Citations on every grounded response

---

## Solution Architecture

```
City Employee (voice or text)
        |
        v
   Custom GPT (OpenAI platform)
   - Voice/text UI (OpenAI handles this)
   - Calls Action on questions needing grounding
        |
        v
   POST /kb/query (HAAIS Knowledge API)
   - Validates Bearer token
   - Embeds question via OpenAI
   - Queries Supabase with governance filters
   - Logs query for audit
   - Returns evidence + citations
        |
        v
   GPT synthesizes grounded answer
        |
        v
   Voice/text response to employee
```

---

## What We Are Adding

### 1. Agent Manifest Schema

**Purpose:** Declarative configuration for all municipal agents.

**Key Fields per Agent:**
| Field | Purpose |
|-------|---------|
| `agent_id` | Unique identifier (e.g., "cle-hr-003") |
| `department_id` | Department scope |
| `instruction_kernel` | System prompt for GPT |
| `default_max_sensitivity` | Sensitivity ceiling |
| `allowed_scopes` | Granular permissions |
| `knowledge_profile` | Accessible doc collections |
| `action_profile` | What agent can do (draft, submit, etc.) |

**Sensitivity Tiers (5 levels):**
`public` < `internal` < `confidential` < `restricted` < `privileged`

**File:** `packages/kb/cleveland-manifest.json`

### 2. Supabase Knowledge Store (SQL)

**Tables:**
| Table | Purpose |
|-------|---------|
| `departments` | Tenant registry |
| `documents` | Doc metadata + visibility + sensitivity + knowledge_profile |
| `document_chunks` | Chunks + embeddings (pgvector) |
| `kb_query_logs` | Audit trail (includes agent_id, knowledge_profiles_used) |
| `agent_manifests` | Dynamic manifest storage |
| `agent_api_keys` | API key to agent mapping |

**Key Functions:**
- `kb_match_chunks(...)` - Basic governance-filtered search
- `kb_match_chunks_by_profile(...)` - Search filtered by knowledge_profile

**File:** `sql/knowledge-layer-schema.sql`

### 3. Knowledge Query API (TypeScript/Express)

**Endpoints:**
- `POST /kb/query` - Semantic search with governance
- `GET /kb/health` - Health check
- `GET /kb/agent` - Get current agent info

**Auth:** Bearer token in Authorization header

**File:** `packages/kb/query.ts`

### 4. Ingestion Pipeline (TypeScript/Node CLI)

**Command:**
```bash
npx ts-node ingest-md.ts <rootFolder> <department_id> <visibility> <sensitivity>
```

**File:** `packages/kb/ingest-md.ts`

### 5. White-Label System Management

**Purpose:** Allow complete reset and re-provisioning for new clients while preserving the HAAIS OS core.

**Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `GET /system/status` | View current manifest, data counts |
| `POST /system/reset` | Clear all client data (requires confirmation) |
| `POST /system/provision` | Set up new client with base Concierge agent |
| `POST /system/import-manifest` | Import complete agent manifest |
| `POST /system/generate-key` | Generate API key for an agent |

**Reset Workflow:**
1. `POST /system/reset` with `confirm: "RESET_ALL_CLIENT_DATA"`
   - Archives audit logs (optional)
   - Deletes: chunks → documents → logs → API keys → manifests → departments
2. `POST /system/provision` with new client details
   - Creates fresh manifest with Concierge agent
   - Creates base department
3. `POST /system/import-manifest` with full agent manifest
   - Imports all agent definitions
   - Creates departments from agents
4. `POST /system/generate-key` for each agent
   - Returns key once (never stored in plain text)

**Security:** Admin endpoints require `adminAuth` bearer token (separate from agent keys).

**File:** `packages/kb/system.ts`

---

## Non-Negotiables (HAAIS Governance)

1. **Department isolation enforced at DB level** (RLS + function filters)
2. **Sensitivity ceiling enforced server-side** (not trusted from client)
3. **Every query logged** with requester, department, retrieved doc IDs
4. **Citations returned** for every grounded answer
5. **Bearer token required** - no anonymous access

---

## File Structure

```
aios/
├── packages/
│   ├── api/                    # Existing FastAPI backend
│   ├── core/
│   │   ├── knowledge/          # Existing Chroma (kept for local dev)
│   │   └── ...
│   └── kb/                     # NEW: Knowledge Layer
│       ├── server.ts           # Express server entry point
│       ├── query.ts            # Query endpoint + health check + agent info
│       ├── system.ts           # White-label system management endpoints
│       ├── manifest.ts         # Agent manifest types + registry
│       ├── cleveland-manifest.json  # Cleveland agent definitions
│       ├── ingest-md.ts        # CLI ingestion pipeline
│       ├── openapi.json        # GPT Action spec (includes admin endpoints)
│       └── package.json        # Dependencies
├── sql/
│   └── knowledge-layer-schema.sql
├── web/                        # Existing Next.js frontend
└── KNOWLEDGE_LAYER_SPEC.md     # THIS FILE
```

---

## Cleveland Agents (8 total)

| Agent | Department | Sensitivity | Citywide |
|-------|------------|-------------|----------|
| Public Safety | Police/Fire | confidential | Yes |
| Public Works | Infrastructure | internal | Yes |
| Human Resources | HR | restricted | Yes |
| Finance & Budget | Finance | confidential | Yes |
| Community Dev | Housing | internal | Yes |
| Public Health | Health | restricted | No |
| Law Department | Legal | privileged | No |
| IT Services | IT | confidential | Yes |

---

## Implementation Checklist

- [x] Create `sql/knowledge-layer-schema.sql`
- [x] Add `privileged` sensitivity tier
- [x] Add `knowledge_profile` column to documents
- [x] Add `kb_match_chunks_by_profile` function
- [x] Create `packages/kb/` directory structure
- [x] Create `manifest.ts` with agent types + registry
- [x] Create `cleveland-manifest.json` with 8 agents
- [x] Implement `query.ts` with manifest-driven auth
- [x] Add `/kb/agent` endpoint for agent info
- [x] Implement `ingest-md.ts` CLI
- [x] Create `openapi.json` for GPT Actions
- [x] Create `server.ts` Express entry point
- [x] Create `package.json` with dependencies
- [x] Add white-label system management (`system.ts`)
- [x] Add `/system/status`, `/system/reset`, `/system/provision` endpoints
- [x] Add `/system/import-manifest`, `/system/generate-key` endpoints
- [x] Update OpenAPI spec with admin endpoints + schemas
- [ ] Run schema on Supabase
- [ ] Test with sample department docs
- [ ] Generate production API keys
- [ ] Configure first Custom GPT Action
- [ ] Verify audit logs populated

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-01-23 | Initial spec + implementation | Shavoni + Claude |
| 2026-01-23 | Added manifest schema with 8 Cleveland agents | Shavoni + Claude |
| 2026-01-25 | Added white-label system management endpoints | Shavoni + Claude |
