# aiOS Multi-Tenant Deployment & Template System

> **Purpose**: Enable aiOS to be reset, duplicated, and deployed for multiple cities/departments
> **Status**: PARTIALLY IMPLEMENTED - See Template Coverage below
> **Last Updated**: January 30, 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [Template System Architecture](#2-template-system-architecture)
3. [Configuration Profiles](#3-configuration-profiles)
4. [Reset & Clone Operations](#4-reset--clone-operations)
5. [Multi-Tenant Data Isolation](#5-multi-tenant-data-isolation)
6. [Implementation Tasks](#6-implementation-tasks)

---

## 1. Overview

### Use Cases

| Scenario | Operation | Example |
|----------|-----------|---------|
| Fresh start | **Reset** | Clear Cleveland data, start clean |
| New city deployment | **Clone + Configure** | Deploy for Detroit, Cincinnati |
| Department instance | **Template** | HR-only version, Finance-only version |
| Backup/Restore | **Export/Import** | Save current state, restore later |
| Demo environment | **Template** | Pre-configured demo with sample data |

### Core Requirements

1. **Configuration Externalization**: All city/org-specific data in config files
2. **Data Isolation**: Separate knowledge bases, agents, policies per tenant
3. **Template Export**: Save current configuration as reusable template
4. **Quick Reset**: One-command reset to clean state
5. **Clone Deployment**: Duplicate instance with new identity

---

## 2. Template System Architecture

### Template Structure

```
templates/
├── cleveland/                    # Cleveland city template
│   ├── manifest.json            # Template metadata
│   ├── agents.json              # Agent configurations
│   ├── policies.json            # Governance policies
│   ├── knowledge/               # Knowledge base documents
│   │   ├── hr/
│   │   ├── finance/
│   │   └── public-health/
│   └── branding/                # UI customization
│       ├── logo.png
│       └── theme.json
│
├── generic-city/                 # Generic city government template
│   ├── manifest.json
│   ├── agents.json              # Generic department agents
│   ├── policies.json            # Standard governance
│   └── knowledge/               # Placeholder structure
│
├── enterprise/                   # Generic enterprise template (NOT BUILT)
│   ├── manifest.json
│   ├── agents.json
│   └── policies.json
│
└── minimal/                      # Bare minimum template
    ├── manifest.json
    └── agents.json              # Just concierge
```

### Current Template Implementation Status

**Location**: `packages/onboarding/manifest.py` (AGENT_TEMPLATES)
**Location**: `packages/onboarding/kb_generator/templates.py` (DOMAIN_TEMPLATES, REGULATORY_TEMPLATES)

#### Municipal Agent Templates (Built)

| Template ID | Name Format | Domain | Status |
|-------------|-------------|--------|--------|
| `public-health` | {city} Public Health | PublicHealth | ✅ Built |
| `hr` | {city} Human Resources | HR | ✅ Built |
| `finance` | {city} Finance | Finance | ✅ Built |
| `building` | {city} Building & Housing | Building | ✅ Built |
| `311` | {city} 311 Services | 311 | ✅ Built |
| `strategy` | {city} Strategy Office | Strategy | ✅ Built |
| `public-safety` | {city} Public Safety | PublicSafety | ✅ Built |
| `parks` | {city} Parks & Recreation | Parks | ✅ Built |
| `public-works` | {city} Public Works | PublicWorks | ✅ Built |

#### Missing Municipal Templates (Gaps)

| Template ID | Name Format | Domain | Priority |
|-------------|-------------|--------|----------|
| `fire` | {city} Fire Department | Fire | HIGH |
| `law` | {city} Law Department | Legal | HIGH |
| `it` | {city} IT Services | Technology | MEDIUM |
| `communications` | {city} Communications | Comms | MEDIUM |
| `clerk` | {city} Clerk's Office | Administrative | LOW |
| `utilities` | {city} Public Utilities | Utilities | LOW |

#### Enterprise Templates (NOT BUILT)

| Template ID | Description | Status |
|-------------|-------------|--------|
| `enterprise-hr` | Corporate HR | ❌ Not Built |
| `enterprise-finance` | Corporate Finance | ❌ Not Built |
| `enterprise-legal` | Legal/Compliance | ❌ Not Built |
| `enterprise-it` | IT/Engineering | ❌ Not Built |
| `enterprise-sales` | Sales/Marketing | ❌ Not Built |
| `enterprise-support` | Customer Support | ❌ Not Built |

#### Regulatory Templates (Built)

| Template ID | Regulation | Status |
|-------------|------------|--------|
| `hipaa` | HIPAA Privacy Rule | ✅ Built |
| `epa_clean_water` | Clean Water Act | ✅ Built |
| `safe_drinking_water` | Safe Drinking Water Act | ✅ Built |
| `fair_housing` | Fair Housing Act | ✅ Built |
| `ohio_building_code` | Ohio Building Code | ✅ Built |
| `cdc_guidelines` | CDC Guidelines | ✅ Built |

#### Domain KB Templates (Built)

| Template ID | Files Generated | Status |
|-------------|-----------------|--------|
| `public_health` | 19 KB files | ✅ Built |
| `building_housing` | 18 KB files | ✅ Built |
| `public_utilities` | 16 KB files | ✅ Built |
| `public_safety` | 17 KB files | ✅ Built |
| `finance` | 16 KB files | ✅ Built |
| `hr` | 16 KB files | ✅ Built |

### Manifest Schema

```json
{
  "name": "cleveland",
  "display_name": "City of Cleveland",
  "version": "1.0.0",
  "description": "Cleveland Civic AI deployment",
  "type": "city-government",
  "created_at": "2026-01-25T00:00:00Z",
  "author": "DEF1LIVE LLC",

  "organization": {
    "name": "City of Cleveland",
    "domain": "clevelandohio.gov",
    "employees": 8000,
    "timezone": "America/New_York"
  },

  "features": {
    "governance_enabled": true,
    "hitl_modes": ["INFORM", "DRAFT", "ESCALATE"],
    "rag_enabled": true,
    "multi_provider": true
  },

  "agents": {
    "source": "agents.json",
    "count": 9
  },

  "policies": {
    "source": "policies.json",
    "count": 12
  },

  "knowledge": {
    "directory": "knowledge/",
    "total_documents": 55
  }
}
```

---

## 3. Configuration Profiles

### Environment Configuration

**File**: `config/environment.json`

```json
{
  "instance_id": "cleveland-prod-001",
  "tenant_id": "city-of-cleveland",
  "environment": "production",

  "template": {
    "name": "cleveland",
    "version": "1.0.0",
    "locked": false
  },

  "database": {
    "type": "sqlite",
    "path": "data/cleveland.db"
  },

  "storage": {
    "knowledge_base": "data/knowledge/",
    "uploads": "data/uploads/",
    "exports": "data/exports/"
  },

  "api": {
    "base_url": "https://api.clevelandcivicai.gov",
    "cors_origins": ["https://clevelandcivicai.gov"]
  },

  "llm": {
    "default_provider": "anthropic",
    "fallback_provider": "openai",
    "local_model": "llama-3.1-70b"
  }
}
```

### Secrets Configuration (Not in Git)

**File**: `config/secrets.json` (gitignored)

```json
{
  "anthropic_api_key": "sk-ant-...",
  "openai_api_key": "sk-...",
  "supabase_url": "https://xxx.supabase.co",
  "supabase_anon_key": "...",
  "admin_password_hash": "..."
}
```

### Branding Configuration

**File**: `config/branding.json`

```json
{
  "organization_name": "City of Cleveland",
  "tagline": "AI-Powered Civic Services",
  "logo_url": "/assets/cleveland-logo.png",
  "favicon_url": "/assets/favicon.ico",

  "theme": {
    "primary_color": "#003366",
    "secondary_color": "#FFD700",
    "font_family": "Inter, sans-serif"
  },

  "contact": {
    "support_email": "ai-support@clevelandohio.gov",
    "admin_email": "ai-admin@clevelandohio.gov"
  },

  "legal": {
    "privacy_policy_url": "https://clevelandohio.gov/privacy",
    "terms_of_service_url": "https://clevelandohio.gov/terms"
  }
}
```

---

## 4. Reset & Clone Operations

### Reset Operations

#### Full Reset (Nuclear Option)

Clears ALL data and returns to template defaults.

```bash
# CLI Command
python -m aios reset --full --confirm

# Or via API
POST /system/reset
{
  "mode": "full",
  "confirm": true,
  "preserve_secrets": true
}
```

**What gets reset**:
- All agents → restored from template
- All policies → restored from template
- All knowledge base documents → cleared
- All conversation history → cleared
- All user data → cleared

**What's preserved**:
- API keys and secrets
- Environment configuration
- Template files

#### Soft Reset (Keep Structure)

Clears user data but keeps configuration.

```bash
python -m aios reset --soft --confirm
```

**What gets reset**:
- Conversation history
- User uploads
- Audit logs

**What's preserved**:
- Agents
- Policies
- Knowledge base
- All configuration

#### Agent Reset

Reset agents to template defaults without touching other data.

```bash
python -m aios reset --agents-only --confirm
```

### Clone Operations

#### Export Current State as Template

```bash
# Export everything as new template
python -m aios template export --name "cleveland-v2" --output templates/

# Export specific components
python -m aios template export --name "cleveland-agents" --agents-only
python -m aios template export --name "cleveland-policies" --policies-only
```

**API Endpoint**:
```
POST /system/template/export
{
  "name": "cleveland-backup-2026-01",
  "include_knowledge": true,
  "include_policies": true,
  "include_agents": true
}

Response:
{
  "template_path": "exports/cleveland-backup-2026-01.zip",
  "manifest": { ... },
  "size_bytes": 15234567
}
```

#### Create New Instance from Template

```bash
# Interactive setup
python -m aios init --template generic-city

# Non-interactive with config
python -m aios init --template generic-city --config new-city-config.json
```

**Interactive Prompts**:
```
? Organization name: City of Detroit
? Organization domain: detroitmi.gov
? Number of employees: 10000
? Timezone: America/Detroit
? Enable governance? Yes
? Default LLM provider: anthropic

Creating new instance...
✓ Copied template files
✓ Generated agents with Detroit branding
✓ Created empty knowledge base
✓ Initialized database

Instance ready! Start with: python -m aios serve
```

#### Clone to New Directory

```bash
# Clone current instance to new location
python -m aios clone --target /deployments/detroit --new-tenant detroit
```

---

## 5. Multi-Tenant Data Isolation

### Single-Instance Multi-Tenant

For running multiple tenants in one application instance.

```
data/
├── tenants/
│   ├── cleveland/
│   │   ├── agents.json
│   │   ├── policies.json
│   │   ├── knowledge/
│   │   └── database.db
│   │
│   ├── detroit/
│   │   ├── agents.json
│   │   ├── policies.json
│   │   ├── knowledge/
│   │   └── database.db
│   │
│   └── cincinnati/
│       └── ...
│
└── shared/
    ├── models/           # Shared LLM models
    └── embeddings/       # Shared embedding cache
```

### Tenant Context

```python
# packages/core/tenant.py

class TenantContext:
    """Manages tenant-specific data isolation."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.data_path = Path(f"data/tenants/{tenant_id}")
        self.agents_path = self.data_path / "agents.json"
        self.policies_path = self.data_path / "policies.json"
        self.knowledge_path = self.data_path / "knowledge"
        self.db_path = self.data_path / "database.db"

    def get_agent_manager(self) -> AgentManager:
        return AgentManager(config_path=self.agents_path)

    def get_governance_engine(self) -> GovernanceEngine:
        return GovernanceEngine(policies_path=self.policies_path)

    def get_knowledge_store(self) -> KnowledgeStore:
        return KnowledgeStore(base_path=self.knowledge_path)
```

### API Tenant Resolution

```python
# Middleware to resolve tenant from request

async def tenant_middleware(request: Request, call_next):
    # Option 1: From subdomain
    # cleveland.civicai.com → tenant_id = "cleveland"
    host = request.headers.get("host", "")
    tenant_id = host.split(".")[0]

    # Option 2: From header
    # X-Tenant-ID: cleveland
    tenant_id = request.headers.get("X-Tenant-ID", tenant_id)

    # Option 3: From path
    # /api/v1/cleveland/ask → tenant_id = "cleveland"

    request.state.tenant = TenantContext(tenant_id)
    response = await call_next(request)
    return response
```

---

## 6. Implementation Tasks

### Phase 0: Template Gaps (HIGH PRIORITY)

- [ ] **Task 0.1**: Add missing municipal templates
  - [ ] Create `fire` template (Fire Department)
  - [ ] Create `law` template (Law Department)
  - [ ] Create `it` template (IT Services)
  - [ ] Create `communications` template

- [ ] **Task 0.2**: Build enterprise template library
  - [ ] Create `enterprise-hr` template
  - [ ] Create `enterprise-finance` template
  - [ ] Create `enterprise-legal` template
  - [ ] Create `enterprise-it` template
  - [ ] Create `enterprise-sales` template
  - [ ] Create `enterprise-support` template

- [ ] **Task 0.3**: Expand routing keywords
  - [ ] Add more keyword variations per template
  - [ ] Improve fuzzy matching for department names

### Phase 1: Template System

- [ ] **Task 1.1**: Create template directory structure
  - [ ] Define manifest.json schema
  - [ ] Create `templates/minimal/` base template
  - [ ] Create `templates/generic-city/` template

- [ ] **Task 1.2**: Implement template export
  - [ ] `POST /system/template/export` endpoint
  - [ ] CLI command `aios template export`
  - [ ] Include agents, policies, knowledge

- [ ] **Task 1.3**: Implement template import
  - [ ] `POST /system/template/import` endpoint
  - [ ] CLI command `aios init --template`
  - [ ] Interactive configuration wizard

### Phase 2: Reset Operations

- [ ] **Task 2.1**: Implement full reset
  - [ ] `POST /system/reset` endpoint (already exists, enhance)
  - [ ] Add `--full` mode
  - [ ] Restore from template

- [ ] **Task 2.2**: Implement soft reset
  - [ ] Add `--soft` mode
  - [ ] Clear only user data

- [ ] **Task 2.3**: Implement agent reset
  - [ ] Add `--agents-only` mode
  - [ ] Restore agents from template

### Phase 3: Multi-Tenant Support

- [ ] **Task 3.1**: Create TenantContext class
  - [ ] Data path isolation
  - [ ] Scoped managers (agents, governance, knowledge)

- [ ] **Task 3.2**: Add tenant middleware
  - [ ] Resolve tenant from request
  - [ ] Inject into request state

- [ ] **Task 3.3**: Update all endpoints for tenant awareness
  - [ ] Pass tenant context to managers
  - [ ] Isolate all data operations

### Phase 4: CLI Tools

- [ ] **Task 4.1**: Create `aios` CLI
  ```bash
  aios init          # Initialize new instance
  aios serve         # Start API server
  aios reset         # Reset operations
  aios template      # Template operations
  aios tenant        # Tenant management
  ```

- [ ] **Task 4.2**: Add tenant management commands
  ```bash
  aios tenant list
  aios tenant create <name>
  aios tenant delete <name>
  aios tenant export <name>
  ```

---

## Quick Reference: Common Operations

### Deploy for New City

```bash
# 1. Clone repository
git clone https://github.com/def1live/aios.git detroit-civic-ai
cd detroit-civic-ai

# 2. Initialize from template
python -m aios init --template generic-city

# 3. Configure (interactive)
# Enter: "City of Detroit", "detroitmi.gov", etc.

# 4. Add city-specific agents
# Edit data/agents.json

# 5. Load knowledge base
python -m aios knowledge import --dir detroit-docs/

# 6. Start
python -m aios serve
```

### Backup Current Deployment

```bash
# Export as template
python -m aios template export \
  --name "cleveland-backup-$(date +%Y%m%d)" \
  --include-knowledge \
  --output backups/
```

### Reset for Demo

```bash
# Soft reset (keeps config, clears user data)
python -m aios reset --soft --confirm

# Load demo data
python -m aios demo load --scenario "city-services"
```

---

## Configuration File Locations

| File | Purpose | Git Tracked |
|------|---------|-------------|
| `config/environment.json` | Instance configuration | Yes (template) |
| `config/secrets.json` | API keys, passwords | No |
| `config/branding.json` | UI customization | Yes |
| `data/agents.json` | Agent definitions | Yes |
| `data/policies.json` | Governance rules | Yes |
| `data/knowledge/` | Knowledge documents | No |
| `data/database.db` | Application database | No |
| `templates/` | Reusable templates | Yes |

---

*Document created 2026-01-25 for aiOS multi-tenant deployment system*
