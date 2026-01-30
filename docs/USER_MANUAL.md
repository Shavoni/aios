# HAAIS AIOS User Manual

## Human-Assisted AI Services - AI Operating System

**Version 1.1 | Enterprise AI Governance Platform**

**Enterprise Hardening Update (January 2026):**
- OIDC/SAML SSO Authentication
- RBAC + ABAC Authorization
- Immutable Hash-Chained Audit Logs
- Grounded AI with Source Enforcement
- PostgreSQL Row-Level Security

---

# Executive Summary

## The Problem

Large organizations—especially government agencies and enterprises—face a critical challenge: **How do you deploy AI assistants that are helpful, accurate, and safe?**

### Current Pain Points

| Challenge | Impact |
|-----------|--------|
| **Ungoverned AI** | Employees using ChatGPT with no oversight, risking data leaks and compliance violations |
| **No Accountability** | No audit trail of AI interactions, impossible to track what advice was given |
| **One-Size-Fits-All** | Generic AI can't handle domain-specific policies, procedures, and institutional knowledge |
| **Shadow IT** | Departments building their own AI solutions, creating security gaps and inconsistency |
| **Cost Uncertainty** | No control over AI spending, no way to optimize costs across providers |
| **Compliance Risk** | AI responses may violate regulations, expose PII, or provide unauthorized advice |

### The Cost of Inaction

- **40-70% of employee AI usage** is on unsanctioned tools
- **$50K-500K potential liability** per compliance violation
- **Hours wasted daily** as employees search for information across siloed systems
- **Inconsistent service** as different departments give different answers

---

## The Solution: HAAIS AIOS

**HAAIS AIOS (Human-Assisted AI Services - AI Operating System)** is an enterprise AI governance platform that gives organizations a **single, secure, auditable front door** to AI-powered assistance.

### Core Value Proposition

```
┌─────────────────────────────────────────────────────────────────┐
│                         HAAIS AIOS                               │
│                                                                  │
│   ┌─────────┐    ┌─────────────┐    ┌─────────────────────┐    │
│   │  User   │ →  │  Concierge  │ →  │  Specialist Agent   │    │
│   │ Request │    │   (Router)  │    │  (HR, Legal, etc.)  │    │
│   └─────────┘    └─────────────┘    └─────────────────────┘    │
│                         │                      │                │
│                         ▼                      ▼                │
│              ┌─────────────────┐    ┌─────────────────┐        │
│              │   Governance    │    │  Knowledge Base │        │
│              │   (Policies,    │    │  (Documents,    │        │
│              │    HITL, Audit) │    │   Procedures)   │        │
│              └─────────────────┘    └─────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### Key Benefits

| Benefit | Description |
|---------|-------------|
| **Centralized Control** | One platform for all AI interactions |
| **Complete Auditability** | Immutable, hash-chained audit logs |
| **Domain Expertise** | Specialized agents with institutional knowledge |
| **Human Oversight** | Configurable approval workflows |
| **Cost Optimization** | Intelligent routing reduces LLM costs 40-70% |
| **Compliance Built-In** | Guardrails prevent policy violations |
| **White-Label Ready** | Fully brandable for any organization |
| **Enterprise SSO** | OIDC/SAML integration (Azure AD, Okta, etc.) |
| **Grounded AI** | Responses cite authoritative sources |
| **Zero-Trust Security** | RBAC + ABAC + Database-level isolation |

### ROI Highlights

- **City of Cleveland Pilot**: 8,000 employees, projected **$1.2M annual savings**
- **April Parker Foundation**: 8 custom GPTs, **$1.38M projected annual value**
- **Average Enterprise**: **40-70% cost reduction** vs. direct OpenAI/Anthropic usage

---

# Platform Overview

## What is HAAIS AIOS?

HAAIS AIOS is an **AI Operating System** that sits between your users and AI language models. It provides:

1. **Intelligent Routing** - The Concierge agent understands user intent and routes to the right specialist
2. **Governed Responses** - Policies control what AI can and cannot say
3. **Institutional Knowledge** - Agents are trained on your documents and procedures
4. **Human Oversight** - Critical responses require human approval
5. **Complete Audit Trail** - Every interaction is logged for compliance

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  Concierge  │  │   Agents    │  │  Analytics  │  │  Settings   │ │
│  │    Chat     │  │  Management │  │  Dashboard  │  │   Panel     │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Router    │  │ Governance  │  │    HITL     │  │   Audit     │ │
│  │   Engine    │  │   Engine    │  │   Manager   │  │   Logger    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                           CORE SERVICES                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Agent     │  │  Knowledge  │  │    LLM      │  │   Multi-    │ │
│  │  Manager    │  │    Base     │  │   Router    │  │   Tenant    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         LLM PROVIDERS                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   OpenAI    │  │  Anthropic  │  │   Azure     │  │   Local     │ │
│  │  GPT-4/4o   │  │   Claude    │  │  OpenAI     │  │   Models    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

---

# Features & Functions

## 1. The Concierge (Intelligent Router)

### What It Does

The Concierge is the **front door** to your AI system. When a user asks a question, the Concierge:

1. **Understands Intent** - Classifies what the user is asking about
2. **Detects Risks** - Identifies sensitive content (PII, legal, financial)
3. **Routes Intelligently** - Directs to the best specialist agent
4. **Provides Warm Handoff** - Introduces the specialist with context

### How It Works

```
User: "I need to update my health insurance beneficiary"

