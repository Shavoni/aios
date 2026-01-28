/**
 * HAAIS Public Source Importer - Legistar Legislation
 *
 * Fetches legislation and meeting data from Legistar-powered portals.
 * Creates markdown files with legislation details, sponsors, and voting records.
 *
 * Legistar API Documentation: https://webapi.legistar.com/
 *
 * Legal Note: Legistar data is public government information.
 * Always include source attribution and meeting dates.
 */

import path from "node:path";
import { fetchJsonWithRetry, type HttpClientConfig } from "../utils/http-client";
import { createMarkdownWithFrontmatter, type SourceFrontmatter } from "../utils/frontmatter";
import { writeSnapshotIfChanged, type WriteResult } from "../utils/write-snapshot";

export interface LegistarMatter {
  /** Matter ID */
  matterId: number;
  /** Matter GUID */
  matterGuid: string;
  /** File number (e.g., "Ord. No. 123-2024") */
  fileNumber: string;
  /** Matter type (e.g., "Ordinance", "Resolution") */
  type: string;
  /** Title/name */
  title: string;
  /** Body text */
  bodyText?: string;
  /** Status */
  status: string;
  /** Introduction date */
  introducedDate: string;
  /** Passed date */
  passedDate?: string;
  /** Enacted date */
  enactedDate?: string;
  /** Sponsors */
  sponsors: string[];
  /** Current body (e.g., "City Council") */
  currentBody?: string;
  /** Attachments */
  attachments: LegistarAttachment[];
  /** History/actions */
  history: LegistarAction[];
}

export interface LegistarAttachment {
  /** Attachment ID */
  id: number;
  /** Name */
  name: string;
  /** URL */
  url: string;
}

export interface LegistarAction {
  /** Action date */
  date: string;
  /** Action text */
  action: string;
  /** Body that took action */
  body: string;
  /** Result (e.g., "Pass", "Fail") */
  result?: string;
  /** Vote tally */
  vote?: {
    yea: number;
    nay: number;
    abstain: number;
    absent: number;
  };
}

export interface LegistarOptions {
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
  /** Maximum matters to fetch (default: 100) */
  limit?: number;
  /** Filter by matter type (e.g., "Ordinance") */
  matterType?: string;
  /** Include only matters introduced since (ISO date) */
  introducedSince?: string;
  /** Include body text (requires additional API calls) */
  includeBodyText?: boolean;
}

// Legistar API response types
interface LegistarMatterResponse {
  MatterId: number;
  MatterGuid: string;
  MatterFile: string;
  MatterName: string;
  MatterTitle?: string;
  MatterBodyId?: number;
  MatterBodyName?: string;
  MatterIntroDate: string;
  MatterPassedDate?: string;
  MatterEnactmentDate?: string;
  MatterEnactmentNumber?: string;
  MatterStatusId?: number;
  MatterStatusName?: string;
  MatterTypeName?: string;
  MatterText?: string;
}

interface LegistarSponsorResponse {
  MatterSponsorName: string;
  MatterSponsorNameId?: number;
}

interface LegistarHistoryResponse {
  MatterHistoryActionDate: string;
  MatterHistoryActionName: string;
  MatterHistoryActionBodyName: string;
  MatterHistoryPassedFlag?: number;
  MatterHistoryTally?: string;
}

interface LegistarAttachmentResponse {
  MatterAttachmentId: number;
  MatterAttachmentName: string;
  MatterAttachmentHyperlink: string;
}

/**
 * Build Legistar API URL for a client
 */
function buildApiUrl(client: string, endpoint: string): string {
  return `https://webapi.legistar.com/v1/${client}/${endpoint}`;
}

/**
 * Extract client name from Legistar portal URL
 * e.g., "https://cityofcleveland.legistar.com" -> "cityofcleveland"
 */
export function extractLegistarClient(portalUrl: string): string {
  const match = portalUrl.match(/https?:\/\/([^.]+)\.legistar\.com/);
  if (!match) {
    throw new Error(`Invalid Legistar portal URL: ${portalUrl}`);
  }
  return match[1];
}

/**
 * Parse vote tally from Legistar format
 */
function parseVoteTally(tally?: string): LegistarAction["vote"] | undefined {
  if (!tally) return undefined;

  // Format: "Yea: 12, Nay: 0, Abstain: 1, Absent: 2"
  const yea = tally.match(/Yea:\s*(\d+)/i)?.[1] || "0";
  const nay = tally.match(/Nay:\s*(\d+)/i)?.[1] || "0";
  const abstain = tally.match(/Abstain:\s*(\d+)/i)?.[1] || "0";
  const absent = tally.match(/Absent:\s*(\d+)/i)?.[1] || "0";

  return {
    yea: parseInt(yea, 10),
    nay: parseInt(nay, 10),
    abstain: parseInt(abstain, 10),
    absent: parseInt(absent, 10),
  };
}

