/**
 * HAAIS Public Source Importer - Snapshot Writer
 *
 * Handles writing content to disk with SHA256 change detection.
 * Only writes if content has actually changed, preventing
 * unnecessary git commits and database re-ingestion.
 *
 * Audit Trail: Every write includes timestamp metadata.
 */

import fs from "node:fs/promises";
import path from "node:path";
import { sha256 } from "./sha";

export interface WriteResult {
  /** Whether the file was written (content changed) */
  changed: boolean;
  /** The file path that was checked/written */
  path: string;
  /** SHA256 hash of the content */
  hash: string;
  /** Previous hash if file existed */
  previousHash?: string;
  /** Whether file was newly created */
  created: boolean;
}

export interface SnapshotMetadata {
  /** SHA256 hash of content */
  hash: string;
  /** ISO timestamp of last update */
  updatedAt: string;
  /** ISO timestamp of creation */
  createdAt: string;
  /** Number of times content has changed */
  changeCount: number;
}

// Metadata cache file suffix
const METADATA_SUFFIX = ".meta.json";

/**
 * Read existing file content if it exists
 */
async function readExisting(filePath: string): Promise<string | null> {
  try {
    return await fs.readFile(filePath, "utf8");
  } catch (err: any) {
    if (err.code === "ENOENT") {
      return null;
    }
    throw err;
  }
}

/**
 * Read snapshot metadata if it exists
 */
async function readMetadata(filePath: string): Promise<SnapshotMetadata | null> {
  try {
    const metaPath = filePath + METADATA_SUFFIX;
    const content = await fs.readFile(metaPath, "utf8");
    return JSON.parse(content) as SnapshotMetadata;
  } catch {
    return null;
  }
}

/**
 * Write snapshot metadata
 */
async function writeMetadata(filePath: string, metadata: SnapshotMetadata): Promise<void> {
  const metaPath = filePath + METADATA_SUFFIX;
  await fs.writeFile(metaPath, JSON.stringify(metadata, null, 2), "utf8");
}

/**
 * Ensure directory exists
 */
async function ensureDir(filePath: string): Promise<void> {
  const dir = path.dirname(filePath);
  await fs.mkdir(dir, { recursive: true });
}

/**
 * Write content to file only if it has changed
 *
 * @param filePath - Absolute or relative path to write to
 * @param content - Content to write
 * @returns WriteResult indicating whether content changed
 */
export async function writeSnapshotIfChanged(
  filePath: string,
  content: string
): Promise<WriteResult> {
  const absolutePath = path.isAbsolute(filePath) ? filePath : path.resolve(process.cwd(), filePath);
  const contentHash = sha256(content);

  // Read existing content and metadata
  const existingContent = await readExisting(absolutePath);
  const existingMetadata = await readMetadata(absolutePath);

  const isNewFile = existingContent === null;
  const previousHash = existingMetadata?.hash || (existingContent ? sha256(existingContent) : undefined);

  // Check if content has changed
  if (!isNewFile && previousHash === contentHash) {
    return {
      changed: false,
      path: absolutePath,
      hash: contentHash,
      previousHash,
      created: false,
    };
  }

  // Content has changed or is new - write it
  await ensureDir(absolutePath);
  await fs.writeFile(absolutePath, content, "utf8");

  // Update metadata
  const now = new Date().toISOString();
  const newMetadata: SnapshotMetadata = {
    hash: contentHash,
    updatedAt: now,
    createdAt: existingMetadata?.createdAt || now,
    changeCount: (existingMetadata?.changeCount || 0) + 1,
  };
  await writeMetadata(absolutePath, newMetadata);

  return {
    changed: true,
    path: absolutePath,
    hash: contentHash,
    previousHash,
    created: isNewFile,
  };
}

/**
 * Batch write multiple snapshots
 *
 * @param snapshots - Array of { path, content } to write
 * @returns Array of WriteResults
 */
export async function writeSnapshotsBatch(
  snapshots: Array<{ path: string; content: string }>
): Promise<WriteResult[]> {
  return Promise.all(
    snapshots.map(({ path: p, content }) => writeSnapshotIfChanged(p, content))
  );
}

/**
 * Get snapshot statistics for a directory
 */
export async function getSnapshotStats(
  directory: string
): Promise<{
  totalFiles: number;
  totalSize: number;
  oldestUpdate: string | null;
  newestUpdate: string | null;
}> {
  const stats = {
    totalFiles: 0,
    totalSize: 0,
    oldestUpdate: null as string | null,
    newestUpdate: null as string | null,
  };

  async function walk(dir: string): Promise<void> {
    try {
      const entries = await fs.readdir(dir, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);

        if (entry.isDirectory()) {
          await walk(fullPath);
        } else if (entry.isFile() && entry.name.endsWith(".md")) {
          stats.totalFiles++;
          const fileStat = await fs.stat(fullPath);
          stats.totalSize += fileStat.size;

          const metadata = await readMetadata(fullPath);
          if (metadata) {
            if (!stats.oldestUpdate || metadata.updatedAt < stats.oldestUpdate) {
              stats.oldestUpdate = metadata.updatedAt;
            }
            if (!stats.newestUpdate || metadata.updatedAt > stats.newestUpdate) {
              stats.newestUpdate = metadata.updatedAt;
            }
          }
        }
      }
    } catch (err: any) {
      if (err.code !== "ENOENT") {
        throw err;
      }
    }
  }

  await walk(directory);
  return stats;
}

/**
 * Clean up orphaned metadata files (metadata without corresponding content)
 */
export async function cleanOrphanedMetadata(directory: string): Promise<string[]> {
  const removed: string[] = [];

  async function walk(dir: string): Promise<void> {
    try {
      const entries = await fs.readdir(dir, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);

        if (entry.isDirectory()) {
          await walk(fullPath);
        } else if (entry.isFile() && entry.name.endsWith(METADATA_SUFFIX)) {
          const contentPath = fullPath.slice(0, -METADATA_SUFFIX.length);
          try {
            await fs.access(contentPath);
          } catch {
            // Content file doesn't exist - remove metadata
            await fs.unlink(fullPath);
            removed.push(fullPath);
          }
        }
      }
    } catch (err: any) {
      if (err.code !== "ENOENT") {
        throw err;
      }
    }
  }

  await walk(directory);
  return removed;
}