Concierge Analysis:
├── Intent: Benefits enrollment change
├── Domain: HR
├── Risk: PII (beneficiary information)
└── Route: HR Assistant

Concierge Response:
"I'll connect you with our HR Assistant who specializes in benefits
and enrollment. They can help you update your beneficiary information."

[Handoff to HR Assistant with context]
```

### User Experience

1. User opens the Concierge chat
2. Types or speaks their question
3. Concierge identifies the right agent
4. User is seamlessly connected
5. Specialist agent responds with domain expertise

### Benefits

- **No Wrong Door** - Users don't need to know which department to contact
- **Consistent Experience** - Same interface for all inquiries
- **Context Preservation** - Specialist knows what user asked
- **Reduced Confusion** - No more "that's not my department"

---

## 2. Specialist Agents

### What They Are

Specialist Agents are AI assistants trained for specific domains. Each agent has:

| Component | Purpose |
|-----------|---------|
| **System Prompt** | Core instructions defining personality and role |
| **Capabilities** | What the agent CAN do |
| **Guardrails** | What the agent CANNOT do |
| **Knowledge Base** | Domain-specific documents and procedures |
| **Escalation Path** | Who to escalate to when needed |

### Example Agents

**HR Assistant**
- Answers benefits questions
- Explains leave policies
- Guides onboarding
- CANNOT: Discuss salaries, handle complaints

**Legal Advisor**
- Explains contract terms
- Provides policy guidance
- Reviews compliance questions
- CANNOT: Provide legal advice, approve contracts

**Finance Helper**
- Explains expense procedures
- Guides budget processes
- Answers payroll questions
- CANNOT: Approve expenditures, access accounts

**IT Support**
- Troubleshoots common issues
- Guides password resets
- Explains system access
- CANNOT: Access user accounts, change permissions

### How Agents Work

```
┌─────────────────────────────────────────────────────────┐
│                    AGENT PROCESSING                      │
│                                                          │
│  User Query                                              │
│      │                                                   │
│      ▼                                                   │
│  ┌─────────────────┐                                    │
│  │ Governance      │ → Check policies, detect risks     │
│  │ Evaluation      │                                    │
│  └────────┬────────┘                                    │
│           │                                              │
│           ▼                                              │
│  ┌─────────────────┐                                    │
│  │ Knowledge Base  │ → Retrieve relevant documents      │
│  │ Search          │                                    │
│  └────────┬────────┘                                    │
│           │                                              │
│           ▼                                              │
│  ┌─────────────────┐                                    │
│  │ LLM Generation  │ → Generate response with context   │
│  │ (with guardrails)│                                   │
│  └────────┬────────┘                                    │
│           │                                              │
│           ▼                                              │
│  ┌─────────────────┐                                    │
│  │ HITL Check      │ → Approval needed? Route to human  │
│  │                 │                                    │
│  └────────┬────────┘                                    │
│           │                                              │
│           ▼                                              │
│      Response to User                                    │
└─────────────────────────────────────────────────────────┘
```

### Managing Agents

**Creating an Agent:**
1. Navigate to Agents page
2. Click "Create Agent"
3. Fill in details:
   - Name and title
   - Domain category
   - Description
   - Capabilities (what it can do)
   - Guardrails (what it cannot do)
   - System prompt
4. Save and activate

**Editing an Agent:**
1. Click on agent card
2. Modify settings
3. Save changes
4. Changes take effect immediately

**Deactivating an Agent:**
1. Click agent settings
2. Set status to "Inactive"
3. Agent no longer receives queries

---

## 3. Knowledge Base

### What It Does

The Knowledge Base gives agents access to your organization's **institutional knowledge**:

- Policy documents
- Procedures manuals
- FAQ databases
- Website content
- Training materials

### How It Works

```
Document Upload
      │
      ▼