/**
 * Fetch matters from Legistar API
 */
export async function fetchLegistarMatters(
  portalUrl: string,
  options: LegistarOptions
): Promise<{ success: true; matters: LegistarMatter[] } | { success: false; error: string }> {
  const client = extractLegistarClient(portalUrl);
  const matters: LegistarMatter[] = [];

  // Build query parameters
  const params = new URLSearchParams();
  params.set("$top", String(options.limit || 100));
  params.set("$orderby", "MatterIntroDate desc");

  if (options.introducedSince) {
    params.set("$filter", `MatterIntroDate ge datetime'${options.introducedSince}'`);
  }

  const mattersUrl = buildApiUrl(client, `matters?${params.toString()}`);
  const mattersResult = await fetchJsonWithRetry<LegistarMatterResponse[]>(mattersUrl, options.httpConfig);

  if (!mattersResult.success) {
    return {
      success: false,
      error: `Failed to fetch matters: ${mattersResult.error.message}`,
    };
  }

  // Filter by matter type if specified
  let mattersList = mattersResult.data;
  if (options.matterType) {
    mattersList = mattersList.filter((m) => m.MatterTypeName?.toLowerCase().includes(options.matterType!.toLowerCase()));
  }

  // Fetch additional details for each matter
  for (const matterData of mattersList) {
    try {
      // Fetch sponsors
      const sponsorsUrl = buildApiUrl(client, `matters/${matterData.MatterId}/sponsors`);
      const sponsorsResult = await fetchJsonWithRetry<LegistarSponsorResponse[]>(sponsorsUrl, options.httpConfig);
      const sponsors = sponsorsResult.success ? sponsorsResult.data.map((s) => s.MatterSponsorName) : [];

      // Fetch history
      const historyUrl = buildApiUrl(client, `matters/${matterData.MatterId}/histories`);
      const historyResult = await fetchJsonWithRetry<LegistarHistoryResponse[]>(historyUrl, options.httpConfig);
      const history: LegistarAction[] = historyResult.success
        ? historyResult.data.map((h) => ({
            date: h.MatterHistoryActionDate,
            action: h.MatterHistoryActionName,
            body: h.MatterHistoryActionBodyName,
            result: h.MatterHistoryPassedFlag === 1 ? "Pass" : h.MatterHistoryPassedFlag === 0 ? "Fail" : undefined,
            vote: parseVoteTally(h.MatterHistoryTally),
          }))
        : [];

      // Fetch attachments
      const attachmentsUrl = buildApiUrl(client, `matters/${matterData.MatterId}/attachments`);
      const attachmentsResult = await fetchJsonWithRetry<LegistarAttachmentResponse[]>(attachmentsUrl, options.httpConfig);
      const attachments: LegistarAttachment[] = attachmentsResult.success
        ? attachmentsResult.data.map((a) => ({
            id: a.MatterAttachmentId,
            name: a.MatterAttachmentName,
            url: a.MatterAttachmentHyperlink,
          }))
        : [];

      // Fetch body text if requested
      let bodyText: string | undefined;
      if (options.includeBodyText) {
        const textUrl = buildApiUrl(client, `matters/${matterData.MatterId}/texts`);
        const textResult = await fetchJsonWithRetry<Array<{ MatterTextPlain?: string }>>(textUrl, options.httpConfig);
        if (textResult.success && textResult.data.length > 0) {
          bodyText = textResult.data[0].MatterTextPlain;
        }
      }

      matters.push({
        matterId: matterData.MatterId,
        matterGuid: matterData.MatterGuid,
        fileNumber: matterData.MatterFile,
        type: matterData.MatterTypeName || "Unknown",
        title: matterData.MatterTitle || matterData.MatterName,
        bodyText,
        status: matterData.MatterStatusName || "Unknown",
        introducedDate: matterData.MatterIntroDate,
        passedDate: matterData.MatterPassedDate || undefined,
        enactedDate: matterData.MatterEnactmentDate || undefined,
        sponsors,
        currentBody: matterData.MatterBodyName,
        attachments,
        history,
      });
    } catch (err: any) {
      console.error(`Failed to fetch details for matter ${matterData.MatterId}: ${err.message}`);
    }
  }

  return { success: true, matters };
}

