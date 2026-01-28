/**
 * HAAIS Public Source Importer - URL Fetcher
 *
 * Fetches HTML pages and converts them to clean Markdown with YAML frontmatter.
 * Strips navigation, footers, and other non-content elements.
 *
 * Legal Note: This fetcher is designed for public government websites.
 * Always include source_url and retrieved_at for audit compliance.
 * Respect robots.txt and rate limits.
 */

import { fetchWithRetry, type HttpClientConfig } from "../utils/http-client";
import { createMarkdownWithFrontmatter, type SourceFrontmatter } from "../utils/frontmatter";

export interface FetchUrlResult {
  /** Converted markdown content (without frontmatter) */
  markdown: string;
  /** Full markdown with YAML frontmatter */
  fullMarkdown: string;
  /** Extracted title */
  title: string;
  /** Original URL (may differ if redirected) */
  finalUrl: string;
  /** Frontmatter metadata */
  metadata: SourceFrontmatter;
}

export interface FetchUrlOptions {
  /** Publisher name (e.g., "City of Cleveland") */
  publisher: string;
  /** Source type */
  sourceType?: SourceFrontmatter["source_type"];
  /** Department/category */
  department?: string;
  /** Sensitivity tier (default: "public") */
  sensitivity?: SourceFrontmatter["sensitivity"];
  /** Visibility scope (default: "citywide") */
  visibility?: SourceFrontmatter["visibility"];
  /** Knowledge profile tag */
  knowledgeProfile?: string;
  /** License notes */
  licenseNotes?: string;
  /** HTTP client config overrides */
  httpConfig?: Partial<HttpClientConfig>;
}

/**
 * Elements to remove from HTML before conversion
 */
const REMOVE_SELECTORS = [
  "script",
  "style",
  "nav",
  "header",
  "footer",
  "aside",
  "iframe",
  "noscript",
  ".nav",
  ".navigation",
  ".menu",
  ".sidebar",
  ".footer",
  ".header",
  ".breadcrumb",
  ".breadcrumbs",
  ".social-share",
  ".share-buttons",
  ".comments",
  ".advertisement",
  ".ad",
  ".ads",
  "#nav",
  "#navigation",
  "#menu",
  "#sidebar",
  "#footer",
  "#header",
  "[role='navigation']",
  "[role='banner']",
  "[role='contentinfo']",
  "[aria-hidden='true']",
];

/**
 * Extract title from HTML
 */
function extractTitle(html: string): string {
  // Try <title> tag
  const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i);
  if (titleMatch) {
    return decodeHtmlEntities(titleMatch[1].trim());
  }

  // Try <h1> tag
  const h1Match = html.match(/<h1[^>]*>([^<]+)<\/h1>/i);
  if (h1Match) {
    return decodeHtmlEntities(h1Match[1].trim());
  }

  // Try og:title
  const ogMatch = html.match(/<meta[^>]+property="og:title"[^>]+content="([^"]+)"/i);
  if (ogMatch) {
    return decodeHtmlEntities(ogMatch[1].trim());
  }

  return "Untitled";
}

/**
 * Decode HTML entities
 */