┌─────────────────┐
│  Text Extraction │ → Convert PDF/DOCX/HTML to text
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Chunking     │ → Split into semantic sections
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Embedding     │ → Convert to vector representations
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Vector Store   │ → Store in ChromaDB for search
└─────────────────┘
```

**When a user asks a question:**

```
User Query: "What's the vacation policy for employees with 5 years?"
                │
                ▼
┌─────────────────────────────────────────────────────────┐
│  Semantic Search                                         │
│  Find documents most similar to the query               │
│                                                          │
│  Results:                                                │
│  1. Employee_Handbook.pdf (Section 4.2 - Leave)  95%    │
│  2. HR_FAQ.md (Vacation Questions)               89%    │
│  3. Benefits_Guide.pdf (Time Off)                82%    │
└─────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────┐
│  Context Injection                                       │
│  Add relevant content to LLM prompt                     │
│                                                          │
│  "Based on the Employee Handbook Section 4.2:           │
│   Employees with 5+ years receive 20 days PTO..."       │
└─────────────────────────────────────────────────────────┘
                │
                ▼
        Accurate, Sourced Response
```

### Adding Knowledge

**Method 1: File Upload**
1. Go to agent's Knowledge Base tab
2. Click "Upload Document"
3. Select files (PDF, DOCX, MD, TXT)
4. Documents are processed automatically

**Method 2: Web Scraping**
1. Go to agent's Knowledge Base tab
2. Click "Add Web Source"
3. Enter URL
4. System fetches and processes content
5. Can schedule automatic refreshes

**Method 3: Onboarding Discovery**
1. Use Onboarding wizard
2. Enter organization's website
3. System crawls and extracts content
4. Review and approve documents

### Knowledge Base Features

| Feature | Description |
|---------|-------------|
| **Semantic Search** | Finds conceptually similar content, not just keywords |
| **Source Attribution** | Responses cite which document information came from |
| **Per-Agent Scoping** | Each agent only sees its relevant documents |
| **Shared Canon** | Some documents shared across all agents |
| **Auto-Refresh** | Web sources can update on schedule |
| **Version History** | Track document changes over time |

---

## 4. Governance Engine

### What It Does

The Governance Engine ensures AI responses comply with organizational policies:

- Enforces guardrails
- Detects sensitive content
- Routes high-risk queries for human review
- Blocks prohibited topics
- Applies domain-specific rules

### Governance Policies

**Constitutional Rules** (Apply to ALL agents)
```json
{
  "never_provide_legal_advice": true,
  "never_access_personal_data": true,
  "always_cite_sources": true,
  "escalate_safety_concerns": true
}
```

**Domain Rules** (Apply to specific domains)
```json
{
  "HR": {
    "prohibited_topics": ["individual_salaries", "terminations"],
    "require_approval": ["policy_changes", "benefits_exceptions"]
  },
  "Legal": {
    "default_hitl_mode": "DRAFT",
    "require_approval": ["contract_advice", "liability_questions"]
  }
}
```

### Risk Detection

The system automatically scans for:

| Risk Signal | Trigger | Action |
|-------------|---------|--------|
| **PII** | Names, SSN, addresses | Flag for review |
| **FINANCIAL** | Account numbers, transactions | Require approval |
| **LEGAL** | Contract terms, legal advice | Route to Legal |
| **CONFIDENTIAL** | Marked content | Block or escalate |
| **SAFETY** | Self-harm, violence | Immediate escalate |

### How Governance Works

```
User Query
    │
    ▼
