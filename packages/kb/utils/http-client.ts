/**
 * HAAIS Public Source Importer - Enterprise HTTP Client
 *
 * Features:
 * - Exponential backoff retry (3 attempts)
 * - Rate limiting (requests per second)
 * - Timeout handling
 * - User-Agent identification
 * - robots.txt awareness
 * - Comprehensive error handling
 *
 * Legal Note: This client identifies itself properly and respects
 * rate limits. Always verify terms of service for target sites.
 */

export interface HttpClientConfig {
  /** Maximum retry attempts (default: 3) */
  maxRetries: number;
  /** Base delay between retries in ms (default: 1000) */
  retryDelayMs: number;
  /** Request timeout in ms (default: 30000) */
  timeoutMs: number;
  /** Requests per second limit (default: 2) */
  rateLimit: number;
  /** User agent string */
  userAgent: string;
  /** Whether to check robots.txt (default: true) */
  respectRobotsTxt: boolean;
}

export interface HttpResponse {
  ok: boolean;
  status: number;
  statusText: string;
  headers: Record<string, string>;
  text: string;
  url: string;
  redirected: boolean;
}

export interface HttpError {
  type: "timeout" | "network" | "http" | "robots_blocked" | "rate_limited";
  message: string;
  status?: number;
  retryable: boolean;
}

const DEFAULT_CONFIG: HttpClientConfig = {
  maxRetries: 3,
  retryDelayMs: 1000,
  timeoutMs: 30000,
  rateLimit: 2,
  userAgent: "HAAIS-PublicSourceImporter/1.0 (+https://github.com/haais/aios; municipal-ai-governance)",
  respectRobotsTxt: true,
};

// Rate limiter state
const requestTimestamps: Map<string, number[]> = new Map();

// Robots.txt cache
const robotsCache: Map<string, { allowed: boolean; cachedAt: number }> = new Map();
const ROBOTS_CACHE_TTL = 3600000; // 1 hour

/**
 * Sleep for specified milliseconds
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Extract domain from URL
 */
