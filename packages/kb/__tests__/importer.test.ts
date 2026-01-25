/**
 * HAAIS Public Source Importer - Test Suite
 *
 * Tests for the public source importer module.
 *
 * Run with: npm test
 */

import { describe, it, before, after } from "node:test";
import assert from "node:assert";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";

import { sha256, hashesMatch } from "../utils/sha";
import { writeSnapshotIfChanged, getSnapshotStats, cleanOrphanedMetadata } from "../utils/write-snapshot";
import { createFrontmatter, parseFrontmatter, createMarkdownWithFrontmatter } from "../utils/frontmatter";

// ============================================================================
// SHA256 Tests
// ============================================================================

describe("SHA256 Utilities", () => {
  it("should generate consistent hashes for same content", () => {
    const content = "Hello, HAAIS!";
    const hash1 = sha256(content);
    const hash2 = sha256(content);

    assert.strictEqual(hash1, hash2);
    assert.strictEqual(hash1.length, 64); // SHA256 produces 64 hex chars
  });

  it("should generate different hashes for different content", () => {
    const hash1 = sha256("Content A");
    const hash2 = sha256("Content B");

    assert.notStrictEqual(hash1, hash2);
  });

  it("should match identical hashes", () => {
    const hash = sha256("Test content");
    assert.strictEqual(hashesMatch(hash, hash), true);
  });

  it("should not match different hashes", () => {
    const hash1 = sha256("Content A");
    const hash2 = sha256("Content B");

    assert.strictEqual(hashesMatch(hash1, hash2), false);
  });
});

// ============================================================================
// Frontmatter Tests
// ============================================================================

describe("Frontmatter Utilities", () => {
  it("should create valid YAML frontmatter", () => {
    const metadata = {
      source_url: "https://example.gov/page",
      retrieved_at: "2024-01-15T12:00:00Z",
      publisher: "City of Test",
      source_type: "web_page" as const,
    };

    const frontmatter = createFrontmatter(metadata);

    assert.ok(frontmatter.startsWith("---\n"));
    assert.ok(frontmatter.endsWith("---\n\n"));
    assert.ok(frontmatter.includes('source_url: "https://example.gov/page"'));
    assert.ok(frontmatter.includes('publisher: "City of Test"'));
  });

  it("should parse frontmatter from markdown", () => {
    const markdown = `---
source_url: "https://example.gov"
retrieved_at: "2024-01-15T12:00:00Z"
publisher: "Test City"
source_type: "web_page"
---

# Content

This is the body.`;

    const { metadata, content } = parseFrontmatter(markdown);

    assert.strictEqual(metadata.source_url, "https://example.gov");
    assert.strictEqual(metadata.publisher, "Test City");
    assert.ok(content.includes("# Content"));
    assert.ok(content.includes("This is the body."));
  });

  it("should handle markdown without frontmatter", () => {
    const markdown = "# Just Content\n\nNo frontmatter here.";

    const { metadata, content } = parseFrontmatter(markdown);

    assert.deepStrictEqual(metadata, {});
    assert.strictEqual(content, markdown);
  });

  it("should escape special characters in frontmatter", () => {
    const metadata = {
      source_url: "https://example.gov",
      retrieved_at: "2024-01-15T12:00:00Z",
      publisher: "City of Test",
      source_type: "web_page" as const,
      title: 'Document with "quotes" and newlines\nhere',
    };

    const frontmatter = createFrontmatter(metadata);

    // Should be escaped properly
    assert.ok(frontmatter.includes('\\"quotes\\"'));
    assert.ok(frontmatter.includes("\\n"));
  });

  it("should create full markdown with frontmatter", () => {
    const metadata = {
      source_url: "https://example.gov",
      retrieved_at: "2024-01-15T12:00:00Z",
      publisher: "Test",
      source_type: "web_page" as const,
    };

    const content = "# Hello\n\nWorld";
    const full = createMarkdownWithFrontmatter(metadata, content);

    assert.ok(full.startsWith("---\n"));
    assert.ok(full.includes("---\n\n# Hello"));
    assert.ok(full.endsWith("World"));
  });
});

// ============================================================================
// Snapshot Writer Tests
// ============================================================================

