#!/usr/bin/env node
/**
 * HAAIS Public Source Importer - CLI
 *
 * Command-line interface for importing public city sources into the knowledge base.
 *
 * Usage:
 *   npx tsx cli/import-public-sources.ts --config configs/cleveland.config.json
 *   npx tsx cli/import-public-sources.ts --config configs/cleveland.config.json --dry-run
 *   npx tsx cli/import-public-sources.ts --config configs/cleveland.config.json --type socrata
 *
 * Exit codes:
 *   0 - Success (all imports completed)
 *   1 - Partial failure (some imports failed)
 *   2 - Configuration error
 *   3 - All imports failed
 */

import fs from "node:fs/promises";
import path from "node:path";
import { fetchUrlsToMarkdown, type FetchUrlOptions } from "../importers/fetch-url";
import { pullSocrataCatalogToFiles, type SocrataCatalogOptions } from "../importers/socrata-catalog";
import { fetchLegistarToFiles, type LegistarOptions } from "../importers/legistar";
import { writeSnapshotIfChanged, getSnapshotStats, type WriteResult } from "../utils/write-snapshot";

// ============================================================================
// Configuration Types
// ============================================================================

export interface PublicSourcesConfig {
  /** Configuration version */
  version: "1.0";
  /** Publisher name (e.g., "City of Cleveland") */
  publisher: string;
  /** Default department */
  department?: string;
  /** Refresh cadence hint (for documentation) */
  refreshCadence?: "daily" | "weekly" | "monthly";
  /** Base output directory (relative to kb root) */
  outputBaseDir: string;
  /** Web pages to import */
  webPages?: WebPageConfig[];
  /** Socrata open data portal configuration */
  socrata?: SocrataConfig;
  /** Legistar portal configuration */
  legistar?: LegistarConfig;
  /** HTTP client settings */
  httpSettings?: {
    maxRetries?: number;
    retryDelayMs?: number;
    timeoutMs?: number;
    rateLimit?: number;
    respectRobotsTxt?: boolean;
  };
}

export interface WebPageConfig {
  /** URL to fetch */
  url: string;
  /** Output filename (without .md extension) */
  filename: string;
  /** Subdirectory within outputBaseDir */
  subdir?: string;
  /** Custom title (overrides extracted title) */
  title?: string;
  /** Source type */
  sourceType?: "web_page" | "ordinance" | "legislation";
  /** Knowledge profile */
  knowledgeProfile?: string;
  /** License notes */
  licenseNotes?: string;
}

export interface SocrataConfig {
  /** Socrata portal base URL */
  baseUrl: string;
  /** Output subdirectory */
  subdir: string;
  /** Knowledge profile */
  knowledgeProfile?: string;
  /** Maximum datasets to fetch */
  limit?: number;
  /** Filter by category */
  category?: string;
}

export interface LegistarConfig {
  /** Legistar portal URL */
  portalUrl: string;
  /** Output subdirectory */
  subdir: string;
  /** Knowledge profile */
  knowledgeProfile?: string;
  /** Maximum matters to fetch */
  limit?: number;
  /** Filter by matter type */
  matterType?: string;
  /** Include matters introduced in last N days */
  introducedWithinDays?: number;
  /** Include full body text */
  includeBodyText?: boolean;
}

// ============================================================================
// CLI Implementation
// ============================================================================

interface ImportResult {
  type: "webPages" | "socrata" | "legistar";
  total: number;
  successful: number;
  changed: number;
  failed: number;
  errors: string[];
  duration: number;
}

interface CLIOptions {
  configPath: string;
  dryRun: boolean;
  type?: "webPages" | "socrata" | "legistar";
  verbose: boolean;
}

