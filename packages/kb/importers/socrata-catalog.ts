/**
 * HAAIS Public Source Importer - Socrata Open Data Catalog
 *
 * Fetches dataset metadata from Socrata-powered open data portals.
 * Creates markdown files with dataset descriptions, column schemas,
 * and API endpoint URLs.
 *
 * Socrata API Documentation: https://dev.socrata.com/
 *
 * Legal Note: Socrata APIs are designed for public access.
 * Always include source attribution and check data licenses.
 */

import path from "node:path";
import { fetchJsonWithRetry, type HttpClientConfig } from "../utils/http-client";
import { createMarkdownWithFrontmatter, type SourceFrontmatter } from "../utils/frontmatter";
import { writeSnapshotIfChanged, type WriteResult } from "../utils/write-snapshot";

export interface SocrataDataset {
  /** Socrata dataset ID (4x4 format, e.g., "abcd-1234") */
  datasetId: string;
  /** Dataset name/title */
  name: string;
  /** Dataset description */
  description: string;
  /** Column definitions */
  columns: SocrataColumn[];
  /** API endpoint URL */
  endpointUrl: string;
  /** Last updated timestamp */
  updatedAt: string;
  /** Category */
  category?: string;
  /** Tags */
  tags?: string[];
  /** License */
  license?: string;
  /** Attribution */
  attribution?: string;
  /** Row count */
  rowCount?: number;
  /** Download count */
  downloadCount?: number;
  /** View count */
  viewCount?: number;
}

export interface SocrataColumn {
  /** Column name */
  name: string;
  /** Column field name (API identifier) */
  fieldName: string;
  /** Data type */
  dataType: string;
  /** Description */
  description?: string;
}

export interface SocrataCatalogOptions {
  /** Publisher name */
  publisher: string;
  /** Output directory for markdown files */
  outputDir: string;
  /** Department/category */
  department?: string;
  /** Knowledge profile tag */
  knowledgeProfile?: string;
  /** HTTP client config overrides */
  httpConfig?: Partial<HttpClientConfig>;
  /** Maximum datasets to fetch (default: unlimited) */
  limit?: number;
  /** Filter by category */
  category?: string;
  /** Include only datasets updated since (ISO date) */
  updatedSince?: string;
}

interface SocrataCatalogResponse {
  results: SocrataCatalogItem[];
  resultSetSize: number;
}

interface SocrataCatalogItem {
  resource: {
    id: string;
    name: string;
    description?: string;
    attribution?: string;
    category?: string;
    type: string;
    updatedAt: string;
    createdAt: string;
    data_updated_at?: string;
    columns_name?: string[];
    columns_field_name?: string[];
    columns_datatype?: string[];
    columns_description?: string[];
    download_count?: number;
    view_count?: number;
    provenance?: string;
  };
  classification: {
    categories?: string[];
    tags?: string[];
    domain_category?: string;
    domain_tags?: string[];
  };
  metadata: {
    license?: string;
    domain?: string;
  };
  permalink: string;
  link: string;
}

/**
 * Build Socrata catalog API URL
 */
function buildCatalogUrl(baseUrl: string, options: SocrataCatalogOptions): string {
  const url = new URL("/api/catalog/v1", baseUrl);

  // Filter to datasets only
  url.searchParams.set("only", "datasets");

  // Limit results
  if (options.limit) {
    url.searchParams.set("limit", String(options.limit));
  } else {
    url.searchParams.set("limit", "1000"); // Default max
  }

  // Category filter
  if (options.category) {
    url.searchParams.set("categories", options.category);
  }

  return url.toString();
}

/**
 * Parse Socrata catalog item to SocrataDataset
 */