┌────────────────────────────────────────┐
│         GOVERNANCE EVALUATION           │
│                                         │
│  1. Intent Classification               │
│     └── What is the user asking?       │
│                                         │
│  2. Risk Signal Detection              │
│     └── PII? Financial? Legal?         │
│                                         │
│  3. Policy Matching                    │
│     └── Which rules apply?             │
│                                         │
│  4. HITL Mode Determination            │
│     └── INFORM / DRAFT / ESCALATE      │
│                                         │
│  5. Guardrail Application              │
│     └── Add constraints to prompt      │
└────────────────────────────────────────┘
    │
    ▼
Governed Response
```

---

## 5. Human-in-the-Loop (HITL)

### What It Does

HITL ensures humans remain in control of AI outputs. Based on query sensitivity, responses can require human review before delivery.

### HITL Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| **INFORM** | Response sent immediately | Low-risk queries |
| **DRAFT** | Response saved for review | Moderate-risk, quality control |
| **EXECUTE** | Requires manager approval | High-stakes decisions |
| **ESCALATE** | Human takes over entirely | Complex or sensitive issues |

### Approval Workflow

```
┌─────────────────────────────────────────────────────────┐
│                  HITL WORKFLOW                           │
│                                                          │
│  Query Triggers DRAFT Mode                               │
│         │                                                │
│         ▼                                                │
│  ┌─────────────────┐                                    │
│  │ AI Generates    │                                    │
│  │ Draft Response  │                                    │
│  └────────┬────────┘                                    │
│           │                                              │
│           ▼                                              │
│  ┌─────────────────┐                                    │
│  │ Saved to        │ → User notified: "Under review"   │
│  │ Approval Queue  │                                    │
│  └────────┬────────┘                                    │
│           │                                              │
│           ▼                                              │
│  ┌─────────────────┐                                    │
│  │ Reviewer Gets   │                                    │
│  │ Notification    │                                    │
│  └────────┬────────┘                                    │
│           │                                              │
│           ├──────────────┐                              │
│           ▼              ▼                              │
│  ┌──────────────┐ ┌──────────────┐                     │
│  │   APPROVE    │ │    EDIT      │                     │
│  │              │ │  & APPROVE   │                     │
│  └──────┬───────┘ └──────┬───────┘                     │
│         │                │                              │
│         └────────┬───────┘                              │
│                  ▼                                       │
│         Response Delivered                               │
│            to User                                       │
└─────────────────────────────────────────────────────────┘
```

### Managing Approvals

**Approvals Dashboard** (`/approvals`)

- View pending approvals
- See query details and AI response
- Approve, edit, or reject
- Add comments for audit trail
- Filter by agent, priority, status

**Approval Actions:**

| Action | Result |
|--------|--------|
| **Approve** | Response sent as-is |
| **Edit & Approve** | Modified response sent |
| **Reject** | Query marked as rejected, user notified |
| **Escalate** | Forwarded to higher authority |

---

## 6. Multi-Tenant Architecture

### What It Does

Multi-tenancy allows a single HAAIS AIOS instance to serve **multiple organizations** with complete data isolation.

### Tenant Features

Each tenant gets:

| Feature | Description |
|---------|-------------|
| **Isolated Data** | Agents, knowledge, conversations are separate |
| **Custom Branding** | Own logo, colors, name |
| **Own Policies** | Independent governance rules |
| **Usage Quotas** | Configurable limits |
| **Separate Billing** | Track costs per tenant |

### Tenant Tiers

| Tier | Agents | API Calls/Month | Features |
|------|--------|-----------------|----------|
| **Free** | 5 | 1,000 | Basic |
| **Starter** | 15 | 10,000 | + Analytics |
| **Professional** | 50 | 100,000 | + HITL |
| **Enterprise** | Unlimited | Unlimited | + SSO, SLA |
| **Government** | Unlimited | Unlimited | + Compliance |

### Tenant Management

**Creating a Tenant:**
1. Go to Tenants page
2. Click "Create Tenant"
3. Enter organization details
4. Select tier
5. Configure initial settings

**Tenant Settings:**
- Default HITL mode
- Prohibited topics
- Approval requirements
- Escalation contacts
- Usage quotas

---

## 7. Analytics & Reporting

### Dashboard Overview

The Analytics Dashboard provides insights into:

- **Usage Metrics** - Queries, tokens, costs
- **Performance** - Response times, satisfaction
- **Governance** - Approvals, escalations, blocks
- **Trends** - Usage patterns over time

### Key Metrics

| Metric | Description |
|--------|-------------|
| **Total Queries** | Number of user interactions |
| **Queries by Agent** | Distribution across specialists |
| **Average Response Time** | Time to generate response |
| **HITL Rate** | % of queries requiring review |
| **Escalation Rate** | % of queries escalated to humans |
| **Token Usage** | LLM tokens consumed |
| **Estimated Cost** | Dollar cost of LLM usage |

### Reports

**Available Reports:**
- Daily usage summary
- Agent performance comparison
- Governance trigger analysis
- Cost breakdown by agent/tenant
- Trend analysis

**Export Options:**
- CSV download
- PDF report
- API access

---

## 8. Audit Trail

### What It Logs

Every interaction is logged with cryptographic integrity:

| Event | Data Captured |
|-------|---------------|
| **Query** | User ID, timestamp, text, agent, tenant |
| **Response** | Generated text, model used, tokens, grounding score |
| **Governance** | Policies triggered, HITL mode, authority basis |
| **Approval** | Reviewer, action, timestamp, modifications |
| **Authentication** | Login/logout, provider, IP address |
| **Configuration** | Policy changes, agent updates, settings |

### Hash-Chained Immutability

Audit records form a cryptographic chain:

```
Record 1 ──hash──► Record 2 ──hash──► Record 3 ...
```

**Tamper Detection:**
- Each record's hash includes the previous record's hash
- Any modification breaks the chain
- Verification API: `POST /audit/verify/{tenant_id}`

### Audit Features

- **Immutable Logs** - Database triggers prevent modification
- **Hash Verification** - Cryptographic tamper detection
- **Searchable** - Find specific interactions by event type, actor, time
- **Filterable** - By date, agent, user, severity, outcome
- **Exportable** - For compliance reporting

### Audit API Endpoints

```http
# Get chain status
GET /audit/status/{tenant_id}