function getDomain(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

/**
 * Check if request is allowed by rate limiter
 */
async function waitForRateLimit(domain: string, rateLimit: number): Promise<void> {
  const now = Date.now();
  const timestamps = requestTimestamps.get(domain) || [];

  // Remove timestamps older than 1 second
  const recentTimestamps = timestamps.filter((t) => now - t < 1000);

  if (recentTimestamps.length >= rateLimit) {
    // Wait until oldest request is more than 1 second old
    const waitTime = 1000 - (now - recentTimestamps[0]);
    if (waitTime > 0) {
      await sleep(waitTime);
    }
  }

  // Record this request
  recentTimestamps.push(Date.now());
  requestTimestamps.set(domain, recentTimestamps);
}

/**
 * Check robots.txt for URL
 */
async function checkRobotsTxt(url: string, userAgent: string): Promise<boolean> {
  const domain = getDomain(url);
  const cached = robotsCache.get(domain);

  if (cached && Date.now() - cached.cachedAt < ROBOTS_CACHE_TTL) {
    return cached.allowed;
  }

  try {
    const robotsUrl = new URL("/robots.txt", url).toString();
    const response = await fetch(robotsUrl, {
      headers: { "User-Agent": userAgent },
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      // No robots.txt or error - assume allowed
      robotsCache.set(domain, { allowed: true, cachedAt: Date.now() });
      return true;
    }

    const robotsTxt = await response.text();
    const urlPath = new URL(url).pathname;

    // Simple robots.txt parser - check for Disallow rules
    // This is a basic implementation; production should use a proper parser
    const lines = robotsTxt.split("\n");
    let inUserAgentSection = false;
    let allowed = true;

    for (const line of lines) {
      const trimmed = line.trim().toLowerCase();

      if (trimmed.startsWith("user-agent:")) {
        const agent = trimmed.slice(11).trim();
        inUserAgentSection = agent === "*" || userAgent.toLowerCase().includes(agent);
      } else if (inUserAgentSection && trimmed.startsWith("disallow:")) {
        const disallowPath = trimmed.slice(9).trim();
        if (disallowPath && urlPath.startsWith(disallowPath)) {
          allowed = false;
          break;
        }
      } else if (inUserAgentSection && trimmed.startsWith("allow:")) {
        const allowPath = trimmed.slice(6).trim();
        if (allowPath && urlPath.startsWith(allowPath)) {
          allowed = true;
        }
      }
    }

    robotsCache.set(domain, { allowed, cachedAt: Date.now() });
    return allowed;
  } catch {
    // Error fetching robots.txt - assume allowed
    robotsCache.set(domain, { allowed: true, cachedAt: Date.now() });
    return true;
  }
}

/**
 * Calculate exponential backoff delay
 */
function getBackoffDelay(attempt: number, baseDelay: number): number {
  // Exponential backoff with jitter: base * 2^attempt + random(0-500ms)
  return baseDelay * Math.pow(2, attempt) + Math.random() * 500;
}

/**
 * Fetch URL with retry, rate limiting, and error handling
 */
export async function fetchWithRetry(
  url: string,
  config: Partial<HttpClientConfig> = {}
): Promise<{ success: true; response: HttpResponse } | { success: false; error: HttpError }> {
  const cfg = { ...DEFAULT_CONFIG, ...config };
  const domain = getDomain(url);

  // Check robots.txt
  if (cfg.respectRobotsTxt) {
    const allowed = await checkRobotsTxt(url, cfg.userAgent);
    if (!allowed) {
      return {
        success: false,
        error: {
          type: "robots_blocked",
          message: `Access to ${url} is disallowed by robots.txt`,
          retryable: false,
        },
      };
    }
  }

  let lastError: HttpError | null = null;

  for (let attempt = 0; attempt < cfg.maxRetries; attempt++) {
    try {
      // Rate limiting
      await waitForRateLimit(domain, cfg.rateLimit);

      // Make request
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), cfg.timeoutMs);

      const response = await fetch(url, {
        headers: {
          "User-Agent": cfg.userAgent,
          Accept: "application/json, text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
          "Accept-Language": "en-US,en;q=0.5",
        },
        signal: controller.signal,
        redirect: "follow",
      });

      clearTimeout(timeoutId);

      // Handle HTTP errors
      if (!response.ok) {
        const isRetryable = response.status >= 500 || response.status === 429;

        if (response.status === 429) {
          // Rate limited - wait longer
          const retryAfter = response.headers.get("Retry-After");
          const waitTime = retryAfter ? parseInt(retryAfter, 10) * 1000 : getBackoffDelay(attempt, cfg.retryDelayMs * 2);
          await sleep(waitTime);
          continue;
        }

        if (isRetryable && attempt < cfg.maxRetries - 1) {
          await sleep(getBackoffDelay(attempt, cfg.retryDelayMs));
          continue;
        }

        return {
          success: false,
          error: {
            type: "http",
            message: `HTTP ${response.status}: ${response.statusText}`,
            status: response.status,
            retryable: isRetryable,
          },
        };
      }

      // Success
      const text = await response.text();
      const headers: Record<string, string> = {};
      response.headers.forEach((value, key) => {
        headers[key] = value;
      });

      return {
        success: true,
        response: {
          ok: true,
          status: response.status,
          statusText: response.statusText,
          headers,
          text,
          url: response.url,
          redirected: response.redirected,
        },
      };
    } catch (err: any) {
      if (err.name === "AbortError") {
        lastError = {
          type: "timeout",
          message: `Request timed out after ${cfg.timeoutMs}ms`,
          retryable: true,
        };
      } else {
        lastError = {
          type: "network",
          message: err.message || "Network error",
          retryable: true,
        };
      }

      if (attempt < cfg.maxRetries - 1) {
        await sleep(getBackoffDelay(attempt, cfg.retryDelayMs));
      }
    }
  }

  return {
    success: false,
    error: lastError || {
      type: "network",
      message: "Unknown error after all retries",
      retryable: false,
    },
  };
}

/**
 * Fetch JSON with retry
 */
export async function fetchJsonWithRetry<T>(
  url: string,
  config: Partial<HttpClientConfig> = {}
): Promise<{ success: true; data: T } | { success: false; error: HttpError }> {
  const result = await fetchWithRetry(url, config);

  if (!result.success) {
    return result;
  }

  try {
    const data = JSON.parse(result.response.text) as T;
    return { success: true, data };
  } catch (err: any) {
    return {
      success: false,
      error: {
        type: "http",
        message: `Invalid JSON response: ${err.message}`,
        retryable: false,
      },
    };
  }
}

/**
 * Clear all caches (useful for testing)
 */
export function clearCaches(): void {
  requestTimestamps.clear();
  robotsCache.clear();
}
