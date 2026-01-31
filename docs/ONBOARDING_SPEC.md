# aiOS Municipal Onboarding System Specification

## Overview

The aiOS Onboarding System automates the deployment of HAAIS-governed AI agents for any municipality. Given a city website URL, it discovers organizational structure, catalogs open data sources, and generates a complete AI deployment.

## System Flow

```
Query Input → Organization Resolver → Intent Parsing → Discovery → Candidate Selection → Manifest Generation → Deployment
```

### Query Types Supported

| Query Type | Example | Resolution |
|------------|---------|------------|
| Direct URL | `https://clevelandohio.gov` | Pass through |
| Organization Name | `Cleveland` | KNOWN_ORGANIZATIONS lookup |
| Intent Query | `IBM corporate leadership global` | Resolver + intent extraction |
| Domain | `clevelandohio.gov` | Auto-add https:// |

## Module Architecture

### Module 0: Organization Resolver (NEW)
**Purpose:** Resolve organization names and intent queries to crawlable URLs

**Input:** Raw query (URL, org name, or intent query)

**Output:** Resolved URL with intent metadata
```json
{
  "resolved_url": "https://ibm.com",
  "organization": "IBM",
  "intent": ["leadership", "global"],
  "priority_paths": ["/leadership", "/executives", "/about/leadership"]
}
```

**Features:**
- KNOWN_ORGANIZATIONS dictionary (50+ entries)
- Intent keyword extraction (leadership, team, careers, investors, etc.)
- Priority path generation based on intent
- Fallback to web search for unknown organizations

**Location:** `packages/onboarding/resolver.py`

---

### Module 1: Discovery Engine
**Purpose:** Crawl city/organization websites and extract organizational intelligence

**Input:** Resolved URL with optional intent and priority paths

**Output:** Structured JSON organizational map
```json
{
  "municipality": {
    "name": "City of Cleveland",
    "state": "Ohio",
    "population": 372624,
    "website": "https://clevelandohio.gov"
  },
  "executive": {
    "mayor": {
      "name": "Justin M. Bibb",
      "title": "Mayor",
      "office": "Office of the Mayor",
      "contact": {...}
    },
    "chief_officers": [...]
  },
  "departments": [
    {
      "id": "public-health",
      "name": "Cleveland Department of Public Health",
      "director": "Dr. David Margolius",
      "title": "Director of Public Health",
      "url": "https://clevelandohio.gov/public-health",
      "contact": {...},
      "suggested_template": "public-health"
    }
  ],
  "data_portals": [
    {
      "type": "socrata",
      "url": "https://data.clevelandohio.gov",
      "api_endpoint": "https://data.clevelandohio.gov/resource/"
    }
  ],
  "governance_docs": [
    {
      "type": "charter",
      "title": "City Charter",
      "url": "..."
    }
  ]
}
```

**Key Features:**
- Respects robots.txt
- Rate limiting (polite crawling)
- Pattern matching for common municipal site structures
- Executive/department detection via title patterns
- Open data portal auto-detection
- **Intent-based priority crawling** - Prioritizes paths matching user intent
- **Shallow crawl with candidate selection** - User reviews candidates before deep crawl
- **Controlled discovery workflow** - Step-by-step with human approval

**Discovery Modes:**
| Mode | Depth | Use Case |
|------|-------|----------|
| Shallow | Homepage + priority paths | Initial candidate discovery |
| Targeted | Intent-specific paths only | "IBM leadership" queries |
| Full | Complete site crawl | Comprehensive onboarding |

---

### Module 2: Open Data Catalog Extractor
**Purpose:** Connect to detected data portals and inventory all datasets

**Supported Platforms:**
- Socrata (SODA API)
- CKAN
- ArcGIS Hub / Open Data
- OpenDataSoft

**Output:** Dataset catalog
```json
{
  "portal": {
    "type": "socrata",
    "url": "https://data.clevelandohio.gov",
    "dataset_count": 147
  },
  "datasets": [
    {
      "id": "abc123",
      "name": "311 Service Requests",
      "description": "All 311 service requests...",
      "category": "Government",
      "tags": ["311", "service requests", "complaints"],
      "formats": ["json", "csv", "geojson"],
      "update_frequency": "daily",
      "record_count": 245000,
      "api_endpoint": "https://data.clevelandohio.gov/resource/abc123.json",
      "suggested_department": "311"
    }
  ]
}
```

---

### Module 3: Configuration Interface
**Purpose:** Present discovered data for user selection and customization

**Sections:**
- **A: Core Infrastructure** (always included)
  - Concierge Router
  - Governance Framework
  - Analytics Module

- **B: Executive Office**
  - Mayor's Office Agent
  - Chief of Staff Agent

- **C: Departments** (discovered)
  - Each department with template dropdown
  - Toggle enable/disable
  - Custom name override

- **D: Open Data Sources**
  - Grouped by suggested department
  - Toggle include/exclude
  - Sync frequency selection

- **E: GIS Services**
  - Map layers
  - Parcel data

- **F: External APIs**
  - Weather services
  - Transit APIs

- **G: Manual Import**
  - Upload zone for PDFs, policy docs

- **H: Sync Configuration**
  - Refresh schedules
  - Notification settings

---

### Module 4: Manifest Generator
**Purpose:** Convert user selections into deployable agent configurations

**Output Structure:**
```
deployment/
├── agents/
│   ├── concierge.json
│   ├── public-health.json
│   ├── hr.json
│   └── ...
├── governance/
│   ├── policies.json
│   └── guardrails.json
├── routing/
│   └── concierge-rules.json
├── data-sources/
│   ├── socrata-config.json
│   └── sync-schedule.json
└── manifest.json
```

