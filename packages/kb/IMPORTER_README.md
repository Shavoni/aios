# HAAIS Public Source Importer

Enterprise-grade module for importing public city data sources into the HAAIS Knowledge Base.

## Features

- **Web Page Import**: Fetch HTML pages, strip navigation/footers, convert to Markdown
- **Socrata Open Data**: Pull dataset metadata from Socrata-powered open data portals
- **Legistar Legislation**: Import legislation, sponsors, and voting records
- **SHA256 Change Detection**: Only update files when content actually changes
- **YAML Frontmatter**: Full audit trail with source URLs and timestamps
- **Rate Limiting**: Respectful crawling with configurable limits
- **Retry Logic**: Exponential backoff for resilient fetching
- **robots.txt Compliance**: Respects site access rules

## Quick Start

```bash
# Navigate to KB package
cd packages/kb

# Install dependencies
npm install

# Dry run (see what would be imported without making changes)
npm run import:public:dry

# Import all public sources
npm run import:public

# Ingest into Supabase
npm run ingest:md kb_sources/citywide_public dept-citywide citywide public citywide_public
```

## Commands

| Command | Description |
|---------|-------------|
| `npm run import:public` | Import all configured sources |
| `npm run import:public:dry` | Dry run (no file changes) |
| `npm run import:socrata` | Import only Socrata data |
| `npm run import:legistar` | Import only Legistar legislation |
| `npm run import:web` | Import only web pages |

## Configuration

Configuration files are stored in `configs/`. See `cleveland.config.json` for a complete example.

### Configuration Schema

```json
{
  "version": "1.0",
  "publisher": "City of Cleveland",
  "department": "dept-citywide",
  "refreshCadence": "weekly",
  "outputBaseDir": "kb_sources/citywide_public",
  "httpSettings": {
    "maxRetries": 3,
    "retryDelayMs": 1000,
    "timeoutMs": 30000,
    "rateLimit": 2,
    "respectRobotsTxt": true
  },
  "webPages": [...],
  "socrata": {...},
  "legistar": {...}
}
```

### Web Pages Configuration

```json
{
  "url": "https://example.gov/page",
  "filename": "page-name",
  "subdir": "web_pages",
  "sourceType": "web_page",
  "knowledgeProfile": "general",
  "licenseNotes": "Public government information."
}
```

### Socrata Configuration

```json
{
  "baseUrl": "https://data.clevelandohio.gov",
  "subdir": "open_data_catalog",
  "knowledgeProfile": "open_data_catalog",
  "limit": 500,
  "category": null
}
```

### Legistar Configuration

```json
{
  "portalUrl": "https://cityofcleveland.legistar.com",
  "subdir": "legislation",
  "knowledgeProfile": "legislation",
  "limit": 100,
  "introducedWithinDays": 365,
  "includeBodyText": false
}
```

## Output Structure

```
kb_sources/
└── citywide_public/
    ├── open_data_catalog/
    │   ├── building-permits.md
    │   ├── crime-data.md
    │   └── ...
    ├── legislation/
    │   ├── ord-no-123-2024.md
    │   ├── res-no-456-2024.md
    │   └── ...
    ├── ordinances/
    │   └── codified-ordinances-overview.md
    └── web_pages/
        ├── city-departments-directory.md
        └── ...
```

## Frontmatter Format

Every imported file includes YAML frontmatter for audit compliance:

```yaml
---
source_url: "https://data.clevelandohio.gov/d/abcd-1234"
retrieved_at: "2024-01-15T12:00:00.000Z"
publisher: "City of Cleveland"
source_type: "open_data"
title: "Building Permits"
license_notes: "Check source for license terms"
department: "dept-citywide"
sensitivity: "public"
visibility: "citywide"
knowledge_profile: "open_data_catalog"
dataset_id: "abcd-1234"
---
```

## Scheduled Refresh

A GitHub Actions workflow automatically refreshes sources weekly:

- **Schedule**: Every Sunday at 2:00 AM UTC
- **Workflow**: `.github/workflows/import-public-sources.yml`
- **Manual Trigger**: Can be run manually via GitHub Actions UI

## API Reference

### Utils

```typescript
import { sha256 } from './utils/sha';
import { writeSnapshotIfChanged } from './utils/write-snapshot';
import { fetchWithRetry } from './utils/http-client';
import { createMarkdownWithFrontmatter } from './utils/frontmatter';
```

### Importers

```typescript
import { fetchUrlToMarkdown } from './importers/fetch-url';
import { pullSocrataCatalogToFiles } from './importers/socrata-catalog';
import { fetchLegistarToFiles } from './importers/legistar';
```

## Testing

```bash
npm test
```

Tests verify:
- SHA256 hash consistency
- Frontmatter creation/parsing
- Idempotent file writing (zero changes on second run)
- Orphaned metadata cleanup

## Legal Notes

- **Socrata APIs** are designed for public access
- **Legistar data** is public government information
- **Web pages** are scraped only from government domains
- Always include `source_url` and `retrieved_at` for attribution
- Verify current status at source before official use
- This module respects `robots.txt` by default

## Cleveland-Specific Sources

| Source | Type | URL |
|--------|------|-----|
| Open Data Portal | Socrata | https://data.clevelandohio.gov |
| Legistar | Legislation | https://cityofcleveland.legistar.com |
| Codified Ordinances | American Legal | https://codelibrary.amlegal.com/codes/cleveland |
| City Website | Web | https://www.clevelandohio.gov |

## Extending for Other Cities

1. Copy `configs/cleveland.config.json` to `configs/your-city.config.json`
2. Update the publisher, URLs, and output paths
3. Run: `npx tsx cli/import-public-sources.ts --config configs/your-city.config.json`

## Architecture

```
packages/kb/
├── cli/
│   └── import-public-sources.ts    # CLI entry point
├── configs/
│   ├── cleveland.config.json       # Cleveland configuration
│   └── public-sources.config.example.json
├── importers/
│   ├── fetch-url.ts                # HTML to Markdown
│   ├── socrata-catalog.ts          # Socrata API
│   ├── legistar.ts                 # Legistar API
│   └── index.ts
├── utils/
│   ├── sha.ts                      # SHA256 hashing
│   ├── http-client.ts              # Retry, rate limiting
│   ├── write-snapshot.ts           # Change detection
│   ├── frontmatter.ts              # YAML handling
│   └── index.ts
├── kb_sources/                     # Output directory
│   └── citywide_public/
└── __tests__/
    └── importer.test.ts
```

## HAAIS Governance Compliance

This module supports HAAIS governance requirements:

1. **Audit Trail**: Every file includes source URL and retrieval timestamp
2. **Data Sovereignty**: Content stored locally before ingestion
3. **Human Oversight**: Changes reviewed via git diff before commit
4. **Transparency**: Full provenance chain from source to KB