# Verify chain integrity
POST /audit/verify/{tenant_id}

# Query audit logs
POST /audit/query
{
  "tenant_id": "cleveland",
  "event_types": ["agent_query"],
  "start_time": "2026-01-01T00:00:00Z"
}

# Get recent events
GET /audit/{tenant_id}/recent?limit=50
```

### Compliance Support

Supports requirements for:
- **GDPR** - Data subject access requests, processing records
- **HIPAA** - Healthcare audit requirements, access logging
- **SOC 2** - Security audit trails, integrity verification
- **FedRAMP** - Government compliance, immutable records

---

## 9. Voice Interface

### What It Does

Voice capabilities allow users to speak queries and hear responses:

- **Speech-to-Text** - Convert voice to text queries
- **Text-to-Speech** - Read responses aloud
- **Barge-In** - Interrupt responses mid-stream
- **Wake Word** - "Hey Phoenix" activation (optional)

### Supported Providers

| Provider | STT | TTS | Features |
|----------|-----|-----|----------|
| **Deepgram** | ✓ | - | Fast, accurate transcription |
| **ElevenLabs** | - | ✓ | Natural voice synthesis |
| **Azure Speech** | ✓ | ✓ | Enterprise-grade |
| **OpenAI Whisper** | ✓ | ✓ | High accuracy |

### Voice Workflow

```
┌─────────────────────────────────────────────────────────┐
│                   VOICE PIPELINE                         │
│                                                          │
│  User Speaks                                             │
│       │                                                  │
│       ▼                                                  │
│  ┌─────────────┐                                        │
│  │  STT        │ → Convert speech to text               │
│  │  (Deepgram) │                                        │
│  └──────┬──────┘                                        │
│         │                                                │
│         ▼                                                │
│  ┌─────────────┐                                        │
│  │  Agent      │ → Process query, generate response     │
│  │  Processing │                                        │
│  └──────┬──────┘                                        │
│         │                                                │
│         ▼                                                │
│  ┌─────────────┐                                        │
│  │  TTS        │ → Convert response to speech           │
│  │ (ElevenLabs)│                                        │
│  └──────┬──────┘                                        │
│         │                                                │
│         ▼                                                │
│    Audio Playback                                        │
└─────────────────────────────────────────────────────────┘
```

---

## 10. Onboarding System

### What It Does

The Onboarding System automates setup for new clients:

1. **Discovery** - Crawls client website to find departments
2. **Analysis** - Identifies organizational structure
3. **Generation** - Creates agents with appropriate prompts
4. **Population** - Builds knowledge base from web content

### Onboarding Workflow

```
Step 1: Enter Website URL
        │
        ▼