function parseArgs(args: string[]): CLIOptions {
  const options: CLIOptions = {
    configPath: "",
    dryRun: false,
    verbose: false,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === "--config" || arg === "-c") {
      options.configPath = args[++i];
    } else if (arg === "--dry-run" || arg === "-n") {
      options.dryRun = true;
    } else if (arg === "--type" || arg === "-t") {
      options.type = args[++i] as CLIOptions["type"];
    } else if (arg === "--verbose" || arg === "-v") {
      options.verbose = true;
    } else if (arg === "--help" || arg === "-h") {
      printHelp();
      process.exit(0);
    }
  }

  return options;
}

function printHelp(): void {
  console.log(`
HAAIS Public Source Importer

USAGE:
  npx tsx cli/import-public-sources.ts --config <config.json> [options]

OPTIONS:
  -c, --config <path>   Path to configuration file (required)
  -n, --dry-run         Show what would be imported without making changes
  -t, --type <type>     Import only specific type: webPages, socrata, legistar
  -v, --verbose         Show detailed output
  -h, --help            Show this help message

EXAMPLES:
  # Import all configured sources
  npx tsx cli/import-public-sources.ts --config configs/cleveland.config.json

  # Dry run to see what would be imported
  npx tsx cli/import-public-sources.ts --config configs/cleveland.config.json --dry-run

  # Import only Socrata data
  npx tsx cli/import-public-sources.ts --config configs/cleveland.config.json --type socrata

EXIT CODES:
  0 - All imports successful
  1 - Some imports failed
  2 - Configuration error
  3 - All imports failed
`);
}

async function loadConfig(configPath: string): Promise<PublicSourcesConfig> {
  const absolutePath = path.isAbsolute(configPath) ? configPath : path.resolve(process.cwd(), configPath);

  try {
    const content = await fs.readFile(absolutePath, "utf8");
    return JSON.parse(content) as PublicSourcesConfig;
  } catch (err: any) {
    if (err.code === "ENOENT") {
      throw new Error(`Configuration file not found: ${absolutePath}`);
    }
    throw new Error(`Failed to parse configuration: ${err.message}`);
  }
}

function log(message: string, verbose: boolean = false): void {
  if (!verbose || process.env.VERBOSE === "true") {
    console.log(message);
  }
}

function logError(message: string): void {
  console.error(`ERROR: ${message}`);
}

async function importWebPages(
  config: PublicSourcesConfig,
  options: CLIOptions
): Promise<ImportResult> {
  const startTime = Date.now();
  const result: ImportResult = {
    type: "webPages",
    total: 0,
    successful: 0,
    changed: 0,
    failed: 0,
    errors: [],
    duration: 0,
  };

  if (!config.webPages || config.webPages.length === 0) {
    return result;
  }

  result.total = config.webPages.length;
  console.log(`\n📄 Importing ${result.total} web pages...`);

  for (const page of config.webPages) {
    const outputDir = path.join(config.outputBaseDir, page.subdir || "");
    const outputPath = path.join(outputDir, `${page.filename}.md`);

    if (options.dryRun) {
      console.log(`  [DRY-RUN] Would fetch: ${page.url}`);
      console.log(`            Output: ${outputPath}`);
      result.successful++;
      continue;
    }

    const fetchOptions: FetchUrlOptions = {
      publisher: config.publisher,
      sourceType: page.sourceType || "web_page",
      department: config.department,
      knowledgeProfile: page.knowledgeProfile,
      licenseNotes: page.licenseNotes,
      httpConfig: config.httpSettings,
    };

    const fetchResult = await fetchUrlsToMarkdown([page.url], fetchOptions);

    if (fetchResult.successful.length > 0) {
      const { fullMarkdown, title } = fetchResult.successful[0].result;

      // Override title if specified
      let markdown = fullMarkdown;
      if (page.title) {
        markdown = markdown.replace(/^title: ".*"$/m, `title: "${page.title}"`);
      }

      const writeResult = await writeSnapshotIfChanged(outputPath, markdown);

      if (writeResult.changed) {
        result.changed++;
        console.log(`  ✅ ${page.filename}: Updated (${title})`);
      } else {
        console.log(`  ⏭️  ${page.filename}: Unchanged`);
      }
      result.successful++;
    }

    if (fetchResult.failed.length > 0) {
      result.failed++;
      const error = fetchResult.failed[0].error;
      result.errors.push(`${page.url}: ${error}`);
      console.log(`  ❌ ${page.filename}: ${error}`);
    }
  }

  result.duration = Date.now() - startTime;
  return result;
}

