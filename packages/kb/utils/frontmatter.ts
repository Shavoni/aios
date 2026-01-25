/**
 * HAAIS Public Source Importer - YAML Frontmatter Utilities
 *
 * Handles creation and parsing of YAML frontmatter for markdown files.
 * Frontmatter provides essential audit trail metadata for governance compliance.
 */

export interface SourceFrontmatter {
  /** Original URL the content was fetched from */
  source_url: string;
  /** ISO timestamp when content was retrieved */
  retrieved_at: string;
  /** Publisher/organization (e.g., "City of Cleveland") */
  publisher: string;
  /** Type of source */
  source_type: "web_page" | "api" | "open_data" | "legislation" | "ordinance";
  /** Title of the document */
  title?: string;
  /** License or legal notes */
  license_notes?: string;
  /** Department/category for routing */
  department?: string;
  /** Sensitivity tier */
  sensitivity?: "public" | "internal" | "confidential" | "restricted" | "privileged";
  /** Visibility scope */
  visibility?: "private" | "citywide" | "shared";
  /** Knowledge profile tags */
  knowledge_profile?: string;
  /** Additional metadata */
  [key: string]: string | undefined;
}

/**
 * Create YAML frontmatter string from metadata
 */
export function createFrontmatter(metadata: SourceFrontmatter): string {
  const lines: string[] = ["---"];

  // Required fields first
  lines.push(`source_url: "${escapeYamlString(metadata.source_url)}"`);
  lines.push(`retrieved_at: "${metadata.retrieved_at}"`);
  lines.push(`publisher: "${escapeYamlString(metadata.publisher)}"`);
  lines.push(`source_type: "${metadata.source_type}"`);

  // Optional fields
  if (metadata.title) {
    lines.push(`title: "${escapeYamlString(metadata.title)}"`);
  }
  if (metadata.license_notes) {
    lines.push(`license_notes: "${escapeYamlString(metadata.license_notes)}"`);
  }
  if (metadata.department) {
    lines.push(`department: "${escapeYamlString(metadata.department)}"`);
  }
  if (metadata.sensitivity) {
    lines.push(`sensitivity: "${metadata.sensitivity}"`);
  }
  if (metadata.visibility) {
    lines.push(`visibility: "${metadata.visibility}"`);
  }
  if (metadata.knowledge_profile) {
    lines.push(`knowledge_profile: "${escapeYamlString(metadata.knowledge_profile)}"`);
  }

  // Any additional metadata
  for (const [key, value] of Object.entries(metadata)) {
    if (
      value &&
      !["source_url", "retrieved_at", "publisher", "source_type", "title", "license_notes", "department", "sensitivity", "visibility", "knowledge_profile"].includes(key)
    ) {
      lines.push(`${key}: "${escapeYamlString(String(value))}"`);
    }
  }

  lines.push("---");
  lines.push("");

  return lines.join("\n");
}

/**
 * Parse YAML frontmatter from markdown content
 */
export function parseFrontmatter(content: string): {
  metadata: Partial<SourceFrontmatter>;
  content: string;
} {
  const frontmatterRegex = /^---\n([\s\S]*?)\n---\n/;
  const match = content.match(frontmatterRegex);

  if (!match) {
    return { metadata: {}, content };
  }

  const frontmatterText = match[1];
  const bodyContent = content.slice(match[0].length);

  const metadata: Partial<SourceFrontmatter> = {};

  for (const line of frontmatterText.split("\n")) {
    const colonIndex = line.indexOf(":");
    if (colonIndex === -1) continue;

    const key = line.slice(0, colonIndex).trim();
    let value = line.slice(colonIndex + 1).trim();

    // Remove quotes if present
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }

    // Unescape YAML strings
    value = unescapeYamlString(value);

    (metadata as any)[key] = value;
  }

  return { metadata, content: bodyContent };
}

/**
 * Escape special characters for YAML string
 */
function escapeYamlString(str: string): string {
  return str
    .replace(/\\/g, "\\\\")
    .replace(/"/g, '\\"')
    .replace(/\n/g, "\\n")
    .replace(/\r/g, "\\r")
    .replace(/\t/g, "\\t");
}

/**
 * Unescape YAML string
 */
function unescapeYamlString(str: string): string {
  return str
    .replace(/\\n/g, "\n")
    .replace(/\\r/g, "\r")
    .replace(/\\t/g, "\t")
    .replace(/\\"/g, '"')
    .replace(/\\\\/g, "\\");
}

/**
 * Combine frontmatter and content into full markdown
 */
export function createMarkdownWithFrontmatter(metadata: SourceFrontmatter, content: string): string {
  return createFrontmatter(metadata) + content;
}

/**
 * Update frontmatter in existing markdown content
 */
export function updateFrontmatter(
  existingContent: string,
  updates: Partial<SourceFrontmatter>
): string {
  const { metadata: existingMetadata, content } = parseFrontmatter(existingContent);
  const newMetadata = { ...existingMetadata, ...updates } as SourceFrontmatter;
  return createMarkdownWithFrontmatter(newMetadata, content);
}