Step 2: Discovery Crawl (5-15 minutes)
        ├── Find department pages
        ├── Identify key personnel
        ├── Extract contact info
        └── Map organizational structure
        │
        ▼
Step 3: Review Discovered Departments
        ├── Check departments to include
        ├── Uncheck departments to skip
        └── Add any missing departments
        │
        ▼
Step 4: Generate Agents
        ├── Create agent configurations
        ├── Generate system prompts
        ├── Set appropriate guardrails
        └── Create Concierge router
        │
        ▼
Step 5: Populate Knowledge Base
        ├── Scrape department pages
        ├── Process documents
        ├── Generate embeddings
        └── Index for search
        │
        ▼
Step 6: Review & Activate
        ├── Test each agent
        ├── Verify responses
        ├── Adjust as needed
        └── Go live!
```

### Time to Deploy

| Organization Size | Discovery | Setup | Total |
|-------------------|-----------|-------|-------|
| Small (5 depts) | 5 min | 30 min | ~1 hour |
| Medium (15 depts) | 15 min | 1 hour | ~2 hours |
| Large (30+ depts) | 30 min | 2 hours | ~4 hours |

---

# User Interface Guide

## Navigation

### Main Menu

| Menu Item | Function |
|-----------|----------|
| **Dashboard** | Overview and quick stats |
| **Chat** | Concierge conversation interface |
| **Agents** | Manage AI agents |
| **Templates** | Pre-built agent templates |
| **Analytics** | Usage reports and metrics |
| **Approvals** | HITL approval queue |
| **Audit** | Compliance audit logs |
| **Tenants** | Multi-tenant management |
| **Settings** | System configuration |

---

## Chat Interface

### Starting a Conversation

1. Click **"Chat"** in navigation
2. Type your question in the input box
3. Press Enter or click Send
4. View response from appropriate agent

### Voice Input

1. Click the **microphone icon**
2. Speak your question
3. Click again to stop recording
4. Question is transcribed and sent

### Conversation Features

- **Agent Handoffs** - See when you're transferred to a specialist
- **Source Citations** - View which documents informed the response
- **Feedback** - Rate responses for quality improvement
- **History** - Previous conversations are saved

---

## Agents Page

### Agent List View

- See all configured agents
- Status indicators (Active/Inactive)
- Domain categories
- Quick actions (Edit, Duplicate, Delete)

### Agent Detail View

**Basic Info Tab**
- Name, title, description
- Domain category
- External GPT URL (if applicable)

**System Prompt Tab**
- Full instructions for the agent
- Personality and tone guidelines
- Response formatting rules

**Guardrails Tab**
- What the agent CANNOT do
- Prohibited topics
- Escalation triggers

**Knowledge Base Tab**
- Uploaded documents
- Web sources
- Document statistics

### Creating an Agent

1. Click **"Create Agent"**
2. Fill in required fields:
   - Unique ID (e.g., `hr-assistant`)
   - Display name
   - Domain category
3. Write system prompt
4. Define capabilities and guardrails
5. Click **"Save"**

---

## Settings Page

### LLM Configuration

- **Provider Selection** - OpenAI, Anthropic, Azure
- **Model Selection** - GPT-4, Claude, etc.
- **Temperature** - Creativity level (0.0-1.0)
- **Max Tokens** - Response length limit

### Branding

- **App Name** - Displayed in header
- **Logo** - Upload custom logo
- **Colors** - Primary and accent colors
- **Footer Text** - Copyright and credits

### Notifications

- **Email Alerts** - Escalation notifications
- **Approval Reminders** - Pending review alerts
- **Usage Warnings** - Quota threshold alerts

---

# API Reference

## Base URL

```
http://localhost:8000
```

## Authentication

**Production (OIDC/SAML):**
```
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
```

**Development (Header-based):**
```
X-Tenant-ID: tenant-123
X-User-ID: dev@local
```

Note: Header auth is disabled in production mode.

## Key Endpoints

### Health Check
```http
GET /health
```
Returns system status.

### Agents

```http
# List all agents
GET /agents