async function importSocrata(
  config: PublicSourcesConfig,
  options: CLIOptions
): Promise<ImportResult> {
  const startTime = Date.now();
  const result: ImportResult = {
    type: "socrata",
    total: 0,
    successful: 0,
    changed: 0,
    failed: 0,
    errors: [],
    duration: 0,
  };

  if (!config.socrata) {
    return result;
  }

  console.log(`\n📊 Importing Socrata open data catalog...`);
  console.log(`   Portal: ${config.socrata.baseUrl}`);

  if (options.dryRun) {
    console.log(`  [DRY-RUN] Would fetch catalog from ${config.socrata.baseUrl}`);
    return result;
  }

  const outputDir = path.join(config.outputBaseDir, config.socrata.subdir);

  const socrataOptions: SocrataCatalogOptions = {
    publisher: config.publisher,
    outputDir,
    department: config.department,
    knowledgeProfile: config.socrata.knowledgeProfile || "open_data_catalog",
    httpConfig: config.httpSettings,
    limit: config.socrata.limit,
    category: config.socrata.category,
  };

  const catalogResult = await pullSocrataCatalogToFiles(config.socrata.baseUrl, socrataOptions);

  result.total = catalogResult.datasets.length;
  result.successful = catalogResult.writeResults.length;
  result.changed = catalogResult.writeResults.filter((r) => r.changed).length;
  result.failed = catalogResult.errors.length;
  result.errors = catalogResult.errors;

  console.log(`   Found ${result.total} datasets`);
  console.log(`   Updated: ${result.changed}, Unchanged: ${result.successful - result.changed}`);

  if (result.errors.length > 0) {
    console.log(`   Errors: ${result.errors.length}`);
    for (const error of result.errors) {
      console.log(`     ❌ ${error}`);
    }
  }

  result.duration = Date.now() - startTime;
  return result;
}

async function importLegistar(
  config: PublicSourcesConfig,
  options: CLIOptions
): Promise<ImportResult> {
  const startTime = Date.now();
  const result: ImportResult = {
    type: "legistar",
    total: 0,
    successful: 0,
    changed: 0,
    failed: 0,
    errors: [],
    duration: 0,
  };

  if (!config.legistar) {
    return result;
  }

  console.log(`\n📜 Importing Legistar legislation...`);
  console.log(`   Portal: ${config.legistar.portalUrl}`);

  if (options.dryRun) {
    console.log(`  [DRY-RUN] Would fetch legislation from ${config.legistar.portalUrl}`);
    return result;
  }

  const outputDir = path.join(config.outputBaseDir, config.legistar.subdir);

  // Calculate introducedSince date
  let introducedSince: string | undefined;
  if (config.legistar.introducedWithinDays) {
    const since = new Date();
    since.setDate(since.getDate() - config.legistar.introducedWithinDays);
    introducedSince = since.toISOString().split("T")[0];
  }

  const legistarOptions: LegistarOptions = {
    publisher: config.publisher,
    outputDir,
    department: config.department || "City Council",
    knowledgeProfile: config.legistar.knowledgeProfile || "legislation",
    httpConfig: config.httpSettings,
    limit: config.legistar.limit,
    matterType: config.legistar.matterType,
    introducedSince,
    includeBodyText: config.legistar.includeBodyText,
  };

  const legistarResult = await fetchLegistarToFiles(config.legistar.portalUrl, legistarOptions);

  result.total = legistarResult.matters.length;
  result.successful = legistarResult.writeResults.length;
  result.changed = legistarResult.writeResults.filter((r) => r.changed).length;
  result.failed = legistarResult.errors.length;
  result.errors = legistarResult.errors;

  console.log(`   Found ${result.total} matters`);
  console.log(`   Updated: ${result.changed}, Unchanged: ${result.successful - result.changed}`);

  if (result.errors.length > 0) {
    console.log(`   Errors: ${result.errors.length}`);
    for (const error of result.errors) {
      console.log(`     ❌ ${error}`);
    }
  }

  result.duration = Date.now() - startTime;
  return result;
}