function parseCatalogItem(item: SocrataCatalogItem, baseUrl: string): SocrataDataset {
  const resource = item.resource;
  const columns: SocrataColumn[] = [];

  // Build columns from parallel arrays
  if (resource.columns_field_name) {
    for (let i = 0; i < resource.columns_field_name.length; i++) {
      columns.push({
        name: resource.columns_name?.[i] || resource.columns_field_name[i],
        fieldName: resource.columns_field_name[i],
        dataType: resource.columns_datatype?.[i] || "text",
        description: resource.columns_description?.[i],
      });
    }
  }

  return {
    datasetId: resource.id,
    name: resource.name,
    description: resource.description || "",
    columns,
    endpointUrl: `${baseUrl}/resource/${resource.id}.json`,
    updatedAt: resource.data_updated_at || resource.updatedAt,
    category: item.classification.domain_category || resource.category,
    tags: [...(item.classification.tags || []), ...(item.classification.domain_tags || [])],
    license: item.metadata.license,
    attribution: resource.attribution,
    rowCount: undefined, // Would need separate API call
    downloadCount: resource.download_count,
    viewCount: resource.view_count,
  };
}

/**
 * Generate markdown content for a dataset
 */
function generateDatasetMarkdown(dataset: SocrataDataset): string {
  const lines: string[] = [];

  // Title
  lines.push(`# ${dataset.name}`);
  lines.push("");

  // Description
  if (dataset.description) {
    lines.push(dataset.description);
    lines.push("");
  }

  // Metadata section
  lines.push("## Dataset Information");
  lines.push("");
  lines.push(`- **Dataset ID:** ${dataset.datasetId}`);
  lines.push(`- **Last Updated:** ${dataset.updatedAt}`);
  if (dataset.category) {
    lines.push(`- **Category:** ${dataset.category}`);
  }
  if (dataset.attribution) {
    lines.push(`- **Attribution:** ${dataset.attribution}`);
  }
  if (dataset.license) {
    lines.push(`- **License:** ${dataset.license}`);
  }
  if (dataset.downloadCount !== undefined) {
    lines.push(`- **Downloads:** ${dataset.downloadCount.toLocaleString()}`);
  }
  if (dataset.viewCount !== undefined) {
    lines.push(`- **Views:** ${dataset.viewCount.toLocaleString()}`);
  }
  lines.push("");

  // API Endpoint
  lines.push("## API Endpoint");
  lines.push("");
  lines.push("```");
  lines.push(dataset.endpointUrl);
  lines.push("```");
  lines.push("");
  lines.push("Use this endpoint with SoQL queries to filter and retrieve data programmatically.");
  lines.push("");

  // Example query
  lines.push("### Example Query");
  lines.push("");
  lines.push("```bash");
  lines.push(`curl "${dataset.endpointUrl}?$limit=10"`);
  lines.push("```");
  lines.push("");

  // Columns section
  if (dataset.columns.length > 0) {
    lines.push("## Columns");
    lines.push("");
    lines.push("| Column Name | Field Name | Data Type | Description |");
    lines.push("|-------------|------------|-----------|-------------|");

    for (const col of dataset.columns) {
      const desc = col.description?.replace(/\|/g, "\\|").replace(/\n/g, " ") || "-";
      lines.push(`| ${col.name} | \`${col.fieldName}\` | ${col.dataType} | ${desc} |`);
    }
    lines.push("");
  }

  // Tags
  if (dataset.tags && dataset.tags.length > 0) {
    lines.push("## Tags");
    lines.push("");
    lines.push(dataset.tags.map((t) => `\`${t}\``).join(", "));
    lines.push("");
  }

  return lines.join("\n");
}

/**
 * Sanitize filename from dataset name
 */