function decodeHtmlEntities(text: string): string {
  const entities: Record<string, string> = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&#39;": "'",
    "&apos;": "'",
    "&nbsp;": " ",
    "&ndash;": "\u2013",
    "&mdash;": "\u2014",
    "&lsquo;": "\u2018",
    "&rsquo;": "\u2019",
    "&ldquo;": "\u201C",
    "&rdquo;": "\u201D",
    "&bull;": "\u2022",
    "&hellip;": "\u2026",
    "&copy;": "\u00A9",
    "&reg;": "\u00AE",
    "&trade;": "\u2122",
  };

  let result = text;
  for (const [entity, char] of Object.entries(entities)) {
    result = result.replace(new RegExp(entity, "gi"), char);
  }

  // Handle numeric entities
  result = result.replace(/&#(\d+);/g, (_, code) => String.fromCharCode(parseInt(code, 10)));
  result = result.replace(/&#x([0-9a-f]+);/gi, (_, code) => String.fromCharCode(parseInt(code, 16)));

  return result;
}

/**
 * Remove unwanted elements from HTML
 * This is a simple regex-based approach - for production, use cheerio
 */
function stripUnwantedElements(html: string): string {
  let result = html;

  // Remove script and style content
  result = result.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, "");
  result = result.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, "");

  // Remove comments
  result = result.replace(/<!--[\s\S]*?-->/g, "");

  // Remove nav, header, footer, aside
  result = result.replace(/<nav[^>]*>[\s\S]*?<\/nav>/gi, "");
  result = result.replace(/<header[^>]*>[\s\S]*?<\/header>/gi, "");
  result = result.replace(/<footer[^>]*>[\s\S]*?<\/footer>/gi, "");
  result = result.replace(/<aside[^>]*>[\s\S]*?<\/aside>/gi, "");
  result = result.replace(/<iframe[^>]*>[\s\S]*?<\/iframe>/gi, "");
  result = result.replace(/<noscript[^>]*>[\s\S]*?<\/noscript>/gi, "");

  // Remove elements with common non-content classes
  const classPatterns = ["nav", "navigation", "menu", "sidebar", "footer", "header", "breadcrumb", "social", "share", "comment", "advertisement", "ad\\b"];
  for (const pattern of classPatterns) {
    const regex = new RegExp(`<[^>]+class="[^"]*\\b${pattern}\\b[^"]*"[^>]*>[\\s\\S]*?<\\/[^>]+>`, "gi");
    result = result.replace(regex, "");
  }

  return result;
}

/**
 * Convert HTML to Markdown
 * This is a simplified converter - for production, use turndown
 */
function htmlToMarkdown(html: string): string {
  let result = html;

  // Get body content
  const bodyMatch = result.match(/<body[^>]*>([\s\S]*)<\/body>/i);
  if (bodyMatch) {
    result = bodyMatch[1];
  }

  // Strip unwanted elements
  result = stripUnwantedElements(result);

  // Convert headings
  result = result.replace(/<h1[^>]*>([\s\S]*?)<\/h1>/gi, "\n# $1\n");
  result = result.replace(/<h2[^>]*>([\s\S]*?)<\/h2>/gi, "\n## $1\n");
  result = result.replace(/<h3[^>]*>([\s\S]*?)<\/h3>/gi, "\n### $1\n");
  result = result.replace(/<h4[^>]*>([\s\S]*?)<\/h4>/gi, "\n#### $1\n");
  result = result.replace(/<h5[^>]*>([\s\S]*?)<\/h5>/gi, "\n##### $1\n");
  result = result.replace(/<h6[^>]*>([\s\S]*?)<\/h6>/gi, "\n###### $1\n");

  // Convert paragraphs
  result = result.replace(/<p[^>]*>([\s\S]*?)<\/p>/gi, "\n$1\n");

  // Convert line breaks
  result = result.replace(/<br\s*\/?>/gi, "\n");

  // Convert bold
  result = result.replace(/<(strong|b)[^>]*>([\s\S]*?)<\/\1>/gi, "**$2**");

  // Convert italic
  result = result.replace(/<(em|i)[^>]*>([\s\S]*?)<\/\1>/gi, "*$2*");

  // Convert links
  result = result.replace(/<a[^>]+href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/gi, "[$2]($1)");

  // Convert unordered lists
  result = result.replace(/<ul[^>]*>([\s\S]*?)<\/ul>/gi, (_, content) => {
    return content.replace(/<li[^>]*>([\s\S]*?)<\/li>/gi, "\n- $1");
  });

  // Convert ordered lists
  let listCounter = 0;
  result = result.replace(/<ol[^>]*>([\s\S]*?)<\/ol>/gi, (_, content) => {
    listCounter = 0;
    return content.replace(/<li[^>]*>([\s\S]*?)<\/li>/gi, () => {
      listCounter++;
      return `\n${listCounter}. `;
    });
  });

  // Convert blockquotes
  result = result.replace(/<blockquote[^>]*>([\s\S]*?)<\/blockquote>/gi, (_, content) => {
    return content
      .split("\n")
      .map((line: string) => `> ${line}`)
      .join("\n");
  });

  // Convert code blocks
  result = result.replace(/<pre[^>]*><code[^>]*>([\s\S]*?)<\/code><\/pre>/gi, "\n```\n$1\n```\n");
  result = result.replace(/<pre[^>]*>([\s\S]*?)<\/pre>/gi, "\n```\n$1\n```\n");

  // Convert inline code
  result = result.replace(/<code[^>]*>([\s\S]*?)<\/code>/gi, "`$1`");

  // Convert tables (simplified)
  result = result.replace(/<table[^>]*>([\s\S]*?)<\/table>/gi, (_, content) => {
    const rows: string[] = [];
    const rowMatches = content.matchAll(/<tr[^>]*>([\s\S]*?)<\/tr>/gi);

    let isHeader = true;
    for (const rowMatch of rowMatches) {
      const cells: string[] = [];
      const cellMatches = rowMatch[1].matchAll(/<(th|td)[^>]*>([\s\S]*?)<\/\1>/gi);

      for (const cellMatch of cellMatches) {
        cells.push(cellMatch[2].replace(/<[^>]+>/g, "").trim());
      }

      if (cells.length > 0) {
        rows.push("| " + cells.join(" | ") + " |");

        if (isHeader) {
          rows.push("| " + cells.map(() => "---").join(" | ") + " |");
          isHeader = false;
        }
      }
    }

    return "\n" + rows.join("\n") + "\n";
  });

  // Remove remaining HTML tags
  result = result.replace(/<[^>]+>/g, "");

  // Decode HTML entities
  result = decodeHtmlEntities(result);

  // Clean up whitespace
  result = result.replace(/\n{3,}/g, "\n\n");
  result = result.replace(/[ \t]+/g, " ");
  result = result.trim();

  return result;
}

