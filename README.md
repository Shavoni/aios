# AIOS - AI Operating System

**Enterprise AI Governance Platform for Multi-Agent Orchestration**

AIOS is a full-stack platform that provides centralized governance, routing, and management for AI agents across an organization. Built for enterprise deployments, it ensures consistent policies, human oversight, and seamless integration with existing AI tools.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)

---

## Overview

AIOS serves as the **intelligent control plane** for enterprise AI deployments, providing:

- **Unified Governance** - Apply consistent policies across all AI agents
- **Smart Routing** - Automatically route requests to the right specialist agent
- **Human-in-the-Loop** - Configurable approval workflows for sensitive operations
- **Multi-Platform Support** - Govern agents from ChatGPT, Copilot, N8N, and custom builds
- **Knowledge Management** - RAG-powered knowledge bases per agent
- **Complete Audit Trail** - Every interaction logged for compliance

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AIOS Platform                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Dashboard  │  │  Concierge  │  │    API      │              │
│  │   (Next.js) │  │    Chat     │  │  (FastAPI)  │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│  ┌──────┴────────────────┴────────────────┴──────┐              │
│  │              Governance Engine                 │              │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐         │              │
│  │  │ Policies│ │  HITL   │ │ Routing │         │              │
│  │  └─────────┘ └─────────┘ └─────────┘         │              │
│  └───────────────────────────────────────────────┘              │
│         │                │                │                      │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐              │
│  │   Agent 1   │  │   Agent 2   │  │   Agent N   │              │
│  │  (Finance)  │  │    (HR)     │  │  (Custom)   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Features

### Agent Management
- Create, configure, and deploy AI agents with custom system prompts
- Per-agent knowledge bases with document upload and web scraping
- Test console for validating agent responses
- GPT/Copilot integration via external URLs

### Intelligent Routing
- **Concierge Agent** - Single entry point that routes to specialists
- Intent classification and domain detection
- Automatic agent selection based on query analysis

### Governance & Compliance
- Constitutional and departmental policy rules
- Risk signal detection (PII, legal, financial)
- Configurable HITL modes: AUTO, DRAFT, REVIEW, ESCALATE
- Complete audit logging

### Onboarding Wizard
- Website discovery to auto-detect organization structure
- LLM-powered agent suggestions based on discovered services
- One-click deployment with human approval

### Template System
- Save entire configurations as reusable templates
- Load templates to quickly replicate setups
- Pre-built templates for common deployments

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key (or Anthropic/local LLM)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Shavoni/aios.git
   cd aios
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Start the backend**
   ```bash
   python run_api.py
   ```
   API will be available at `http://localhost:8000`

5. **Set up frontend**
   ```bash
   cd web
   npm install
   npm run dev
   ```
   Dashboard will be available at `http://localhost:3000`

### Environment Variables

```env
# LLM Provider (choose one)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Or use local LLM
OLLAMA_BASE_URL=http://localhost:11434

# Optional
LLM_PROVIDER=openai  # openai, anthropic, or local
DEFAULT_MODEL=gpt-4o
```

---

## Usage

### Dashboard

Access the web dashboard at `http://localhost:3000`:

| Page | Description |
|------|-------------|
| **Dashboard** | Overview with KPIs, health status, recent activity |
| **Agents** | Create/manage agents, upload knowledge, test responses |
| **Approvals** | Review pending HITL items and discovered agents |
| **Templates** | Browse pre-built templates, save/load configurations |
| **Analytics** | Usage metrics, cost tracking, performance data |
| **Settings** | API keys, governance policies, system reset |

**Want to customize the UI?** See the [UI Development Guide](docs/UI_DEVELOPMENT_GUIDE.md) for comprehensive documentation on the frontend architecture, component library, theming, and how to build custom pages.

### Concierge Chat

Access the public-facing chat interface at `http://localhost:3000/chat`:

- Single entry point for all AI services
- Automatic routing to specialist agents
- Agent directory sidebar
- Conversation history

### API Endpoints

Base URL: `http://localhost:8000`

#### Core Endpoints

```
GET  /health                    - Health check
GET  /agents                    - List all agents
POST /agents                    - Create agent
POST /agents/{id}/query         - Query an agent
POST /agents/route              - Route to best agent
```

#### Governance

```
POST /governance/evaluate       - Evaluate policies
GET  /hitl/queue                - Get pending approvals
POST /hitl/queue/{id}/approve   - Approve item
```

#### System

```
POST /system/reset              - Reset for new client
POST /system/export-template    - Save configuration
POST /system/import-template    - Load configuration
```

Full API documentation available at `http://localhost:8000/docs`

---

## Project Structure

