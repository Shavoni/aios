/**
 * White-label configuration for HAAIS AIOS
 *
 * This file contains all branding and configuration that can be customized
 * per deployment/client.
 */

export interface BrandConfig {
  // Core branding
  appName: string;
  tagline: string;
  organization: string;

  // Colors (Tailwind class names)
  primaryColor: string;
  primaryColorLight: string;
  primaryColorDark: string;
  accentColor: string;

  // Logo/Icon
  logoIcon: string; // Lucide icon name (fallback)
  logoUrl?: string; // Custom logo URL (takes precedence over logoIcon)
  logoAlt?: string; // Alt text for logo
  faviconUrl?: string; // Custom favicon URL

  // Footer
  footerText: string;

  // Contact
  supportEmail?: string;
  supportPhone?: string;

  // Chat base URL for internal agents
  chatBaseUrl?: string; // e.g., "/chat" or external URL
}

// Default configuration - HAAIS AIOS
export const brandConfig: BrandConfig = {
  appName: "HAAIS AIOS",
  tagline: "AI Operating System",
  organization: "Greater Cleveland Partnership",

  primaryColor: "blue-600",
  primaryColorLight: "blue-100",
  primaryColorDark: "blue-700",
  accentColor: "slate-600",

  logoIcon: "Building2",
  logoUrl: undefined, // Set to custom logo URL, e.g., "/logo.png" or "https://..."
  logoAlt: "HAAIS AIOS Logo",
  faviconUrl: undefined, // Set to custom favicon URL

  footerText: "HAAIS AIOS • Powered by DEF1LIVE LLC",

  supportEmail: "support@haais.ai",
  chatBaseUrl: "/chat",
};

// Cleveland-specific configuration
export const clevelandConfig: BrandConfig = {
  appName: "Cleveland AI Gateway",
  tagline: "City Employee Support",
  organization: "City of Cleveland",

  primaryColor: "blue-600",
  primaryColorLight: "blue-100",
  primaryColorDark: "blue-700",
  accentColor: "slate-600",

  logoIcon: "Building2",
  logoUrl: undefined, // Set to "/cleveland-logo.png" or city seal URL
  logoAlt: "City of Cleveland Logo",
  faviconUrl: undefined,

  footerText: "Cleveland AI Gateway • Powered by HAAIS AIOS",

  supportEmail: "it-support@clevelandohio.gov",
  chatBaseUrl: "/chat",
};

// Phoenix configuration for Cleveland deployment
export const phoenixConfig: BrandConfig = {
  appName: "Phoenix",
  tagline: "AI Gateway",
  organization: "City of Cleveland",

  primaryColor: "amber-500",
  primaryColorLight: "amber-100",
  primaryColorDark: "amber-600",
  accentColor: "orange-500",

  logoIcon: "Sparkles",
  logoUrl: undefined,
  logoAlt: "Phoenix AI Gateway",
  faviconUrl: undefined,

  footerText: "Phoenix AI Gateway • City of Cleveland",

  supportEmail: "it-support@clevelandohio.gov",
  chatBaseUrl: "/chat",
};

// Export active config - can be switched based on environment
export const config = process.env.NEXT_PUBLIC_BRAND === "cleveland"
  ? clevelandConfig
  : process.env.NEXT_PUBLIC_BRAND === "phoenix"
  ? phoenixConfig
  : brandConfig; // Default to HAAIS AIOS