/**
 * Fetch URL and convert to Markdown with frontmatter
 */
export async function fetchUrlToMarkdown(
  url: string,
  options: FetchUrlOptions
): Promise<{ success: true; result: FetchUrlResult } | { success: false; error: string }> {
  const result = await fetchWithRetry(url, options.httpConfig);

  if (!result.success) {
    return {
      success: false,
      error: `Failed to fetch ${url}: ${result.error.message}`,
    };
  }

  const html = result.response.text;
  const title = extractTitle(html);
  const markdown = htmlToMarkdown(html);

  const metadata: SourceFrontmatter = {
    source_url: result.response.url,
    retrieved_at: new Date().toISOString(),
    publisher: options.publisher,
    source_type: options.sourceType || "web_page",
    title,
    license_notes: options.licenseNotes || "Public government information. Verify current status at source URL.",
    department: options.department,
    sensitivity: options.sensitivity || "public",
    visibility: options.visibility || "citywide",
    knowledge_profile: options.knowledgeProfile,
  };

  const fullMarkdown = createMarkdownWithFrontmatter(metadata, markdown);

  return {
    success: true,
    result: {
      markdown,
      fullMarkdown,
      title,
      finalUrl: result.response.url,
      metadata,
    },
  };
}

/**
 * Batch fetch multiple URLs
 */
export async function fetchUrlsToMarkdown(
  urls: string[],
  options: FetchUrlOptions
): Promise<{
  successful: Array<{ url: string; result: FetchUrlResult }>;
  failed: Array<{ url: string; error: string }>;
}> {
  const successful: Array<{ url: string; result: FetchUrlResult }> = [];
  const failed: Array<{ url: string; error: string }> = [];

  for (const url of urls) {
    const result = await fetchUrlToMarkdown(url, options);

    if (result.success) {
      successful.push({ url, result: result.result });
    } else {
      failed.push({ url, error: result.error });
    }
  }

  return { successful, failed };
}
