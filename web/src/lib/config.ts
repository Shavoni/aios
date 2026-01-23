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
  logoIcon: string; // Lucide icon name or URL

  // Footer
  footerText: string;

  // Contact
  supportEmail?: string;
  supportPhone?: string;
}

// Default configuration for Greater Cleveland Partnership
export const brandConfig: BrandConfig = {
  appName: "HAAIS AIOS",
  tagline: "AI Operating System",
  organization: "Greater Cleveland Partnership",

  primaryColor: "blue-600",
  primaryColorLight: "blue-100",
  primaryColorDark: "blue-700",
  accentColor: "slate-600",

  logoIcon: "Building2",

  footerText: "HAAIS AIOS • Powered by DEF1LIVE LLC",

  supportEmail: "support@haais.ai",
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

  footerText: "Cleveland AI Gateway • Powered by HAAIS AIOS",

  supportEmail: "it-support@clevelandohio.gov",
};

// Export active config - can be switched based on environment
export const config = process.env.NEXT_PUBLIC_BRAND === "cleveland"
  ? clevelandConfig
  : brandConfig;