/**
 * Generate markdown content for a matter
 */
function generateMatterMarkdown(matter: LegistarMatter): string {
  const lines: string[] = [];

  // Title
  lines.push(`# ${matter.fileNumber}: ${matter.title}`);
  lines.push("");

  // Status badge
  lines.push(`**Status:** ${matter.status}`);
  lines.push("");

  // Metadata
  lines.push("## Information");
  lines.push("");
  lines.push(`- **File Number:** ${matter.fileNumber}`);
  lines.push(`- **Type:** ${matter.type}`);
  lines.push(`- **Introduced:** ${new Date(matter.introducedDate).toLocaleDateString()}`);
  if (matter.passedDate) {
    lines.push(`- **Passed:** ${new Date(matter.passedDate).toLocaleDateString()}`);
  }
  if (matter.enactedDate) {
    lines.push(`- **Enacted:** ${new Date(matter.enactedDate).toLocaleDateString()}`);
  }
  if (matter.currentBody) {
    lines.push(`- **Current Body:** ${matter.currentBody}`);
  }
  lines.push("");

  // Sponsors
  if (matter.sponsors.length > 0) {
    lines.push("## Sponsors");
    lines.push("");
    for (const sponsor of matter.sponsors) {
      lines.push(`- ${sponsor}`);
    }
    lines.push("");
  }

  // Body text
  if (matter.bodyText) {
    lines.push("## Full Text");
    lines.push("");
    lines.push(matter.bodyText);
    lines.push("");
  }

  // History
  if (matter.history.length > 0) {
    lines.push("## Legislative History");
    lines.push("");
    lines.push("| Date | Body | Action | Result |");
    lines.push("|------|------|--------|--------|");

    for (const action of matter.history) {
      const date = new Date(action.date).toLocaleDateString();
      const result = action.result || "-";
      const vote = action.vote ? ` (${action.vote.yea}-${action.vote.nay})` : "";
      lines.push(`| ${date} | ${action.body} | ${action.action} | ${result}${vote} |`);
    }
    lines.push("");
  }

  // Attachments
  if (matter.attachments.length > 0) {
    lines.push("## Attachments");
    lines.push("");
    for (const attachment of matter.attachments) {
      lines.push(`- [${attachment.name}](${attachment.url})`);
    }
    lines.push("");
  }

  return lines.join("\n");
}

/**
 * Sanitize filename from file number
 */
function sanitizeFilename(fileNumber: string): string {
  return fileNumber
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

/**
 * Fetch Legistar matters and write to markdown files
 */
export async function fetchLegistarToFiles(
  portalUrl: string,
  options: LegistarOptions
): Promise<{
  success: boolean;
  matters: LegistarMatter[];
  writeResults: WriteResult[];
  errors: string[];
}> {
  const errors: string[] = [];

  // Fetch matters
  const mattersResult = await fetchLegistarMatters(portalUrl, options);

  if (!mattersResult.success) {
    return {
      success: false,
      matters: [],
      writeResults: [],
      errors: [mattersResult.error],
    };
  }

  const matters = mattersResult.matters;
  const writeResults: WriteResult[] = [];

  // Write markdown files
  for (const matter of matters) {
    try {
      const markdownContent = generateMatterMarkdown(matter);

      const metadata: SourceFrontmatter = {
        source_url: `${portalUrl}/LegislationDetail.aspx?ID=${matter.matterId}&GUID=${matter.matterGuid}`,
        retrieved_at: new Date().toISOString(),
        publisher: options.publisher,
        source_type: "legislation",
        title: `${matter.fileNumber}: ${matter.title}`,
        license_notes: "Public legislative record. Official version available at source URL.",
        department: options.department || "City Council",
        sensitivity: "public",
        visibility: "citywide",
        knowledge_profile: options.knowledgeProfile || "legislation",
        file_number: matter.fileNumber,
        matter_type: matter.type,
        status: matter.status,
        introduced_date: matter.introducedDate,
      };

      const fullMarkdown = createMarkdownWithFrontmatter(metadata, markdownContent);

      const filename = `${sanitizeFilename(matter.fileNumber)}.md`;
      const filePath = path.join(options.outputDir, filename);

      const writeResult = await writeSnapshotIfChanged(filePath, fullMarkdown);
      writeResults.push(writeResult);
    } catch (err: any) {
      errors.push(`Failed to write ${matter.fileNumber}: ${err.message}`);
    }
  }

  return {
    success: errors.length === 0,
    matters,
    writeResults,
    errors,
  };
}
