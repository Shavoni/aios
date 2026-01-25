/**
 * HAAIS Public Source Importer - SHA256 Utility
 *
 * Provides cryptographic hashing for change detection.
 * Used to determine if content has changed since last import.
 */

import crypto from "node:crypto";

/**
 * Generate SHA256 hash of text content
 * @param text - The text content to hash
 * @returns Hexadecimal SHA256 hash string
 */
export function sha256(text: string): string {
  return crypto.createHash("sha256").update(text, "utf8").digest("hex");
}

/**
 * Generate SHA256 hash of a buffer (for binary files)
 * @param buffer - The buffer to hash
 * @returns Hexadecimal SHA256 hash string
 */
export function sha256Buffer(buffer: Buffer): string {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

/**
 * Compare two hashes for equality (constant-time to prevent timing attacks)
 * @param hash1 - First hash
 * @param hash2 - Second hash
 * @returns True if hashes match
 */
export function hashesMatch(hash1: string, hash2: string): boolean {
  if (hash1.length !== hash2.length) return false;
  return crypto.timingSafeEqual(Buffer.from(hash1), Buffer.from(hash2));
}