# Get agent details
GET /agents/{agent_id}

# Create agent
POST /agents

# Update agent
PUT /agents/{agent_id}

# Delete agent
DELETE /agents/{agent_id}

# Query agent
POST /agents/{agent_id}/query
{
  "query": "What is the vacation policy?",
  "use_knowledge_base": true
}
```

### Knowledge Base

```http
# Upload document
POST /agents/{agent_id}/knowledge/upload

# Add web source
POST /agents/{agent_id}/knowledge/web
{
  "url": "https://example.com/policies"
}

# List documents
GET /agents/{agent_id}/knowledge
```

### Governance

```http
# Evaluate governance
POST /governance/evaluate
{
  "text": "Query text",
  "tenant_id": "tenant-123",
  "role": "employee",
  "department": "HR"
}
```

### Tenants

```http
# List tenants
GET /tenants

# Create tenant
POST /tenants
{
  "name": "Organization Name",
  "tier": "enterprise",
  "admin_email": "admin@org.com"
}

# Update tenant settings
PUT /tenants/{tenant_id}/settings
```

### Full API Documentation

Interactive API docs available at:
```
http://localhost:8000/docs
```

---

# Glossary

| Term | Definition |
|------|------------|
| **Agent** | An AI assistant configured for a specific domain |
| **Concierge** | The router agent that directs users to specialists |
| **Governance** | Policies controlling AI behavior |
| **Guardrails** | Restrictions on what an agent can do |
| **HITL** | Human-in-the-Loop - requiring human approval |
| **Knowledge Base** | Documents an agent can reference |
| **Tenant** | An organization using the platform |
| **Vector Embedding** | Numeric representation of text for search |
| **RAG** | Retrieval-Augmented Generation |

---

# Support

## Getting Help

- **Documentation**: `/docs` folder
- **API Reference**: http://localhost:8000/docs
- **Email**: support@haais.ai

## Reporting Issues

Include:
1. Steps to reproduce
2. Expected behavior
3. Actual behavior
4. Screenshots if applicable
5. Browser/OS information

---

# Appendix: Security & Compliance

## Enterprise Security Features (P0 Controls)

HAAIS AIOS implements enterprise-grade security controls for regulated environments.

### 1. Enterprise Authentication

**OIDC/SAML Single Sign-On**

AIOS integrates with your existing identity provider:

| Provider | Support |
|----------|---------|
| **Azure AD** | Full OIDC support |
| **Okta** | Full OIDC support |
| **Auth0** | Full OIDC support |
| **Generic OIDC** | Any compliant provider |
| **SAML 2.0** | Enterprise SSO |

**How It Works:**
1. User accesses AIOS
2. Redirected to your IdP (Azure AD, Okta, etc.)
3. User authenticates with corporate credentials
4. JWT token issued with user claims
5. AIOS validates token and extracts:
   - User ID
   - Tenant ID
   - Roles and groups
   - Department

**Development Mode:**
- Header-based auth (`X-Tenant-ID`) for local development
- Automatically blocked in production mode

### 2. Authorization (RBAC + ABAC)

**Role-Based Access Control (RBAC)**

Pre-defined roles with granular permissions:

| Role | Permissions |
|------|-------------|
| **Admin** | Full system access |
| **Tenant Admin** | Manage agents, policies, approvals |
| **Manager** | Review approvals, view analytics |
| **Employee** | Query agents, view responses |
| **Viewer** | Read-only access |

**Attribute-Based Access Control (ABAC)**

Dynamic policies based on user attributes:

```
Example: Engineering department can delete agents
Condition: user.department == "Engineering"
Permission: agent:delete
Effect: ALLOW
```

**Permissions Include:**
- `agent:read`, `agent:write`, `agent:query`, `agent:delete`
- `kb:read`, `kb:write`, `kb:delete`
- `policy:read`, `policy:write`, `policy:approve`
- `approval:read`, `approval:review`, `approval:override`
- `audit:read`, `audit:export`
- `tenant:admin`, `system:admin`

### 3. Immutable Audit Logging

**Hash-Chained Audit Trail**

Every interaction is logged with cryptographic integrity:

```
Record N:
├── sequence_number: 42
├── tenant_id: "cleveland"
├── event_type: "agent_query"
├── actor_id: "jane.doe@city.gov"
├── action: "Queried HR agent"
├── payload: {...}
├── previous_hash: "a1b2c3..."  ← Links to Record N-1
└── record_hash: "d4e5f6..."    ← Computed from content
```

**Tamper Detection:**
- Chain verification detects any modification
- Cannot delete records (append-only)
- Database triggers prevent UPDATE/DELETE

**Audit Events Tracked:**
- Agent queries and responses
- Authentication events
- Configuration changes
- Governance decisions
- Approval workflow actions

### 4. Grounded AI Enforcement

**Source Attribution Requirements**

AI responses must be backed by authoritative sources:

| Grounding Score | Action |
|-----------------|--------|
| 0.8 - 1.0 | Deliver immediately |
| 0.5 - 0.8 | Deliver with warning |
| 0.0 - 0.5 | **Block** - insufficient verification |

**Fallback Behavior:**

When grounding score is too low:
```
"I don't have sufficient verified information to answer
this question. Please consult an authoritative source
or contact support for assistance."
```

**Authority Levels:**
1. **Constitutional** - Immutable rules, laws
2. **Statutory** - Regulations, ordinances
3. **Organizational** - Company policies
4. **Departmental** - Team procedures
5. **Operational** - Day-to-day guidance

### 5. Tenant Data Isolation

**PostgreSQL Row-Level Security (RLS)**

Data isolation enforced at the database level:

```sql
-- Every query automatically filtered
SELECT * FROM agents WHERE tenant_id = current_tenant_id()
```

**Benefits:**
- Application bugs cannot leak data
- Even direct SQL access is restricted
- Automatic enforcement on all queries

## Data Security

- All data encrypted at rest
- HTTPS required for production
- API keys stored securely
- No data sent to third parties (except LLM providers)
- RLS prevents cross-tenant data access

## Compliance Support

HAAIS AIOS is **designed to support** deployment in regulated environments:

| Framework | AIOS Support |
|-----------|--------------|
| **SOC 2** | Access controls, audit logging, encryption |
| **HIPAA** | PHI detection, audit trails, access controls |
| **GDPR** | Data access logging, retention policies, export |
| **FedRAMP** | Architecture supports certification path |

**Note:** Certification requires third-party audits and organization-specific implementations. See `docs/compliance/COMPLIANCE_POSITIONING.md` for detailed framework mappings.

## LLM Data Handling

- Queries sent to LLM providers (OpenAI/Anthropic)
- No training on your data (per provider policies)
- Option for Azure OpenAI (data stays in your Azure tenant)
- Local LLM support available for air-gapped deployments

---

# Appendix: API Authentication

## Production Authentication

```http
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
```

JWT token from your OIDC provider containing:
- `sub`: User ID
- `tenant_id`: Organization ID
- `roles`: User roles
- `email`: User email

## Development Authentication

```http
X-Tenant-ID: cleveland
X-User-ID: developer@local
X-User-Role: admin
```

**Note:** Header auth is automatically disabled in production mode.

---

*HAAIS AIOS User Manual v1.1*
*© 2026 DEF1LIVE LLC / HAAIS*
*All Rights Reserved*
