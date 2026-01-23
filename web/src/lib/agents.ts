/**
 * Cleveland Leadership Asset Registry
 * These agents map to the custom GPTs built for Cleveland's AI Gateway
 */

export interface LeadershipAsset {
  id: string;
  name: string;
  title: string;
  domain: AgentDomain;
  description: string;
  capabilities: string[];
  guardrails: string[];
  escalatesTo: string;
  gptUrl: string;
  status: "active" | "inactive" | "degraded";
  isRouter: boolean;
}

export type AgentDomain =
  | "Router"
  | "Strategy"
  | "PublicHealth"
  | "HR"
  | "Finance"
  | "Building"
  | "311"
  | "Regional";

export const CLEVELAND_AGENTS: LeadershipAsset[] = [
  {
    id: "concierge",
    name: "Cleveland Civic AI Concierge",
    title: "Leadership Asset Router",
    domain: "Router",
    description: "Routes staff to the correct department leadership asset. Clarifies intent with minimal questions, provides safe next steps, and escalates high-risk matters.",
    capabilities: [
      "Intent classification",
      "Department routing",
      "Risk triage",
      "Safe next-step guidance",
    ],
    guardrails: [
      "Minimal clarifying questions",
      "No speculation on policy",
      "Escalate high-risk to human",
    ],
    escalatesTo: "Department Leadership",
    gptUrl: "https://chatgpt.com/g/g-693f69110450819193f6657905a2bc16-1-cleveland-civic-ai-concierge-leadership-asset",
    status: "active",
    isRouter: true,
  },
  {
    id: "strategy",
    name: "Dr. Elizabeth Crowe, PhD",
    title: "Cleveland AI Strategy Advisor",
    domain: "Strategy",
    description: "Strategic advisor for the Cleveland AI opportunity. Provides deep insights, generates deal-making documents, and offers strategic guidance based on comprehensive knowledge base.",
    capabilities: [
      "Strategic guidance",
      "Deal-making documents",
      "Pilot design",
      "Governance modeling",
    ],
    guardrails: [
      "No commitment impersonation",
      "Source-based responses only",
      "Flag missing information",
    ],
    escalatesTo: "City Leadership",
    gptUrl: "https://chatgpt.com/g/g-693f4d79d37881919210e12d92c8c92a-cleveland-ai-strategy-advisor",
    status: "active",
    isRouter: false,
  },
  {
    id: "public-health",
    name: "Dr. David Margolius",
    title: "Director of Public Health (CDPH)",
    domain: "PublicHealth",
    description: "Converts approved program guidance and public advisories into clear staff workflows and resident-facing drafts. Protects sensitive health information, routes high-risk matters to leadership.",
    capabilities: [
      "Staff workflow creation",
      "Resident-facing drafts",
      "Public advisory translation",
      "Health communication",
    ],
    guardrails: [
      "Protect PHI (HIPAA)",
      "No clinical advice",
      "Route PHI requests to privacy/legal",
      "No operational steps for sensitive data",
    ],
    escalatesTo: "Public Health Leadership",
    gptUrl: "https://chatgpt.com/g/g-693f576dc69c8191b7f84287c959f921-cleveland-public-health-leadership-asset",
    status: "active",
    isRouter: false,
  },
  {
    id: "hr",
    name: "Matthew J. Cole",
    title: "HR Leadership Asset",
    domain: "HR",
    description: "Turns HR policies into clear guidance, drafts communications, supports managers, routes sensitive matters to HR leadership. Reinforces responsible AI rules: privacy, fairness, accountability.",
    capabilities: [
      "Policy interpretation",
      "Manager support",
      "Communication drafts",
      "Responsible AI guidance",
    ],
    guardrails: [
      "Privacy protection",
      "Fairness in guidance",
      "No employment decisions",
      "Route sensitive matters to HR leadership",
    ],
    escalatesTo: "HR Leadership",
    gptUrl: "https://chatgpt.com/g/g-693f5cebfc9c8191bb722a89b9b2e0c4-matthew-j-cole-cleveland-hr-leadership-asset",
    status: "active",
    isRouter: false,
  },
  {
    id: "finance",
    name: "Ayesha Bell Hardaway",
    title: "Chief Financial Officer",
    domain: "Finance",
    description: "Explains purchasing rules, budget processes, and vendor workflows from approved policies. Drafts compliant justifications and communications, flags audit risks, routes exceptions for human approval.",
    capabilities: [
      "Purchasing rule guidance",
      "Budget process explanation",
      "Vendor workflow support",
      "Compliant draft generation",
    ],
    guardrails: [
      "No legal advice",
      "Flag audit risks",
      "Route exceptions to human",
      "Source from approved policies only",
    ],
    escalatesTo: "Finance Leadership / Procurement",
    gptUrl: "https://chatgpt.com/g/g-693f60021ab48191a767ca3c2c07b1b6-ayesha-bell-hardaway-finance-leadership-asset",
    status: "active",
    isRouter: false,
  },
  {
    id: "building",
    name: "Sally Martin O'Toole",
    title: "Building & Housing Asset",
    domain: "Building",
    description: "Helps staff and leaders navigate permits, inspections, and customer guidance using approved procedures and code references. Produces consistent explanations, drafts notices, routes complex cases to human experts.",
    capabilities: [
      "Permit guidance",
      "Inspection procedures",
      "Code reference lookup",
      "Notice drafting",
    ],
    guardrails: [
      "Use approved procedures only",
      "Reference specific codes",
      "Route complex cases to experts",
      "No legal interpretations",
    ],
    escalatesTo: "Building & Housing Leadership",
    gptUrl: "https://chatgpt.com/g/g-693f6324e204819187b121395bd2903c-sally-martin-otoole-building-housing-asset",
    status: "active",
    isRouter: false,
  },
  {
    id: "311",
    name: "Kate Connor Warren",
    title: "Director of Cleveland 311",
    domain: "311",
    description: "Improves first-contact resolution by guiding staff with scripts, service catalog rules, and escalation paths. Drafts consistent responses and helps supervisors refine routing and knowledge articles.",
    capabilities: [
      "Script guidance",
      "Service catalog rules",
      "Escalation path routing",
      "Knowledge article refinement",
    ],
    guardrails: [
      "Follow service catalog",
      "Consistent response drafting",
      "Proper escalation paths",
      "No promises outside SLA",
    ],
    escalatesTo: "311 Supervisors",
    gptUrl: "https://chatgpt.com/g/g-693f66e109fc8191aee3b31b2458e2aa-cleveland-311-leadership-asset",
    status: "active",
    isRouter: false,
  },
  {
    id: "gcp",
    name: "Freddy Collier",
    title: "SVP Strategy, Greater Cleveland Partnership",
    domain: "Regional",
    description: "Strategic AI leadership tool that strengthens GCP's regional role by aligning governance, narrative, and cross-sector coordination. Helps Cleveland move from fragmented efforts to unified, responsible AI vision.",
    capabilities: [
      "Regional alignment",
      "Cross-sector coordination",
      "Governance narrative",
      "Unified AI vision",
    ],
    guardrails: [
      "No City commitments",
      "Coordination focus only",
      "Route operational matters to City",
      "Narrative alignment, not execution",
    ],
    escalatesTo: "GCP Leadership",
    gptUrl: "https://chatgpt.com/g/g-6937851af410819181e24dedcc13d98c-leadership-asset-g-c-p-thinkin",
    status: "active",
    isRouter: false,
  },
];