function sanitizeFilename(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

/**
 * Pull Socrata catalog and return dataset metadata
 */
export async function pullSocrataCatalog(
  baseUrl: string,
  options: SocrataCatalogOptions
): Promise<{ success: true; datasets: SocrataDataset[] } | { success: false; error: string }> {
  const catalogUrl = buildCatalogUrl(baseUrl, options);

  const result = await fetchJsonWithRetry<SocrataCatalogResponse>(catalogUrl, options.httpConfig);

  if (!result.success) {
    return {
      success: false,
      error: `Failed to fetch Socrata catalog: ${result.error.message}`,
    };
  }

  const datasets = result.data.results
    .filter((item) => item.resource.type === "dataset")
    .map((item) => parseCatalogItem(item, baseUrl));

  // Filter by updatedSince if specified
  if (options.updatedSince) {
    const sinceDate = new Date(options.updatedSince);
    return {
      success: true,
      datasets: datasets.filter((d) => new Date(d.updatedAt) >= sinceDate),
    };
  }

  return { success: true, datasets };
}

/**
 * Pull Socrata catalog and write markdown files
 */
export async function pullSocrataCatalogToFiles(
  baseUrl: string,
  options: SocrataCatalogOptions
): Promise<{
  success: boolean;
  datasets: SocrataDataset[];
  writeResults: WriteResult[];
  errors: string[];
}> {
  const errors: string[] = [];

  // Fetch catalog
  const catalogResult = await pullSocrataCatalog(baseUrl, options);

  if (!catalogResult.success) {
    return {
      success: false,
      datasets: [],
      writeResults: [],
      errors: [catalogResult.error],
    };
  }

  const datasets = catalogResult.datasets;
  const writeResults: WriteResult[] = [];

  // Write markdown files
  for (const dataset of datasets) {
    try {
      const markdownContent = generateDatasetMarkdown(dataset);

      const metadata: SourceFrontmatter = {
        source_url: `${baseUrl}/d/${dataset.datasetId}`,
        retrieved_at: new Date().toISOString(),
        publisher: options.publisher,
        source_type: "open_data",
        title: dataset.name,
        license_notes: dataset.license || "Check source for license terms",
        department: options.department,
        sensitivity: "public",
        visibility: "citywide",
        knowledge_profile: options.knowledgeProfile || "open_data_catalog",
        dataset_id: dataset.datasetId,
        category: dataset.category,
        data_updated_at: dataset.updatedAt,
      };

      const fullMarkdown = createMarkdownWithFrontmatter(metadata, markdownContent);

      const filename = `${sanitizeFilename(dataset.name)}.md`;
      const filePath = path.join(options.outputDir, filename);

      const writeResult = await writeSnapshotIfChanged(filePath, fullMarkdown);
      writeResults.push(writeResult);
    } catch (err: any) {
      errors.push(`Failed to write ${dataset.name}: ${err.message}`);
    }
  }

  return {
    success: errors.length === 0,
    datasets,
    writeResults,
    errors,
  };
}

/**
 * Get dataset details by ID
 */
export async function getSocrataDataset(
  baseUrl: string,
  datasetId: string,
  options?: { httpConfig?: Partial<HttpClientConfig> }
): Promise<{ success: true; dataset: SocrataDataset } | { success: false; error: string }> {
  const metadataUrl = `${baseUrl}/api/views/${datasetId}.json`;

  interface SocrataViewResponse {
    id: string;
    name: string;
    description?: string;
    attribution?: string;
    category?: string;
    rowsUpdatedAt?: number;
    createdAt: number;
    viewType: string;
    columns?: Array<{
      name: string;
      fieldName: string;
      dataTypeName: string;
      description?: string;
    }>;
    license?: {
      name?: string;
      termsLink?: string;
    };
    metadata?: {
      custom_fields?: Record<string, Record<string, string>>;
    };
    tags?: string[];
    downloadCount?: number;
    viewCount?: number;
  }

  const result = await fetchJsonWithRetry<SocrataViewResponse>(metadataUrl, options?.httpConfig);

  if (!result.success) {
    return {
      success: false,
      error: `Failed to fetch dataset ${datasetId}: ${result.error.message}`,
    };
  }

  const view = result.data;

  const columns: SocrataColumn[] = (view.columns || []).map((col) => ({
    name: col.name,
    fieldName: col.fieldName,
    dataType: col.dataTypeName,
    description: col.description,
  }));

  return {
    success: true,
    dataset: {
      datasetId: view.id,
      name: view.name,
      description: view.description || "",
      columns,
      endpointUrl: `${baseUrl}/resource/${view.id}.json`,
      updatedAt: view.rowsUpdatedAt ? new Date(view.rowsUpdatedAt * 1000).toISOString() : new Date(view.createdAt * 1000).toISOString(),
      category: view.category,
      tags: view.tags,
      license: view.license?.name,
      attribution: view.attribution,
      downloadCount: view.downloadCount,
      viewCount: view.viewCount,
    },
  };
}