```
aios/
├── packages/
│   ├── api/              # FastAPI endpoints
│   ├── core/             # Business logic
│   │   ├── agents/       # Agent management
│   │   ├── governance/   # Policy engine
│   │   ├── hitl/         # Human-in-the-loop
│   │   ├── knowledge/    # RAG & embeddings
│   │   ├── llm/          # LLM adapters
│   │   └── router/       # Intent routing
│   ├── onboarding/       # Discovery & deployment
│   └── kb/               # Knowledge base tools
├── web/                  # Next.js frontend
│   └── src/
│       ├── app/          # Pages (App Router)
│       ├── components/   # React components
│       └── lib/          # Utilities & API client
├── templates/            # Pre-built configurations
├── docs/                 # Documentation
└── tests/                # Test suite
```

---

## Deployment Templates

AIOS includes pre-built templates for rapid deployment:

| Template | Description | Agents |
|----------|-------------|--------|
| **Cleveland Municipal** | City government services | 10 |
| **Generic City** | Adaptable municipal template | 8 |
| **Minimal** | Basic setup for customization | 2 |

### Creating Custom Templates

1. Configure your agents in the dashboard
2. Go to **Agents** → **Save as Template**
3. Enter a name and description
4. Template saved to `data/templates/`

### Loading Templates

1. Go to **Templates** → **Saved** tab
2. Select a template
3. Choose **Replace** or **Merge** mode
4. Click **Load Template**

---

## Configuration

### Governance Policies

Policies are defined in `data/governance_policies.json`:

```json
{
  "constitutional_rules": [
    {
      "id": "public-statement-draft",
      "trigger": "audience == 'public'",
      "action": "DRAFT",
      "description": "Public communications require review"
    }
  ],
  "department_rules": {
    "HR": [
      {
        "id": "hr-employment-review",
        "trigger": "task == 'employment_action'",
        "action": "REVIEW"
      }
    ]
  }
}
```

### HITL Modes

| Mode | Behavior |
|------|----------|
| `AUTO` | Response delivered immediately |
| `DRAFT` | Response saved as draft for review |
| `REVIEW` | Human must approve before delivery |
| `ESCALATE` | Routed to supervisor/specialist |

---

## Development

### Running Tests

```bash
# Backend tests
pytest tests/ -v

# Frontend tests
cd web && npm test
```

### Code Style

```bash
# Python
ruff check packages/
ruff format packages/

# TypeScript
cd web && npm run lint
```

### Adding a New Agent Type

1. Create agent via API or dashboard
2. Configure system prompt and guardrails
3. Upload knowledge documents
4. Test in the console
5. Enable for production

---

## Roadmap

- [ ] Authentication & SSO integration
- [ ] Docker Compose deployment
- [ ] Kubernetes Helm chart
- [ ] Azure AD integration
- [ ] Slack/Teams bot connectors
- [ ] Advanced analytics dashboard
- [ ] Multi-language support

---

## FAQ

### What is AIOS?

AIOS is an **Enterprise AI Governance Platform** that helps organizations manage and orchestrate multiple AI agents. It provides centralized control, routing, and compliance for AI deployments.

### Can AIOS help me build professional UIs?

AIOS includes a **production-ready professional UI** built with Next.js 16, React 19, and shadcn/ui. While AIOS is not a UI builder tool, you can:

✅ Study the codebase as a reference implementation  
✅ Customize and extend the existing UI components  
✅ Use the same professional tech stack for your projects  
✅ Learn modern frontend development patterns  

See the [UI Development Guide](docs/UI_DEVELOPMENT_GUIDE.md) for comprehensive documentation.

### What can I build with AIOS?

AIOS is designed for:
- **Enterprise AI deployments** across organizations
- **Multi-agent systems** with centralized governance
- **Municipal/government** AI services
- **Corporate AI gateways** with policy compliance

### Do I need coding experience?

- **End Users**: No coding required - use the dashboard and chat interface
- **Administrators**: Basic configuration via web UI
- **Developers**: Python/TypeScript knowledge helpful for customization

### How much does it cost?

AIOS is **open source and free** (MIT License). You only pay for:
- LLM API costs (OpenAI, Anthropic, or free with local models)
- Hosting/infrastructure costs

---

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support

- **Documentation**: [docs/INDEX.md](docs/INDEX.md) - Full documentation library
- **UI Development**: [docs/UI_DEVELOPMENT_GUIDE.md](docs/UI_DEVELOPMENT_GUIDE.md) - Frontend customization guide
- **Issues**: [GitHub Issues](https://github.com/Shavoni/aios/issues)
- **Email**: support@haais.io

---

## About

AIOS is developed by **HAAIS (Human-AI Augmented Intelligence Systems)** as part of the Cleveland API Gateway initiative, in partnership with CGI.

**Built with:**
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [Next.js](https://nextjs.org/) - Frontend framework
- [LangChain](https://langchain.com/) - LLM orchestration
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [shadcn/ui](https://ui.shadcn.com/) - UI components