**Agent Config Template:**
```json
{
  "id": "public-health",
  "name": "Dr. David Margolius",
  "title": "Director of Public Health (CDPH)",
  "domain": "PublicHealth",
  "description": "...",
  "system_prompt": "...",
  "capabilities": [...],
  "guardrails": [...],
  "escalates_to": "Public Health Leadership",
  "data_sources": ["abc123", "def456"],
  "governance": {
    "sensitivity": "high",
    "hitl_mode": "DRAFT",
    "pii_protection": true
  }
}
```

---

### Module 5: Deployment Orchestrator
**Purpose:** Execute the deployment sequence with progress tracking

**Deployment Steps:**
1. Validate manifest
2. Provision tenant (if new)
3. Deploy governance framework
4. Create agents from configs
5. Connect data sources
6. Run initial data sync
7. Configure Concierge routing
8. Execute smoke tests
9. Generate completion report

**Progress Events (WebSocket):**
```json
{
  "step": 4,
  "total_steps": 9,
  "status": "in_progress",
  "message": "Creating agent: Public Health",
  "progress_percent": 44
}
```

---

## Tech Stack

- **Backend:** Python/FastAPI (existing)
- **Frontend:** Next.js/React (existing)
- **Crawler:** BeautifulSoup + httpx (async)
- **Task Queue:** Background threads or Celery
- **Database:** JSON file storage (existing) → PostgreSQL (future)
- **WebSocket:** FastAPI WebSocket for progress

---

## API Endpoints

### Discovery
- `POST /onboarding/discover` - Start discovery for URL
- `GET /onboarding/discover/{job_id}` - Get discovery status/results

### Catalog
- `GET /onboarding/catalog/{discovery_id}` - Get data catalog for discovery

### Configuration
- `POST /onboarding/config` - Save configuration selections
- `GET /onboarding/config/{id}` - Get saved configuration
- `POST /onboarding/config/{id}/validate` - Validate before deploy

### Deployment
- `POST /onboarding/deploy` - Start deployment
- `GET /onboarding/deploy/{job_id}` - Get deployment status
- `WS /onboarding/deploy/{job_id}/progress` - WebSocket for live updates

---

## Department Template Mapping

### Municipal Templates (Implemented)

| Discovered Pattern | Template ID | Domain | Status |
|-------------------|-------------|--------|--------|
| Public Health, CDPH, Health Dept | `public-health` | PublicHealth | ✅ Built |
| Human Resources, HR, Personnel | `hr` | HR | ✅ Built |
| Finance, Treasury, Fiscal | `finance` | Finance | ✅ Built |
| Building, Housing, Permits | `building` | Building | ✅ Built |
| 311, Citizen Services | `311` | 311 | ✅ Built |
| Planning, Development, Economic | `strategy` | Strategy | ✅ Built |
| Police, Public Safety | `public-safety` | PublicSafety | ✅ Built |
| Parks, Recreation | `parks` | Parks | ✅ Built |
| Public Works, Streets, Utilities | `public-works` | PublicWorks | ✅ Built |

### Missing Municipal Templates (Gaps)

| Pattern | Template ID | Domain | Priority |
|---------|-------------|--------|----------|
| Fire, Emergency Services | `fire` | Fire | HIGH |
| Law, Legal, City Attorney | `law` | Legal | HIGH |
| IT, Technology, Digital | `it` | Technology | MEDIUM |
| Communications, Public Affairs | `communications` | Comms | MEDIUM |

### Enterprise Templates (Not Built)

Enterprise discovery requires different templates:

| Pattern | Template ID | Domain | Status |
|---------|-------------|--------|--------|
| Human Resources | `enterprise-hr` | HR | ❌ Not Built |
| Finance, Accounting | `enterprise-finance` | Finance | ❌ Not Built |
| Legal, Compliance | `enterprise-legal` | Legal | ❌ Not Built |
| IT, Engineering | `enterprise-it` | Technology | ❌ Not Built |
| Sales, Marketing | `enterprise-sales` | Sales | ❌ Not Built |
| Customer Support | `enterprise-support` | Support | ❌ Not Built |

---

## Implementation Sequence

1. **Phase 1:** Discovery Engine (crawler + org extraction)
2. **Phase 2:** Data Portal Detection + Catalog
3. **Phase 3:** Configuration API
4. **Phase 4:** Configuration UI
5. **Phase 5:** Manifest Generator
6. **Phase 6:** Deployment Orchestrator
7. **Phase 7:** Integration Testing

---

## Success Criteria

- [x] Can discover Cleveland's org structure from URL
- [x] Detects data.clevelandohio.gov and catalogs datasets
- [ ] Configuration UI renders all discovered items
- [x] Generated manifests match HAAIS schema
- [x] Deployment creates functional agents
- [ ] End-to-end flow completes in < 10 minutes
- [x] Organization resolver handles name queries (e.g., "Cleveland")
- [x] Intent parsing extracts keywords (e.g., "leadership", "global")
- [ ] Enterprise templates support corporate discovery
- [ ] Extraction quality filters irrelevant content

---

## Known Issues & Gaps

### Extraction Quality Issues

1. **Blind Keyword Matching**: Currently matches keywords without URL path filtering
2. **No Page Type Detection**: Cannot distinguish leadership pages from news articles
3. **False Positives**: News sites like CNN.com return article content instead of organizational data

### Template Coverage Gaps

1. **Missing Municipal**: fire, law, it, communications
2. **No Enterprise Templates**: Corporate discovery not supported
3. **Routing Keywords Too Narrow**: May miss department matches

### Recommended Improvements

1. Add URL path filtering (e.g., exclude `/news/`, `/blog/`, `/article/`)
2. Implement page type detection (leadership vs news vs product)
3. Build enterprise template library
4. Expand routing keywords for better matching