describe("Snapshot Writer", () => {
  let tempDir: string;

  before(async () => {
    tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "haais-test-"));
  });

  after(async () => {
    await fs.rm(tempDir, { recursive: true, force: true });
  });

  it("should write new file and return created=true", async () => {
    const filePath = path.join(tempDir, "new-file.md");
    const content = "# New Content\n\nThis is new.";

    const result = await writeSnapshotIfChanged(filePath, content);

    assert.strictEqual(result.changed, true);
    assert.strictEqual(result.created, true);
    assert.ok(result.hash.length === 64);

    // Verify file was written
    const written = await fs.readFile(filePath, "utf8");
    assert.strictEqual(written, content);
  });

  it("should not write unchanged content", async () => {
    const filePath = path.join(tempDir, "unchanged.md");
    const content = "# Same Content\n\nNo changes.";

    // First write
    const result1 = await writeSnapshotIfChanged(filePath, content);
    assert.strictEqual(result1.changed, true);

    // Second write with same content
    const result2 = await writeSnapshotIfChanged(filePath, content);
    assert.strictEqual(result2.changed, false);
    assert.strictEqual(result2.hash, result1.hash);
  });

  it("should detect and write changed content", async () => {
    const filePath = path.join(tempDir, "changed.md");

    // First write
    await writeSnapshotIfChanged(filePath, "Version 1");

    // Second write with different content
    const result = await writeSnapshotIfChanged(filePath, "Version 2");

    assert.strictEqual(result.changed, true);
    assert.strictEqual(result.created, false);
    assert.ok(result.previousHash !== result.hash);
  });

  it("should create directories as needed", async () => {
    const filePath = path.join(tempDir, "deep", "nested", "dir", "file.md");

    const result = await writeSnapshotIfChanged(filePath, "Content");

    assert.strictEqual(result.changed, true);

    // Verify file exists
    const stat = await fs.stat(filePath);
    assert.ok(stat.isFile());
  });

  it("running import twice results in zero changes", async () => {
    const filePath = path.join(tempDir, "idempotent.md");
    const content = "# Idempotent Test\n\nShould only write once.";

    // First run
    const run1 = await writeSnapshotIfChanged(filePath, content);
    assert.strictEqual(run1.changed, true);

    // Second run - should detect no change
    const run2 = await writeSnapshotIfChanged(filePath, content);
    assert.strictEqual(run2.changed, false);

    // Third run - still no change
    const run3 = await writeSnapshotIfChanged(filePath, content);
    assert.strictEqual(run3.changed, false);
  });
});

// ============================================================================
// Snapshot Stats Tests
// ============================================================================

describe("Snapshot Stats", () => {
  let tempDir: string;

  before(async () => {
    tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "haais-stats-"));

    // Create some test files
    await writeSnapshotIfChanged(path.join(tempDir, "file1.md"), "Content 1");
    await writeSnapshotIfChanged(path.join(tempDir, "subdir", "file2.md"), "Content 2");
    await writeSnapshotIfChanged(path.join(tempDir, "subdir", "file3.md"), "Content 3");
  });

  after(async () => {
    await fs.rm(tempDir, { recursive: true, force: true });
  });

  it("should count markdown files", async () => {
    const stats = await getSnapshotStats(tempDir);

    assert.strictEqual(stats.totalFiles, 3);
    assert.ok(stats.totalSize > 0);
  });

  it("should track update timestamps", async () => {
    const stats = await getSnapshotStats(tempDir);

    assert.ok(stats.newestUpdate !== null);
    assert.ok(stats.oldestUpdate !== null);

    // Parse as dates to verify format
    const newest = new Date(stats.newestUpdate!);
    const oldest = new Date(stats.oldestUpdate!);

    assert.ok(newest instanceof Date);
    assert.ok(oldest instanceof Date);
  });
});

// ============================================================================
// Orphaned Metadata Cleanup Tests
// ============================================================================

describe("Orphaned Metadata Cleanup", () => {
  let tempDir: string;

  before(async () => {
    tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "haais-orphan-"));

    // Create a file with metadata
    await writeSnapshotIfChanged(path.join(tempDir, "exists.md"), "Content");

    // Create orphaned metadata (no corresponding content file)
    await fs.writeFile(
      path.join(tempDir, "orphan.md.meta.json"),
      JSON.stringify({ hash: "abc", updatedAt: "2024-01-01" })
    );
  });

  after(async () => {
    await fs.rm(tempDir, { recursive: true, force: true });
  });

  it("should remove orphaned metadata files", async () => {
    const removed = await cleanOrphanedMetadata(tempDir);

    assert.strictEqual(removed.length, 1);
    assert.ok(removed[0].includes("orphan.md.meta.json"));

    // Verify it was actually removed
    try {
      await fs.access(path.join(tempDir, "orphan.md.meta.json"));
      assert.fail("File should have been removed");
    } catch (err: any) {
      assert.strictEqual(err.code, "ENOENT");
    }
  });

  it("should not remove valid metadata files", async () => {
    // Valid metadata should still exist
    const metaPath = path.join(tempDir, "exists.md.meta.json");
    const stat = await fs.stat(metaPath);
    assert.ok(stat.isFile());
  });
});

console.log("Running HAAIS Public Source Importer tests...");