/**
 * Routing map: domain keywords → agent ID
 */
export const ROUTING_MAP: Record<string, string> = {
  // Public Health
  "health": "public-health",
  "clinic": "public-health",
  "medical": "public-health",
  "disease": "public-health",
  "vaccine": "public-health",
  "opioid": "public-health",
  "cdph": "public-health",

  // HR
  "hr": "hr",
  "human resources": "hr",
  "employee": "hr",
  "benefits": "hr",
  "hiring": "hr",
  "termination": "hr",
  "policy": "hr",
  "manager": "hr",

  // Finance
  "finance": "finance",
  "budget": "finance",
  "procurement": "finance",
  "vendor": "finance",
  "purchasing": "finance",
  "contract": "finance",
  "payment": "finance",
  "audit": "finance",

  // Building & Housing
  "building": "building",
  "housing": "building",
  "permit": "building",
  "inspection": "building",
  "code": "building",
  "zoning": "building",

  // 311
  "311": "311",
  "citizen": "311",
  "complaint": "311",
  "service request": "311",
  "pothole": "311",
  "trash": "311",
  "noise": "311",

  // Strategy
  "strategy": "strategy",
  "pilot": "strategy",
  "initiative": "strategy",
  "partnership": "strategy",

  // Regional (GCP)
  "regional": "gcp",
  "gcp": "gcp",
  "partnership": "gcp",
  "coordination": "gcp",
};

/**
 * Get agent by ID
 */
export function getAgent(id: string): LeadershipAsset | undefined {
  return CLEVELAND_AGENTS.find(agent => agent.id === id);
}

/**
 * Get router agent (Concierge)
 */
export function getRouter(): LeadershipAsset {
  return CLEVELAND_AGENTS.find(agent => agent.isRouter)!;
}

/**
 * Route request to appropriate agent based on text
 */
export function routeRequest(text: string): LeadershipAsset {
  const lowerText = text.toLowerCase();

  for (const [keyword, agentId] of Object.entries(ROUTING_MAP)) {
    if (lowerText.includes(keyword)) {
      const agent = getAgent(agentId);
      if (agent) return agent;
    }
  }

  // Default to concierge for unclear requests
  return getRouter();
}

/**
 * Domain colors for UI
 */
export const DOMAIN_COLORS: Record<AgentDomain, string> = {
  Router: "bg-indigo-500",
  Strategy: "bg-violet-500",
  PublicHealth: "bg-red-500",
  HR: "bg-green-500",
  Finance: "bg-cyan-500",
  Building: "bg-amber-500",
  "311": "bg-blue-500",
  Regional: "bg-purple-500",
};
