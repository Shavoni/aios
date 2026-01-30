# HAAIS AIOS Operations Manual

> Complete guide for deploying HAAIS AIOS for new enterprise clients

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Starting Fresh (Clean Slate)](#2-starting-fresh-clean-slate)
3. [Starting the Application](#3-starting-the-application)
4. [Creating a New Client/Tenant](#4-creating-a-new-clienttenant)
5. [Onboarding Workflow](#5-onboarding-workflow)
6. [Agent Configuration](#6-agent-configuration)
7. [Knowledge Base Setup](#7-knowledge-base-setup)
8. [Governance & Policies](#8-governance--policies)
9. [Branding & White-Label](#9-branding--white-label)
10. [Testing & Validation](#10-testing--validation)
11. [Going Live](#11-going-live)
12. [Maintenance & Operations](#12-maintenance--operations)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Prerequisites

### System Requirements
- **Python**: 3.11+
- **Node.js**: 18+
- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 10GB for knowledge base and vector embeddings

### API Keys Required
Create a `.env` file in the project root:

```env
# Required - at least one LLM provider
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...

# Optional - for enhanced features
DEEPGRAM_API_KEY=...          # Voice transcription
ELEVENLABS_API_KEY=...        # Voice synthesis
```

### Install Dependencies

```bash
# Backend
cd "E:\My AI Projects and Apps\aiOS"
pip install -r requirements.txt

# Frontend
cd web
npm install
```

---

## 2. Starting Fresh (Clean Slate)

To remove all existing data and start fresh for a new client:

### Option A: Full Reset (Delete Everything)

```bash
# From project root
cd "E:\My AI Projects and Apps\aiOS"

# Remove all data
rmdir /s /q data\agents.json
rmdir /s /q data\knowledge
rmdir /s /q data\tenants
rmdir /s /q data\sessions
rmdir /s /q data\hitl
rmdir /s /q data\templates
rmdir /s /q data\onboarding

# Recreate empty directories
mkdir data\knowledge\files
mkdir data\knowledge\chroma
mkdir data\tenants
mkdir data\sessions\conversations
mkdir data\hitl
mkdir data\templates
mkdir data\onboarding
```

### Option B: Keep Templates, Reset Data

```bash
# Keep templates for reference, remove client-specific data
del data\agents.json
rmdir /s /q data\knowledge
rmdir /s /q data\tenants
rmdir /s /q data\sessions
rmdir /s /q data\hitl

mkdir data\knowledge\files
mkdir data\knowledge\chroma
mkdir data\tenants
mkdir data\sessions\conversations
mkdir data\hitl
```

### Initialize Empty Data Files

Create these empty JSON files:

**data/agents.json:**
```json
[]
```

**data/tenants/tenants.json:**
```json
{}
```

**data/hitl/approvals.json:**
```json
[]
```

---

## 3. Starting the Application

### Start Backend API

```bash
cd "E:\My AI Projects and Apps\aiOS"
python run_api.py
```

Wait for: `Uvicorn running on http://0.0.0.0:8000`

### Start Frontend

```bash
cd "E:\My AI Projects and Apps\aiOS\web"
npm run dev
```

Wait for: `Ready in Xs` - then access http://localhost:3000 (or 3002 if 3000 is busy)

### Verify Both Running

- **API Health:** http://localhost:8000/health
- **Frontend:** http://localhost:3000

---

## 4. Creating a New Client/Tenant

### Method 1: Via UI (Recommended)

1. Navigate to **http://localhost:3000/tenants**
2. Click **"Create Tenant"**
3. Fill in:
   - **Name**: Organization name (e.g., "City of Phoenix")
   - **Tier**: Select subscription tier
     - `free` - Limited features
     - `starter` - Basic features
     - `professional` - Full features
     - `enterprise` - Full + priority support
     - `government` - Government-specific compliance
   - **Admin Email**: Primary contact
   - **Admin Name**: Administrator name

### Method 2: Via API

```bash
curl -X POST http://localhost:8000/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "name": "City of Phoenix",
    "tier": "government",
    "admin_email": "admin@phoenix.gov",
    "admin_name": "John Smith"
  }'
```

### Method 3: Direct JSON

Edit `data/tenants/tenants.json`:

```json
{
  "phoenix-001": {
    "id": "phoenix-001",
    "name": "City of Phoenix",
    "status": "active",
    "tier": "government",
    "admin_email": "admin@phoenix.gov",
    "admin_name": "John Smith",
    "created_at": "2026-01-29T00:00:00",
    "updated_at": "2026-01-29T00:00:00",
    "settings": {
      "preferred_models": {},
      "default_temperature": 0.7,
      "default_max_tokens": 2000,
      "default_hitl_mode": "INFORM",
      "require_approval_for_domains": [],
      "prohibited_topics": [],
      "welcome_message": "Welcome to Phoenix AI Gateway",
      "escalation_email": "escalations@phoenix.gov"
    },
    "quota": {
      "daily_api_calls": 10000,
      "monthly_api_calls": 250000,
      "max_tokens_per_request": 8000,
      "max_requests_per_minute": 60,
      "max_agents": 50,
      "max_active_agents": 25,
      "max_concurrent_queries": 10,
      "max_kb_documents": 1000,
      "max_kb_size_mb": 500,
      "daily_llm_budget_usd": 100.0,
      "monthly_llm_budget_usd": 2500.0
    },
    "metadata": {}
  }
}
```

---

## 5. Onboarding Workflow

The onboarding system automates agent and knowledge base creation from client websites.

### Step 1: Start Onboarding Discovery

1. Navigate to **http://localhost:3000/onboarding**
2. Enter the client's main website URL (e.g., `https://www.phoenix.gov`)
3. Click **"Start Discovery"**
4. Wait for the crawler to analyze the site structure

### Step 2: Review Discovered Departments

The system will identify:
- Department/division pages
- Key personnel
- Service areas
- Contact information

### Step 3: Select Departments to Create Agents For

- Check the departments you want AI agents for
- Uncheck any that shouldn't have agents
- Click **"Generate Agents"**

### Step 4: Review Generated Agents

For each agent, verify:
- Name and title
- Domain classification
- Capabilities list
- Guardrails (restrictions)
- System prompt

### Step 5: Approve and Create

Click **"Create Agents"** to finalize. This will:
1. Create agent configurations
2. Generate the Concierge router agent
3. Start knowledge base population

---

## 6. Agent Configuration

### Agent Structure

Each agent has:

| Field | Description |
|-------|-------------|
| `id` | Unique identifier (e.g., `hr-assistant`) |
| `name` | Display name (e.g., "Sarah Johnson") |
| `title` | Job title (e.g., "HR Director") |
| `domain` | Category (HR, Finance, Legal, etc.) |
| `description` | What the agent does |
| `capabilities` | List of things agent CAN do |
| `guardrails` | List of things agent CANNOT do |
| `system_prompt` | Full LLM instructions |
| `escalates_to` | Who to escalate to |
| `gpt_url` | Optional external GPT link |
| `status` | `active`, `inactive`, or `degraded` |
| `is_router` | `true` for Concierge only |

### Creating Agents Manually

**Via UI:**
1. Go to **http://localhost:3000/agents**
2. Click **"Create Agent"**
3. Fill in all fields
4. Click **"Save"**

**Via API:**
```bash
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{
    "id": "hr-assistant",
    "name": "HR Assistant",
    "title": "Human Resources Specialist",
    "domain": "HR",
    "description": "Answers employee questions about HR policies and benefits",
    "capabilities": ["HR policy guidance", "Benefits information", "Leave procedures"],
    "guardrails": ["NEVER provide salary information", "NEVER handle complaints directly"],
    "system_prompt": "You are an HR assistant...",
    "escalates_to": "HR Director",
    "status": "active",
    "is_router": false
  }'
```

### The Concierge Agent

The Concierge is the **router agent** - it's the front door that directs users to specialist agents.

**Key Properties:**
- `is_router: true`
- `domain: "Router"`
- System prompt contains list of all other agents

**Auto-Generation:**
The Concierge is automatically regenerated when:
- New agents are created
- Agents are modified
- Agents are deleted

To manually regenerate:
```bash
curl -X POST http://localhost:8000/system/regenerate-concierge
```

---

## 7. Knowledge Base Setup

### Understanding the Knowledge Base

- **Vector Database**: ChromaDB stores embeddings for semantic search
- **Documents**: Markdown files in `data/knowledge/files/`
- **Per-Agent**: Each agent has its own knowledge collection
- **Shared Canon**: Some knowledge is shared across all agents

### Adding Knowledge via UI

1. Go to **http://localhost:3000/agents**
2. Click on an agent
3. Click **"Knowledge Base"** tab
4. Upload files (PDF, MD, TXT, DOCX supported)
5. Or add web URLs for automatic scraping

### Adding Knowledge via API

**Upload a file:**
```bash
curl -X POST http://localhost:8000/agents/hr-assistant/knowledge/upload \
  -F "file=@employee_handbook.pdf"
```

**Add from URL:**
```bash
curl -X POST http://localhost:8000/agents/hr-assistant/knowledge/web \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/hr-policies"}'
```

### Knowledge Base Best Practices

1. **Keep documents focused** - One topic per document
2. **Use clear headings** - Helps chunking and retrieval
3. **Update regularly** - Schedule periodic refreshes for web sources
4. **Test retrieval** - Query the agent and check if it finds relevant info

---

## 8. Governance & Policies

### HITL Modes (Human-in-the-Loop)

| Mode | Behavior |
|------|----------|
| `INFORM` | Agent responds immediately |
| `DRAFT` | Response saved for human review before sending |
| `EXECUTE` | Requires manager approval |
| `ESCALATE` | Routed to human, agent cannot respond |

### Setting Default HITL Mode

**Per-Tenant (via UI):**
1. Go to **http://localhost:3000/tenants**
2. Click on tenant → **Settings**
3. Set "Default HITL Mode"

**Per-Domain:**
Edit `data/governance_policies.json`:

```json
{
  "domain_policies": {
    "Legal": {
      "default_hitl_mode": "DRAFT",
      "require_approval": true
    },
    "HR": {
      "default_hitl_mode": "INFORM",
      "prohibited_topics": ["salary", "termination"]
    }
  }
}
```

### Risk Detection

The system automatically detects:
- **PII** - Personal identifiable information
- **FINANCIAL** - Financial data or transactions
- **LEGAL** - Legal contracts or advice
- **CONFIDENTIAL** - Marked confidential content

Configure responses to risk signals in governance policies.

---

## 9. Branding & White-Label

### Frontend Branding

Edit `web/src/lib/config.ts`:

```typescript
export const brandConfig: BrandConfig = {
  appName: "Phoenix AI Gateway",
  tagline: "City Employee Support",
  organization: "City of Phoenix",

  primaryColor: "orange-600",
  primaryColorLight: "orange-100",
  primaryColorDark: "orange-700",
  accentColor: "red-500",

  logoIcon: "Building2",
  logoUrl: "/phoenix-logo.png",  // Place in web/public/
  logoAlt: "City of Phoenix Logo",

  footerText: "Phoenix AI Gateway • Powered by HAAIS AIOS",
  supportEmail: "it-support@phoenix.gov",
};
```

### Environment-Based Branding

Set in `.env.local`:
```env
NEXT_PUBLIC_BRAND=phoenix
```

Then create a `phoenixConfig` in config.ts and add to the switch statement.

### Custom Logo

1. Place logo file in `web/public/` (e.g., `logo.png`)
2. Set `logoUrl: "/logo.png"` in config
3. Recommended size: 200x50px for header

---

## 10. Testing & Validation

### Test Checklist

- [ ] **API Health**: http://localhost:8000/health returns `"status": "ok"`
- [ ] **Agents Load**: http://localhost:3000/agents shows all agents
- [ ] **Concierge Works**: Chat routes to correct agents
- [ ] **Knowledge Retrieval**: Agents answer from their knowledge base
- [ ] **HITL Works**: Approval workflow triggers correctly
- [ ] **Tenant Isolation**: Data is properly scoped

### Test Commands

```bash
# Test agent query
curl -X POST http://localhost:8000/agents/hr-assistant/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the vacation policy?"}'

# Test routing
curl -X POST http://localhost:8000/agents/route \
  -H "Content-Type: application/json" \
  -d '{"query": "I need help with my paycheck"}'

# Test governance
curl -X POST http://localhost:8000/governance/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Tell me about employee salaries",
    "tenant_id": "phoenix-001",
    "role": "employee",
    "department": "General"
  }'
```

### Simulation Mode

Test without making real LLM calls:
```bash
curl -X POST http://localhost:8000/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "How do I request time off?",
    "tenant_id": "phoenix-001"
  }'
```

---

## 11. Going Live

### Pre-Launch Checklist

- [ ] All agents configured and tested
- [ ] Knowledge bases populated and verified
- [ ] Governance policies set appropriately
- [ ] HITL approvers assigned
- [ ] Branding customized
- [ ] API keys are production keys (not test)
- [ ] Error handling tested
- [ ] Backup procedures in place

### Production Deployment

**Option A: Direct Server**
```bash
# Backend
cd "E:\My AI Projects and Apps\aiOS"
uvicorn packages.api:app --host 0.0.0.0 --port 8000 --workers 4

# Frontend
cd web
npm run build
npm start
```

**Option B: Docker (Recommended)**
```bash
docker-compose up -d
```

### SSL/HTTPS

For production, always use HTTPS. Configure via:
- Reverse proxy (nginx, Caddy)
- Cloud load balancer (AWS ALB, Azure App Gateway)

---

## 12. Maintenance & Operations

### Daily Operations

| Task | How |
|------|-----|
| Check API health | GET http://localhost:8000/health |
| Review approvals | http://localhost:3000/approvals |
| Monitor usage | http://localhost:3000/analytics |
| Check audit logs | http://localhost:3000/audit |

### Backup Procedures

**Backup data folder:**
```bash
# Create timestamped backup
xcopy /E /I data backup\data_%date:~-4,4%%date:~-7,2%%date:~-10,2%
```

**Critical files to backup:**
- `data/agents.json`
- `data/tenants/`
- `data/knowledge/`
- `data/governance_policies.json`
- `.env`

### Updating Knowledge Base

**Manual refresh:**
```bash
curl -X POST http://localhost:8000/agents/{agent_id}/knowledge/refresh
```

**Scheduled refresh:**
The system has a built-in scheduler. Configure in `packages/core/knowledge/__init__.py`.

### Monitoring

Key metrics to watch:
- API response times
- LLM token usage
- Error rates
- Approval queue depth

---

## 13. Troubleshooting

### Common Issues

**"Failed to fetch" errors in browser**
- API server not running
- Fix: `python run_api.py`

**"Internal Server Error" on queries**
- Usually stale code or missing data
- Fix: Restart API server

**Agent not responding**
- Check agent status is "active"
- Verify LLM API key is valid
- Check governance isn't blocking

**Knowledge base not finding documents**
- Documents may not be embedded yet
- Fix: Re-upload or trigger refresh

**Concierge not routing correctly**
- Regenerate Concierge: POST `/system/regenerate-concierge`

### Log Locations

- **API logs**: Console output from `python run_api.py`
- **Frontend logs**: Browser DevTools Console
- **Audit logs**: http://localhost:3000/audit

### Getting Help

- **Documentation**: `/docs` folder
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Support**: support@haais.ai

---

## Quick Reference

### Key URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

### Key Commands

```bash
# Start backend
python run_api.py

# Start frontend
cd web && npm run dev

# Build frontend
cd web && npm run build

# Run tests
pytest tests/
```

### Key Files

| File | Purpose |
|------|---------|
| `data/agents.json` | Agent configurations |
| `data/tenants/tenants.json` | Tenant data |
| `data/governance_policies.json` | Policy rules |
| `web/src/lib/config.ts` | Branding config |
| `.env` | API keys and secrets |

---

*HAAIS AIOS Operations Manual v1.0*
*Last Updated: January 2026*