function printSummary(results: ImportResult[]): void {
  console.log("\n" + "=".repeat(60));
  console.log("IMPORT SUMMARY");
  console.log("=".repeat(60));

  let totalFiles = 0;
  let totalChanged = 0;
  let totalFailed = 0;
  let totalDuration = 0;

  for (const result of results) {
    if (result.total > 0) {
      console.log(`\n${result.type}:`);
      console.log(`  Total:     ${result.total}`);
      console.log(`  Updated:   ${result.changed}`);
      console.log(`  Unchanged: ${result.successful - result.changed}`);
      console.log(`  Failed:    ${result.failed}`);
      console.log(`  Duration:  ${(result.duration / 1000).toFixed(1)}s`);

      totalFiles += result.successful;
      totalChanged += result.changed;
      totalFailed += result.failed;
      totalDuration += result.duration;
    }
  }

  console.log("\n" + "-".repeat(60));
  console.log(`TOTAL: ${totalFiles} files (${totalChanged} updated, ${totalFailed} failed)`);
  console.log(`TIME:  ${(totalDuration / 1000).toFixed(1)}s`);
  console.log("=".repeat(60) + "\n");
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const options = parseArgs(args);

  if (!options.configPath) {
    logError("Configuration file required. Use --config <path>");
    process.exit(2);
  }

  console.log("🏛️  HAAIS Public Source Importer");
  console.log("=".repeat(60));

  // Load configuration
  let config: PublicSourcesConfig;
  try {
    config = await loadConfig(options.configPath);
    console.log(`Config:    ${options.configPath}`);
    console.log(`Publisher: ${config.publisher}`);
    console.log(`Output:    ${config.outputBaseDir}`);

    if (options.dryRun) {
      console.log("\n⚠️  DRY RUN MODE - No files will be written\n");
    }
  } catch (err: any) {
    logError(err.message);
    process.exit(2);
  }

  // Run imports
  const results: ImportResult[] = [];

  if (!options.type || options.type === "webPages") {
    results.push(await importWebPages(config, options));
  }

  if (!options.type || options.type === "socrata") {
    results.push(await importSocrata(config, options));
  }

  if (!options.type || options.type === "legistar") {
    results.push(await importLegistar(config, options));
  }

  // Print summary
  printSummary(results);

  // Get final stats
  if (!options.dryRun) {
    try {
      const stats = await getSnapshotStats(config.outputBaseDir);
      console.log(`📁 Snapshot Directory Stats:`);
      console.log(`   Total Files: ${stats.totalFiles}`);
      console.log(`   Total Size:  ${(stats.totalSize / 1024).toFixed(1)} KB`);
      if (stats.newestUpdate) {
        console.log(`   Last Update: ${stats.newestUpdate}`);
      }
    } catch {
      // Directory may not exist yet
    }
  }

  // Determine exit code
  const totalFailed = results.reduce((sum, r) => sum + r.failed, 0);
  const totalSuccessful = results.reduce((sum, r) => sum + r.successful, 0);
  const allErrors = results.flatMap((r) => r.errors);

  if (allErrors.length > 0) {
    console.log("\n⚠️  Some imports failed. Errors:");
    for (const error of allErrors) {
      console.log(`   - ${error}`);
    }
  }

  if (totalSuccessful === 0 && totalFailed > 0) {
    console.log("\n❌ All imports failed");
    process.exit(3);
  } else if (totalFailed > 0) {
    console.log("\n⚠️  Some imports failed");
    process.exit(1);
  } else {
    console.log("\n✅ All imports completed successfully");
    process.exit(0);
  }
}

// Run CLI
main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(3);
});
