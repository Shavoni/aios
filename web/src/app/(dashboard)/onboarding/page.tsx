"use client";

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Globe,
  Search,
  Loader2,
  CheckCircle2,
  XCircle,
  Building2,
  Users,
  User,
  Database,
  FileText,
  ChevronRight,
  ChevronLeft,
  Sparkles,
  RefreshCw,
  Rocket,
  AlertCircle,
  Landmark,
  Briefcase,
  Building,
  Heart,
  GraduationCap,
  ShoppingBag,
  Stethoscope,
  Scale,
  Home,
  Link2,
  Upload,
  Shield,
  Plus,
  Trash2,
  ExternalLink,
  Trophy,
} from "lucide-react";
import { CandidateAgentsPanel, CandidateAgent } from "@/components/onboarding/candidate-agents-panel";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// =============================================================================
// Types
// =============================================================================

interface Executive {
  name: string;
  title: string;
  office: string;
  url: string | null;
}

interface Department {
  id: string;
  name: string;
  director: string | null;
  director_title: string | null;
  url: string | null;
  description: string | null;
  suggested_template: string | null;
  contact: {
    email: string | null;
    phone: string | null;
    address: string | null;
  };
}

interface DataPortal {
  type: string;
  url: string;
  api_endpoint: string | null;
}

interface DiscoveryCandidate {
  id: string;
  name: string;
  type: string; // Granular types: executive, cabinet, director, public-safety, finance, etc.
  url: string;
  confidence: "high" | "medium" | "low";
  source_urls: string[];
  suggested_agent_name: string | null;
  metadata: Record<string, unknown>;
  selected: boolean;
}

interface DiscoveryProgress {
  pages_crawled: number;
  departments_detected: number;
  leaders_detected: number;
  services_detected: number;
  data_portals_detected: number;
}

interface DiscoveryResult {
  id: string;
  status: "pending" | "crawling" | "extracting" | "completed" | "failed" | "cancelled" | "awaiting_selection";
  started_at: string;
  completed_at: string | null;
  source_url: string;
  mode: "shallow" | "targeted" | "full";
  municipality: {
    name: string;
    state: string | null;
    website: string;
    population: number | null;
  } | null;
  executive: Executive | null;
  chief_officers: Executive[];
  departments: Department[];
  data_portals: DataPortal[];
  pages_crawled: number;
  error: string | null;
  candidates: DiscoveryCandidate[];
  progress: DiscoveryProgress;
  cancelled: boolean;
}

interface SelectedAgent {
  id: string;
  name: string;
  title: string;
  enabled: boolean;
  director_name: string | null;
  director_title: string | null;
  template_id: string | null;
  gpt_url: string;
  isExecutive?: boolean;
}

interface OrganizationType {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  templates: string[];
  compliancePresets: string[];
  discoveryPatterns: string[];
}

interface Industry {
  id: string;
  name: string;
  icon: React.ElementType;
  compliance: string[];
  agentTemplates: string[];
}

// =============================================================================
// Configuration
// =============================================================================

const ORG_TYPES: OrganizationType[] = [
  {
    id: "municipal",
    name: "City / Municipality",
    description: "Local city government with mayor, council, and departments",
    icon: Landmark,
    templates: ["mayor", "council", "public-health", "public-safety", "utilities", "building", "parks", "finance", "hr", "311"],
    compliancePresets: ["public-records", "foia", "ada"],
    discoveryPatterns: ["mayor", "director", "commissioner", "department"],
  },
  {
    id: "county",
    name: "County Government",
    description: "County-level government with commissioners and agencies",
    icon: Building2,
    templates: ["commissioners", "sheriff", "recorder", "auditor", "prosecutor", "public-health", "social-services"],
    compliancePresets: ["public-records", "foia", "ada"],
    discoveryPatterns: ["commissioner", "sheriff", "agency", "office"],
  },
  {
    id: "school-district",
    name: "School District",
    description: "K-12 school district with superintendent and schools",
    icon: GraduationCap,
    templates: ["superintendent", "curriculum", "student-services", "special-education", "transportation", "food-services", "facilities", "hr", "finance"],
    compliancePresets: ["ferpa", "ada"],
    discoveryPatterns: ["superintendent", "principal", "director", "coordinator"],
  },
  {
    id: "university",
    name: "College / University",
    description: "Higher education institution with colleges and departments",
    icon: GraduationCap,
    templates: ["president", "provost", "admissions", "financial-aid", "registrar", "student-affairs", "academic-advising", "career-services", "housing", "research"],
    compliancePresets: ["ferpa", "ada", "title-ix"],
    discoveryPatterns: ["president", "provost", "dean", "director", "chair"],
  },
  {
    id: "k12-school",
    name: "Individual School",
    description: "Single K-12 school with principal and staff",
    icon: GraduationCap,
    templates: ["principal", "counselor", "front-office", "athletics", "parent-liaison", "special-education"],
    compliancePresets: ["ferpa", "ada"],
    discoveryPatterns: ["principal", "assistant principal", "counselor", "coach"],
  },
  {
    id: "enterprise",
    name: "Enterprise Business",
    description: "Large corporation with 500+ employees",
    icon: Building,
    templates: ["ceo", "cfo", "cto", "sales", "marketing", "engineering", "support", "legal", "hr", "finance"],
    compliancePresets: ["soc2", "gdpr"],
    discoveryPatterns: ["chief", "vp", "director", "head of"],
  },
  {
    id: "smb",
    name: "Small/Medium Business",
    description: "Growing business with teams and departments",
    icon: Briefcase,
    templates: ["owner", "operations", "sales", "support", "admin"],
    compliancePresets: [],
    discoveryPatterns: ["owner", "manager", "team"],
  },
  {
    id: "nonprofit",
    name: "Non-Profit Organization",
    description: "Mission-driven organization with programs and services",
    icon: Heart,
    templates: ["executive-director", "programs", "development", "volunteers", "communications"],
    compliancePresets: ["501c3"],
    discoveryPatterns: ["executive director", "program", "coordinator"],
  },
  {
    id: "nil-collective",
    name: "NIL Collective / Agency",
    description: "Manage NIL deals and opportunities for college athletes",
    icon: Trophy,
    templates: ["athlete-relations", "brand-partnerships", "deal-negotiation", "compliance", "social-media", "finance", "legal"],
    compliancePresets: ["nil-compliance", "ftc-endorsement"],
    discoveryPatterns: ["director", "manager", "coordinator", "agent"],
  },
  {
    id: "nil-university",
    name: "University NIL Office",
    description: "University compliance and support for athlete NIL activities",
    icon: GraduationCap,
    templates: ["nil-compliance-officer", "athlete-education", "brand-vetting", "disclosure-management", "tax-guidance"],
    compliancePresets: ["nil-compliance", "ncaa", "ferpa"],
    discoveryPatterns: ["compliance", "director", "coordinator", "advisor"],
  },
];

const INDUSTRIES: Industry[] = [
  {
    id: "healthcare",
    name: "Healthcare",
    icon: Stethoscope,
    compliance: ["hipaa"],
    agentTemplates: ["patient-services", "clinical-support", "billing", "scheduling"],
  },
  {
    id: "legal",
    name: "Legal Services",
    icon: Scale,
    compliance: [],
    agentTemplates: ["intake", "case-management", "research", "client-services"],
  },
  {
    id: "education",
    name: "Education",
    icon: GraduationCap,
    compliance: ["ferpa"],
    agentTemplates: ["admissions", "student-services", "academic-support", "financial-aid"],
  },
  {
    id: "sports-nil",
    name: "Sports / NIL",
    icon: Trophy,
    compliance: ["nil-compliance", "ftc-endorsement"],
    agentTemplates: ["athlete-relations", "deal-management", "brand-partnerships", "compliance", "social-media"],
  },
  {
    id: "retail",
    name: "Retail / E-Commerce",
    icon: ShoppingBag,
    compliance: [],
    agentTemplates: ["customer-service", "order-support", "returns", "product-info"],
  },
  {
    id: "realestate",
    name: "Real Estate",
    icon: Home,
    compliance: [],
    agentTemplates: ["listings", "buyer-support", "seller-support", "property-management"],
  },
  {
    id: "general",
    name: "General / Other",
    icon: Briefcase,
    compliance: [],
    agentTemplates: ["customer-service", "sales", "support", "hr"],
  },
];

const COMPLIANCE_PRESETS: Record<string, { name: string; guardrails: string[] }> = {
  hipaa: {
    name: "HIPAA Compliance",
    guardrails: [
      "NEVER store, process, or transmit Protected Health Information (PHI)",
      "NEVER discuss specific patient cases or medical records",
      "Always direct medical questions to licensed healthcare providers",
      "Maintain strict confidentiality of all health-related inquiries",
    ],
  },
  ferpa: {
    name: "FERPA Compliance",
    guardrails: [
      "NEVER disclose student education records without proper authorization",
      "NEVER share personally identifiable student information",
      "Direct all records requests through official channels",
      "Protect student privacy in all interactions",
    ],
  },
  "title-ix": {
    name: "Title IX Compliance",
    guardrails: [
      "Provide information about Title IX reporting procedures when relevant",
      "Direct all complaints of discrimination or harassment to Title IX Coordinator",
      "NEVER attempt to investigate or adjudicate Title IX matters",
      "Maintain confidentiality while ensuring proper reporting",
      "Provide supportive measures information to complainants",
    ],
  },
  ada: {
    name: "ADA Compliance",
    guardrails: [
      "Provide information about accommodation request procedures",
      "Direct accessibility concerns to appropriate ADA coordinator",
      "Ensure responses are accessible and inclusive",
      "Support reasonable accommodation processes",
    ],
  },
  gdpr: {
    name: "GDPR Compliance",
    guardrails: [
      "Respect data subject rights including right to erasure",
      "NEVER process personal data without lawful basis",
      "Maintain transparency about data processing activities",
      "Implement data minimization principles",
    ],
  },
  soc2: {
    name: "SOC2 Compliance",
    guardrails: [
      "Maintain confidentiality of proprietary information",
      "Log and audit all sensitive operations",
      "Follow principle of least privilege for data access",
      "Protect system integrity and availability",
    ],
  },
  "public-records": {
    name: "Public Records",
    guardrails: [
      "Be aware that communications may be subject to public records requests",
      "NEVER delete records that may be subject to retention requirements",
      "Maintain transparency in government operations",
    ],
  },
  foia: {
    name: "FOIA Compliance",
    guardrails: [
      "Support Freedom of Information Act requirements",
      "Direct records requests to appropriate records custodian",
      "Maintain awareness of exemption categories",
    ],
  },
  "501c3": {
    name: "501(c)(3) Non-Profit",
    guardrails: [
      "NEVER engage in political campaign activities",
      "Limit lobbying activities according to regulations",
      "Maintain transparency about organizational mission and finances",
      "Support donor privacy while meeting disclosure requirements",
    ],
  },
  "nil-compliance": {
    name: "NIL Compliance",
    guardrails: [
      "NEVER facilitate pay-for-play arrangements or recruitment inducements",
      "Ensure all NIL activities comply with state-specific NIL laws",
      "Require proper disclosure of NIL relationships per FTC guidelines",
      "Verify athlete eligibility status before facilitating any deals",
      "NEVER share confidential deal terms without authorization",
      "Ensure deals are based on fair market value for services rendered",
      "Maintain records of all NIL agreements for compliance audits",
      "Direct questions about NCAA rules to compliance officers",
    ],
  },
  ncaa: {
    name: "NCAA Compliance",
    guardrails: [
      "NEVER provide information that could jeopardize athlete eligibility",
      "Direct all eligibility questions to institutional compliance staff",
      "NEVER facilitate improper benefits or recruiting violations",
      "Maintain awareness of current NCAA NIL guidance and bylaws",
      "Support institutional disclosure requirements",
    ],
  },
  "ftc-endorsement": {
    name: "FTC Endorsement Guidelines",
    guardrails: [
      "Require clear and conspicuous disclosure of material connections",
      "Ensure athletes understand #ad and sponsorship disclosure requirements",
      "NEVER facilitate undisclosed paid endorsements",
      "Verify endorsement claims are truthful and substantiated",
      "Maintain documentation of disclosure compliance",
    ],
  },
};

const PRESETS: Preset[] = [
  {
    id: "city-government",
    name: "City Government",
    description: "Mayor's office, city departments, and public services",
    icon: Landmark,
    orgType: "municipal",
    industry: "general",
    gradient: "from-blue-500 to-indigo-600",
    suggestedAgents: [
      { name: "Mayor's Office", title: "Executive Assistant", template: "mayors-command-center" },
      { name: "Public Safety", title: "Director", template: "public-safety" },
      { name: "Public Works", title: "Director", template: "utilities" },
      { name: "Parks & Recreation", title: "Director", template: "parks" },
      { name: "Finance", title: "Director", template: "finance" },
      { name: "Human Resources", title: "Director", template: "hr" },
    ],
  },
  {
    id: "school-district",
    name: "School District",
    description: "K-12 education with superintendent and departments",
    icon: GraduationCap,
    orgType: "school-district",
    industry: "education",
    gradient: "from-emerald-500 to-teal-600",
    suggestedAgents: [
      { name: "Superintendent's Office", title: "Executive Assistant", template: "superintendent" },
      { name: "Curriculum & Instruction", title: "Director", template: "curriculum" },
      { name: "Student Services", title: "Director", template: "student-services" },
      { name: "Special Education", title: "Coordinator", template: "special-education" },
      { name: "Transportation", title: "Director", template: "transportation" },
    ],
  },
  {
    id: "university",
    name: "University / College",
    description: "Higher education with admissions, registrar, and student services",
    icon: GraduationCap,
    orgType: "university",
    industry: "education",
    gradient: "from-purple-500 to-violet-600",
    suggestedAgents: [
      { name: "President's Office", title: "Executive Assistant", template: "president" },
      { name: "Admissions", title: "Director", template: "admissions" },
      { name: "Financial Aid", title: "Director", template: "financial-aid" },
      { name: "Registrar", title: "Registrar", template: "registrar" },
      { name: "Student Affairs", title: "Dean", template: "student-affairs" },
    ],
  },
  {
    id: "healthcare-org",
    name: "Healthcare Organization",
    description: "HIPAA-compliant patient services and clinical support",
    icon: Stethoscope,
    orgType: "enterprise",
    industry: "healthcare",
    gradient: "from-rose-500 to-pink-600",
    suggestedAgents: [
      { name: "Patient Services", title: "Director", template: "patient-services" },
      { name: "Scheduling", title: "Coordinator", template: "scheduling" },
      { name: "Billing", title: "Manager", template: "billing" },
      { name: "Clinical Support", title: "Director", template: "clinical-support" },
    ],
  },
  {
    id: "nil-collective",
    name: "NIL Collective",
    description: "Athlete brand deals, compliance, and partnership management",
    icon: Trophy,
    orgType: "nil-collective",
    industry: "sports-nil",
    gradient: "from-amber-500 to-orange-600",
    suggestedAgents: [
      { name: "Athlete Relations", title: "Director", template: "athlete-relations" },
      { name: "Brand Partnerships", title: "Manager", template: "brand-partnerships" },
      { name: "Compliance", title: "Officer", template: "compliance" },
      { name: "Social Media", title: "Coordinator", template: "social-media" },
    ],
  },
  {
    id: "small-business",
    name: "Small Business",
    description: "Lean team with sales, support, and operations",
    icon: Briefcase,
    orgType: "smb",
    industry: "general",
    gradient: "from-cyan-500 to-blue-600",
    suggestedAgents: [
      { name: "Sales", title: "Representative", template: "sales" },
      { name: "Customer Support", title: "Agent", template: "support" },
      { name: "Operations", title: "Manager", template: "operations" },
    ],
  },
];

type WizardStep = "start" | "type" | "industry" | "source" | "discovering" | "candidates" | "select" | "link-gpts" | "review" | "deploy";

interface Preset {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  orgType: string;
  industry: string;
  suggestedAgents: { name: string; title: string; template: string }[];
  gradient: string;
}

// =============================================================================
// Component
// =============================================================================

export default function OnboardingPage() {
  // Wizard state
  const [step, setStep] = useState<WizardStep>("start");
  const [selectedPreset, setSelectedPreset] = useState<Preset | null>(null);
  const [orgType, setOrgType] = useState<OrganizationType | null>(null);
  const [industry, setIndustry] = useState<Industry | null>(null);
  const [sourceType, setSourceType] = useState<"website" | "manual">("website");

  // Discovery state
  const [url, setUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [discovery, setDiscovery] = useState<DiscoveryResult | null>(null);
  const [candidates, setCandidates] = useState<DiscoveryCandidate[]>([]);

  // Agent configuration
  const [selectedAgents, setSelectedAgents] = useState<SelectedAgent[]>([]);
  const [orgName, setOrgName] = useState("");
  const [bulkGptUrls, setBulkGptUrls] = useState("");

  // Deployment
  const [configId, setConfigId] = useState<string | null>(null);
  const [isDeploying, setIsDeploying] = useState(false);
  const [deployStatus, setDeployStatus] = useState<string | null>(null);

  // Poll for discovery status
  useEffect(() => {
    if (!jobId || step !== "discovering") return;

    const pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/onboarding/discover/${jobId}`);
        if (res.ok) {
          const data: DiscoveryResult = await res.json();
          setDiscovery(data);

          if (data.status === "awaiting_selection") {
            // Shallow crawl complete, show candidate selection
            clearInterval(pollInterval);
            setCandidates(data.candidates || []);
            setOrgName(data.municipality?.name || "");
            setStep("candidates");
          } else if (data.status === "completed") {
            // Full/legacy mode - go straight to agent selection
            clearInterval(pollInterval);
            initializeAgentsFromDiscovery(data);
            setStep("select");
          } else if (data.status === "failed") {
            clearInterval(pollInterval);
            setError(data.error || "Discovery failed");
            setStep("source");
          } else if (data.status === "cancelled") {
            clearInterval(pollInterval);
            setStep("start");
          }
        }
      } catch (err) {
        console.error("Poll error:", err);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [jobId, step]);

  // Cancel discovery
  const cancelDiscovery = async () => {
    if (!jobId) return;

    try {
      await fetch(`${API_BASE}/onboarding/discover/${jobId}/cancel`, {
        method: "POST",
      });
      setStep("start");
      setJobId(null);
      setDiscovery(null);
    } catch (err) {
      console.error("Cancel error:", err);
    }
  };

  // Convert DiscoveryCandidate to CandidateAgent for the panel
  const convertToCandidateAgents = useCallback(
    (discoveryCandidates: DiscoveryCandidate[]): CandidateAgent[] => {
      return discoveryCandidates.map((c) => ({
        id: c.id,
        name: c.name,
        type: c.type,
        department: (c.metadata?.department as string) || undefined,
        description: (c.metadata?.description as string) || undefined,
        confidence: c.confidence,
        confidenceScore:
          c.confidence === "high" ? 90 : c.confidence === "medium" ? 60 : 30,
        sourceUrls: c.source_urls || [],
        suggestedAgentName: c.suggested_agent_name || undefined,
        tags: (c.metadata?.tags as string[]) || undefined,
        metadata: c.metadata,
        selected: c.selected,
      }));
    },
    []
  );

  // Convert CandidateAgent back to DiscoveryCandidate
  const convertToDiscoveryCandidates = useCallback(
    (candidateAgents: CandidateAgent[]): DiscoveryCandidate[] => {
      return candidateAgents.map((c) => ({
        id: c.id,
        name: c.name,
        type: c.type,
        url: c.sourceUrls[0] || "",
        confidence: c.confidence,
        source_urls: c.sourceUrls,
        suggested_agent_name: c.suggestedAgentName || null,
        metadata: c.metadata || {},
        selected: c.selected,
      }));
    },
    []
  );

  // Handle selection changes from CandidateAgentsPanel
  const handleCandidateSelectionChange = useCallback(
    (updatedAgents: CandidateAgent[]) => {
      const discoveryCandidates = convertToDiscoveryCandidates(updatedAgents);
      setCandidates(discoveryCandidates);
    },
    [convertToDiscoveryCandidates]
  );

  // Handle "Create Agents" from CandidateAgentsPanel
  const handleCreateAgentsFromPanel = useCallback(
    async (selectedAgents: CandidateAgent[]) => {
      if (!jobId) return;

      setIsLoading(true);
      try {
        // Update selections on the server
        const selections: Record<string, boolean> = {};
        candidates.forEach((c) => {
          const isSelected = selectedAgents.some((s) => s.id === c.id);
          selections[c.id] = isSelected;
        });

        await fetch(`${API_BASE}/onboarding/discover/${jobId}/candidates`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ selections }),
        });

        // Convert selected to DiscoveryCandidates for agent initialization
        const selectedDiscoveryCandidates = convertToDiscoveryCandidates(selectedAgents);
        initializeAgentsFromCandidates(selectedDiscoveryCandidates);
        setStep("select");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to create agents");
      } finally {
        setIsLoading(false);
      }
    },
    [jobId, candidates, convertToDiscoveryCandidates]
  );

  // Initialize agents from candidates
  const initializeAgentsFromCandidates = (candidateList: DiscoveryCandidate[]) => {
    const agents: SelectedAgent[] = candidateList.map((c, index) => ({
      id: c.id,
      name: c.name,
      title: c.suggested_agent_name || `${c.name} Assistant`,
      enabled: true,
      director_name: (c.metadata?.director as string) || null,
      director_title: (c.metadata?.director_title as string) || null,
      template_id: (c.metadata?.template as string) || null,
      gpt_url: "",
      isExecutive: c.type === "leadership" && index === 0,
    }));
    setSelectedAgents(agents);
  };

  const initializeAgentsFromDiscovery = (data: DiscoveryResult) => {
    const agents: SelectedAgent[] = [];

    // Add executive if found
    if (data.executive) {
      agents.push({
        id: "executive",
        name: data.executive.name,
        title: data.executive.title,
        enabled: true,
        director_name: data.executive.name,
        director_title: data.executive.title,
        template_id: orgType?.id === "municipal" ? "mayors-command-center" : "executive",
        gpt_url: "",
        isExecutive: true,
      });
    }

    // Add departments
    data.departments.forEach((dept) => {
      agents.push({
        id: dept.id,
        name: dept.name,
        title: dept.director_title || "Director",
        enabled: true,
        director_name: dept.director,
        director_title: dept.director_title,
        template_id: dept.suggested_template,
        gpt_url: "",
      });
    });

    // Add chief officers
    data.chief_officers.forEach((officer, i) => {
      agents.push({
        id: `officer-${i}`,
        name: officer.name,
        title: officer.title,
        enabled: true,
        director_name: officer.name,
        director_title: officer.title,
        template_id: null,
        gpt_url: "",
      });
    });

    setSelectedAgents(agents);
    setOrgName(data.municipality?.name || "");
  };

  const startDiscovery = async () => {
    if (!url.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      // Send raw input as 'query' - backend resolver handles URL normalization
      // and organization name lookup (e.g., "CNN" -> cnn.com)
      const res = await fetch(`${API_BASE}/onboarding/discover`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: url.trim() }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to start discovery");
      }

      const data = await res.json();
      setJobId(data.job_id);
      setStep("discovering");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start discovery");
    } finally {
      setIsLoading(false);
    }
  };

  const addManualAgent = () => {
    const newAgent: SelectedAgent = {
      id: `manual-${Date.now()}`,
      name: "",
      title: "",
      enabled: true,
      director_name: null,
      director_title: null,
      template_id: null,
      gpt_url: "",
    };
    setSelectedAgents([...selectedAgents, newAgent]);
  };

  const updateAgent = (id: string, updates: Partial<SelectedAgent>) => {
    setSelectedAgents((prev) =>
      prev.map((a) => (a.id === id ? { ...a, ...updates } : a))
    );
  };

  const removeAgent = (id: string) => {
    setSelectedAgents((prev) => prev.filter((a) => a.id !== id));
  };

  const toggleAgent = (id: string) => {
    setSelectedAgents((prev) =>
      prev.map((a) => (a.id === id ? { ...a, enabled: !a.enabled } : a))
    );
  };

  const parseBulkGptUrls = () => {
    const lines = bulkGptUrls.split("\n").filter((l) => l.trim());
    const urlPattern = /https:\/\/chatgpt\.com\/g\/[^\s]+/g;

    lines.forEach((line, index) => {
      const match = line.match(urlPattern);
      if (match && selectedAgents[index]) {
        updateAgent(selectedAgents[index].id, { gpt_url: match[0] });
      }
    });
  };

  const deployAgents = async () => {
    setIsDeploying(true);
    setError(null);
    setDeployStatus("Submitting agents for approval...");

    try {
      const enabledAgents = selectedAgents.filter((a) => a.enabled);

      // Build agent data for pending queue
      const pendingAgents = enabledAgents.map((agent) => ({
        id: agent.id.replace(/[^a-z0-9-]/gi, "-").toLowerCase(),
        name: agent.director_name || agent.name,
        title: agent.title,
        domain: agent.template_id || "General",
        description: `AI assistant for ${agent.name}. ${agent.title ? `Serving as ${agent.title}.` : ""}`,
        capabilities: industry?.agentTemplates || [],
        guardrails: industry?.compliance.flatMap(c => COMPLIANCE_PRESETS[c]?.guardrails || []) || [],
        gpt_url: agent.gpt_url,
        system_prompt: `You are an AI assistant for ${agent.name}. ${agent.title ? `You serve as ${agent.title}.` : ""}\n\nOrganization: ${orgName}\nType: ${orgType?.name}\nIndustry: ${industry?.name}`,
        source: "discovery",
      }));

      // Submit to pending approval queue
      const res = await fetch(`${API_BASE}/system/pending-agents/bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(pendingAgents),
      });

      if (!res.ok) {
        throw new Error("Failed to submit agents for approval");
      }

      const result = await res.json();
      setDeployStatus(`${result.added} agents submitted for approval. Go to Approvals to review.`);
      setStep("deploy");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Deployment failed");
      setDeployStatus(null);
    } finally {
      setIsDeploying(false);
    }
  };

  const resetWizard = () => {
    setStep("start");
    setSelectedPreset(null);
    setOrgType(null);
    setIndustry(null);
    setSourceType("website");
    setUrl("");
    setJobId(null);
    setDiscovery(null);
    setCandidates([]);
    setSelectedAgents([]);
    setOrgName("");
    setBulkGptUrls("");
    setConfigId(null);
    setError(null);
    setDeployStatus(null);
  };

  const applyPreset = (preset: Preset) => {
    setSelectedPreset(preset);

    // Set org type
    const foundOrgType = ORG_TYPES.find(o => o.id === preset.orgType);
    if (foundOrgType) setOrgType(foundOrgType);

    // Set industry
    const foundIndustry = INDUSTRIES.find(i => i.id === preset.industry);
    if (foundIndustry) setIndustry(foundIndustry);

    // Create suggested agents
    const agents: SelectedAgent[] = preset.suggestedAgents.map((agent, index) => ({
      id: `preset-${index}`,
      name: agent.name,
      title: agent.title,
      enabled: true,
      director_name: null,
      director_title: agent.title,
      template_id: agent.template,
      gpt_url: "",
      isExecutive: index === 0,
    }));

    setSelectedAgents(agents);
    setOrgName(preset.name + " Organization");
    setStep("select");
  };

  const startManualOnboarding = () => {
    setSelectedPreset(null);
    setStep("type");
  };

  const getStepIndex = (s: WizardStep) => {
    const steps: WizardStep[] = ["start", "type", "industry", "source", "discovering", "candidates", "select", "link-gpts", "review", "deploy"];
    return steps.indexOf(s);
  };

  const canGoBack = () => {
    return !["start", "discovering", "deploy"].includes(step);
  };

  const goBack = () => {
    const stepMap: Record<WizardStep, WizardStep> = {
      start: "start",
      type: "start",
      industry: "type",
      source: "industry",
      discovering: "source",
      candidates: "start",  // Go back to start from candidate selection
      select: selectedPreset ? "start" : (candidates.length > 0 ? "candidates" : "source"),
      "link-gpts": "select",
      review: "link-gpts",
      deploy: "review",
    };
    setStep(stepMap[step]);
  };

  // =============================================================================
  // Render
  // =============================================================================

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header with Gradient */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-violet-600 via-purple-600 to-indigo-600 p-6 text-white shadow-xl">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDM0aDR2MmgtNHYtMnptMC04aDR2Nmg0djJoLTh2LTh6bTAgMTZoOHYyaC04di0yem0tMTYgMGg0djJoLTR2LTJ6bTAtOGg0djZoNHYyaC04di04em0wIDE2aDh2Mmgtxdi0yeiIvPjwvZz48L2c+PC9zdmc+')] opacity-30"></div>
        <div className="relative">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/20 backdrop-blur-sm">
                <Sparkles className="h-8 w-8" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight">
                  {step === "start" ? "Welcome to AIOS" : "Onboarding Wizard"}
                </h1>
                <p className="text-white/80">
                  {step === "start"
                    ? "Get your AI agents up and running in minutes"
                    : selectedPreset
                    ? `Setting up: ${selectedPreset.name}`
                    : "Set up AI agents for your organization"}
                </p>
              </div>
            </div>
            {step !== "start" && step !== "deploy" && (
              <Button
                variant="ghost"
                size="sm"
                onClick={resetWizard}
                className="text-white/80 hover:text-white hover:bg-white/20"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Start Over
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Progress Steps - Only show after start step */}
      {step !== "start" && (
        <Card className="border-0 shadow-md">
          <CardContent className="p-4">
            <div className="flex items-center justify-between overflow-x-auto pb-1">
              {[
                { id: "type", label: "Org Type", icon: Building2 },
                { id: "industry", label: "Industry", icon: Briefcase },
                { id: "source", label: "Discover", icon: Globe },
                { id: "candidates", label: "Review", icon: CheckCircle2 },
                { id: "select", label: "Agents", icon: Users },
                { id: "link-gpts", label: "Link GPTs", icon: Link2 },
                { id: "review", label: "Confirm", icon: Shield },
                { id: "deploy", label: "Deploy", icon: Rocket },
              ].map((s, i) => {
                const isActive = step === s.id ||
                  (step === "discovering" && s.id === "source") ||
                  (step === "candidates" && s.id === "candidates");
                const isComplete = getStepIndex(step) > getStepIndex(s.id as WizardStep);
                const Icon = s.icon;

                return (
                  <div key={s.id} className="flex items-center flex-1">
                    <div className="flex flex-col items-center flex-1">
                      <div
                        className={`flex items-center justify-center w-10 h-10 rounded-xl text-sm font-medium transition-all ${
                          isActive
                            ? "bg-gradient-to-br from-violet-500 to-purple-600 text-white shadow-lg scale-110"
                            : isComplete
                            ? "bg-green-500 text-white"
                            : "bg-muted text-muted-foreground"
                        }`}
                      >
                        {isComplete ? <CheckCircle2 className="w-5 h-5" /> : <Icon className="w-5 h-5" />}
                      </div>
                      <span className={`mt-2 text-xs font-medium ${isActive ? "text-purple-600" : isComplete ? "text-green-600" : "text-muted-foreground"}`}>
                        {s.label}
                      </span>
                    </div>
                    {i < 6 && (
                      <div className={`h-0.5 w-full mx-2 ${isComplete ? "bg-green-500" : "bg-muted"}`} />
                    )}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error Display */}
      {error && (
        <Card className="border-0 shadow-md bg-gradient-to-r from-red-50 to-rose-50 dark:from-red-950/30 dark:to-rose-950/30 border-l-4 border-l-red-500">
          <CardContent className="flex items-center gap-3 py-4">
            <div className="p-2 rounded-lg bg-red-100 dark:bg-red-900/50">
              <XCircle className="w-5 h-5 text-red-600" />
            </div>
            <span className="text-red-700 dark:text-red-400 flex-1 font-medium">{error}</span>
            <Button variant="ghost" size="sm" onClick={() => setError(null)} className="hover:bg-red-100 dark:hover:bg-red-900/30">
              Dismiss
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Step 0: Start - Choose Preset or Manual */}
      {step === "start" && (
        <div className="space-y-6">
          {/* Discover from Website - Most prominent option */}
          <Card className="border-0 shadow-lg overflow-hidden">
            <div className="bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 p-6">
              <div className="flex items-center gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/20 backdrop-blur-sm">
                  <Globe className="h-8 w-8 text-white" />
                </div>
                <div className="text-white flex-1">
                  <h2 className="text-xl font-bold">Discover from Website</h2>
                  <p className="text-white/80">Drop in a city or organization URL and we'll auto-discover the structure</p>
                </div>
              </div>
            </div>
            <CardContent className="p-6">
              <div className="flex gap-3">
                <Input
                  placeholder="e.g., clevelandohio.gov, chicago.gov, your-company.com"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && url.trim()) {
                      // Set default org type for discovery
                      const cityOrg = ORG_TYPES.find(o => o.id === "municipal");
                      const generalIndustry = INDUSTRIES.find(i => i.id === "general");
                      if (cityOrg) setOrgType(cityOrg);
                      if (generalIndustry) setIndustry(generalIndustry);
                      startDiscovery();
                    }
                  }}
                  className="flex-1 h-12 text-lg"
                />
                <Button
                  onClick={() => {
                    // Set default org type for discovery
                    const cityOrg = ORG_TYPES.find(o => o.id === "municipal");
                    const generalIndustry = INDUSTRIES.find(i => i.id === "general");
                    if (cityOrg) setOrgType(cityOrg);
                    if (generalIndustry) setIndustry(generalIndustry);
                    startDiscovery();
                  }}
                  disabled={isLoading || !url.trim()}
                  className="h-12 px-8 bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700"
                >
                  {isLoading ? (
                    <Loader2 className="w-5 h-5 animate-spin mr-2" />
                  ) : (
                    <Search className="w-5 h-5 mr-2" />
                  )}
                  Discover
                </Button>
              </div>
              <div className="flex items-center gap-4 mt-4 text-sm text-muted-foreground">
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                  Auto-detect departments
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                  Find leadership info
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                  Discover data portals
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-muted" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-background px-4 text-sm text-muted-foreground font-medium">
                or choose a preset
              </span>
            </div>
          </div>

          {/* Quick Start with Presets */}
          <Card className="border-0 shadow-lg">
            <CardHeader className="border-b bg-muted/30">
              <CardTitle className="flex items-center gap-2">
                <Rocket className="h-5 w-5 text-purple-500" />
                Quick Start with Presets
              </CardTitle>
              <CardDescription>
                Choose a pre-configured template to get started immediately
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {PRESETS.map((preset, index) => {
                  const Icon = preset.icon;
                  return (
                    <button
                      key={preset.id}
                      onClick={() => applyPreset(preset)}
                      className="group relative p-5 rounded-xl border-2 border-muted text-left transition-all hover:border-purple-300 hover:shadow-lg dark:hover:border-purple-700 overflow-hidden animate-in fade-in"
                      style={{ animationDelay: `${index * 50}ms` }}
                    >
                      {/* Gradient overlay on hover */}
                      <div className={`absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity bg-gradient-to-br ${preset.gradient}`} />

                      <div className="relative">
                        <div className={`inline-flex p-3 rounded-xl mb-3 bg-gradient-to-br ${preset.gradient} shadow-md`}>
                          <Icon className="w-6 h-6 text-white" />
                        </div>
                        <h3 className="font-semibold text-lg group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">
                          {preset.name}
                        </h3>
                        <p className="text-sm text-muted-foreground mt-1">
                          {preset.description}
                        </p>
                        <div className="flex items-center gap-2 mt-3 text-xs text-muted-foreground">
                          <Users className="w-3 h-3" />
                          <span>{preset.suggestedAgents.length} pre-configured agents</span>
                        </div>
                      </div>

                      {/* Arrow indicator */}
                      <div className="absolute right-4 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-all group-hover:translate-x-1">
                        <ChevronRight className="w-5 h-5 text-purple-500" />
                      </div>
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Manual Onboarding - Compact version */}
          <Card className="border-0 shadow-md border border-dashed border-muted hover:border-purple-300 dark:hover:border-purple-700 transition-colors">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-xl bg-muted">
                    <Users className="w-5 h-5 text-muted-foreground" />
                  </div>
                  <div>
                    <span className="font-medium">Need full control?</span>
                    <span className="text-muted-foreground ml-2">Configure organization type, industry, and agents manually</span>
                  </div>
                </div>
                <Button
                  onClick={startManualOnboarding}
                  variant="ghost"
                  className="hover:bg-purple-50 dark:hover:bg-purple-950/30"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Manual Setup
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Help Section */}
          <Card className="border-0 shadow-md bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-950/30 dark:to-emerald-950/30 border border-green-100 dark:border-green-800">
            <CardContent className="p-5">
              <div className="flex items-start gap-4">
                <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/50">
                  <Sparkles className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <h4 className="font-semibold text-green-800 dark:text-green-200">Recommended: Discover from Website</h4>
                  <p className="text-sm text-green-700 dark:text-green-300 mt-1">
                    Just paste a city or organization URL above. We'll automatically crawl the site to find
                    departments, leadership, and data sources - then generate agents for each one.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Step 1: Organization Type */}
      {step === "type" && (
        <div className="space-y-6">
          <Card className="border-0 shadow-lg">
            <CardHeader className="border-b bg-muted/30">
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5 text-muted-foreground" />
                What type of organization?
              </CardTitle>
              <CardDescription>
                Select the type that best describes your organization
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {ORG_TYPES.map((type) => {
                  const Icon = type.icon;
                  const isSelected = orgType?.id === type.id;

                  return (
                    <button
                      key={type.id}
                      onClick={() => setOrgType(type)}
                      className={`group p-4 rounded-xl border-2 text-left transition-all hover:shadow-md ${
                        isSelected
                          ? "border-purple-500 bg-gradient-to-br from-purple-50 to-violet-50 dark:from-purple-950/30 dark:to-violet-950/30 shadow-md"
                          : "border-muted hover:border-purple-300 dark:hover:border-purple-700"
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className={`p-2.5 rounded-xl transition-all ${
                          isSelected
                            ? "bg-gradient-to-br from-purple-500 to-violet-600 text-white shadow-md"
                            : "bg-muted group-hover:bg-purple-100 dark:group-hover:bg-purple-900/30"
                        }`}>
                          <Icon className={`w-5 h-5 ${isSelected ? "text-white" : "text-muted-foreground group-hover:text-purple-600"}`} />
                        </div>
                        <div>
                          <div className={`font-medium ${isSelected ? "text-purple-700 dark:text-purple-300" : ""}`}>{type.name}</div>
                          <div className="text-sm text-muted-foreground mt-1">
                            {type.description}
                          </div>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button
              onClick={() => setStep("industry")}
              disabled={!orgType}
              className="bg-gradient-to-r from-purple-500 to-violet-600 hover:from-purple-600 hover:to-violet-700"
            >
              Continue
              <ChevronRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Industry */}
      {step === "industry" && (
        <div className="space-y-6">
          <Card className="border-0 shadow-lg">
            <CardHeader className="border-b bg-muted/30">
              <CardTitle className="flex items-center gap-2">
                <Briefcase className="h-5 w-5 text-muted-foreground" />
                What industry?
              </CardTitle>
              <CardDescription>
                This helps us apply the right compliance guardrails and templates
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {INDUSTRIES.map((ind) => {
                  const Icon = ind.icon;
                  const isSelected = industry?.id === ind.id;

                  return (
                    <button
                      key={ind.id}
                      onClick={() => setIndustry(ind)}
                      className={`group p-4 rounded-xl border-2 text-left transition-all hover:shadow-md ${
                        isSelected
                          ? "border-purple-500 bg-gradient-to-br from-purple-50 to-violet-50 dark:from-purple-950/30 dark:to-violet-950/30 shadow-md"
                          : "border-muted hover:border-purple-300 dark:hover:border-purple-700"
                      }`}
                    >
                      <div className={`inline-flex p-2.5 rounded-xl mb-3 transition-all ${
                        isSelected
                          ? "bg-gradient-to-br from-purple-500 to-violet-600 text-white shadow-md"
                          : "bg-muted group-hover:bg-purple-100 dark:group-hover:bg-purple-900/30"
                      }`}>
                        <Icon className={`w-5 h-5 ${isSelected ? "text-white" : "text-muted-foreground group-hover:text-purple-600"}`} />
                      </div>
                      <div className={`font-medium ${isSelected ? "text-purple-700 dark:text-purple-300" : ""}`}>{ind.name}</div>
                      {ind.compliance.length > 0 && (
                        <div className="flex gap-1 mt-2 flex-wrap">
                          {ind.compliance.slice(0, 2).map((c) => (
                            <Badge key={c} variant="secondary" className="text-xs bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                              {c.toUpperCase()}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-between">
            <Button variant="outline" onClick={goBack}>
              <ChevronLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            <Button
              onClick={() => setStep("source")}
              disabled={!industry}
              className="bg-gradient-to-r from-purple-500 to-violet-600 hover:from-purple-600 hover:to-violet-700"
            >
              Continue
              <ChevronRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </div>
      )}

      {/* Step 3: Source */}
      {step === "source" && (
        <div className="space-y-6">
          <Card className="border-0 shadow-lg">
            <CardHeader className="border-b bg-muted/30">
              <CardTitle className="flex items-center gap-2">
                <Globe className="h-5 w-5 text-muted-foreground" />
                How would you like to set up agents?
              </CardTitle>
              <CardDescription>
                We can discover your org structure automatically or you can add agents manually
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              {/* Source Type Toggle */}
              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={() => setSourceType("website")}
                  className={`group p-6 rounded-xl border-2 text-center transition-all hover:shadow-md ${
                    sourceType === "website"
                      ? "border-purple-500 bg-gradient-to-br from-purple-50 to-violet-50 dark:from-purple-950/30 dark:to-violet-950/30 shadow-md"
                      : "border-muted hover:border-purple-300 dark:hover:border-purple-700"
                  }`}
                >
                  <div className={`inline-flex p-3 rounded-xl mb-3 transition-all ${
                    sourceType === "website"
                      ? "bg-gradient-to-br from-purple-500 to-violet-600 text-white shadow-md"
                      : "bg-muted group-hover:bg-purple-100 dark:group-hover:bg-purple-900/30"
                  }`}>
                    <Globe className={`w-8 h-8 ${sourceType === "website" ? "text-white" : "text-muted-foreground group-hover:text-purple-600"}`} />
                  </div>
                  <div className={`font-semibold text-lg ${sourceType === "website" ? "text-purple-700 dark:text-purple-300" : ""}`}>
                    Discover from Website
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">
                    We'll crawl your website to find officials and departments
                  </div>
                </button>
                <button
                  onClick={() => setSourceType("manual")}
                  className={`group p-6 rounded-xl border-2 text-center transition-all hover:shadow-md ${
                    sourceType === "manual"
                      ? "border-purple-500 bg-gradient-to-br from-purple-50 to-violet-50 dark:from-purple-950/30 dark:to-violet-950/30 shadow-md"
                      : "border-muted hover:border-purple-300 dark:hover:border-purple-700"
                  }`}
                >
                  <div className={`inline-flex p-3 rounded-xl mb-3 transition-all ${
                    sourceType === "manual"
                      ? "bg-gradient-to-br from-purple-500 to-violet-600 text-white shadow-md"
                      : "bg-muted group-hover:bg-purple-100 dark:group-hover:bg-purple-900/30"
                  }`}>
                    <Users className={`w-8 h-8 ${sourceType === "manual" ? "text-white" : "text-muted-foreground group-hover:text-purple-600"}`} />
                  </div>
                  <div className={`font-semibold text-lg ${sourceType === "manual" ? "text-purple-700 dark:text-purple-300" : ""}`}>
                    Add Manually
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">
                    Enter your team structure and link existing GPTs
                  </div>
                </button>
              </div>

              {/* Website Discovery */}
              {sourceType === "website" && (
                <div className="space-y-4">
                  <div className="flex gap-3">
                    <Input
                      placeholder="e.g., yourcompany.com or clevelandohio.gov"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && startDiscovery()}
                      className="flex-1 h-12 text-lg"
                    />
                    <Button
                      onClick={startDiscovery}
                      disabled={isLoading || !url.trim()}
                      className="h-12 px-6 bg-gradient-to-r from-purple-500 to-violet-600 hover:from-purple-600 hover:to-violet-700"
                    >
                      {isLoading ? (
                        <Loader2 className="w-5 h-5 animate-spin mr-2" />
                      ) : (
                        <Search className="w-5 h-5 mr-2" />
                      )}
                      Discover
                    </Button>
                  </div>

                  <div className="p-5 bg-gradient-to-br from-muted/50 to-muted rounded-xl border">
                    <h4 className="font-semibold mb-3 flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-purple-500" />
                      What we'll discover:
                    </h4>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <div className="p-1.5 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                          <User className="w-4 h-4 text-blue-600" />
                        </div>
                        Executives and leadership
                      </div>
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <div className="p-1.5 rounded-lg bg-green-100 dark:bg-green-900/30">
                          <Building2 className="w-4 h-4 text-green-600" />
                        </div>
                        Departments and teams
                      </div>
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <div className="p-1.5 rounded-lg bg-amber-100 dark:bg-amber-900/30">
                          <Database className="w-4 h-4 text-amber-600" />
                        </div>
                        Data sources and portals
                      </div>
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <div className="p-1.5 rounded-lg bg-rose-100 dark:bg-rose-900/30">
                          <FileText className="w-4 h-4 text-rose-600" />
                        </div>
                        Policies and documentation
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Manual Entry */}
              {sourceType === "manual" && (
                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium">Organization Name</label>
                    <Input
                      placeholder="Your Company Name"
                      value={orgName}
                      onChange={(e) => setOrgName(e.target.value)}
                      className="mt-1 h-12 text-lg"
                    />
                  </div>

                  <Button
                    onClick={() => {
                      if (orgName.trim()) {
                        addManualAgent();
                        setStep("select");
                      }
                    }}
                    disabled={!orgName.trim()}
                    className="bg-gradient-to-r from-purple-500 to-violet-600 hover:from-purple-600 hover:to-violet-700"
                  >
                    Continue to Add Agents
                    <ChevronRight className="w-4 h-4 ml-2" />
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="flex justify-between">
            <Button variant="outline" onClick={goBack}>
              <ChevronLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
          </div>
        </div>
      )}

      {/* Step 4: Discovering */}
      {step === "discovering" && discovery && (
        <Card className="border-0 shadow-lg overflow-hidden">
          <div className="bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/20 backdrop-blur-sm">
                  <Loader2 className="w-7 h-7 text-white animate-spin" />
                </div>
                <div className="text-white">
                  <h2 className="text-xl font-bold">Discovering...</h2>
                  <p className="text-white/80 text-sm">Scanning {discovery.source_url}</p>
                </div>
              </div>
              <Button
                variant="ghost"
                onClick={cancelDiscovery}
                className="text-white/80 hover:text-white hover:bg-white/20"
              >
                <XCircle className="w-4 h-4 mr-2" />
                Cancel
              </Button>
            </div>
          </div>
          <CardContent className="p-6">
            <div className="space-y-6">
              <div className="flex items-center gap-3 p-4 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800">
                <div className="w-3 h-3 rounded-full bg-amber-500 animate-pulse" />
                <span className="capitalize font-medium text-amber-700 dark:text-amber-300">{discovery.status}</span>
                <span className="text-sm text-amber-600 dark:text-amber-400 ml-auto">
                  {discovery.pages_crawled} pages scanned
                </span>
              </div>

              {/* Better progress indicators */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-gradient-to-br from-purple-50 to-violet-50 dark:from-purple-950/30 dark:to-violet-950/30 border border-purple-100 dark:border-purple-800 text-center">
                  <div className="text-3xl font-bold text-purple-700 dark:text-purple-300">
                    {discovery.progress?.departments_detected || discovery.departments.length}
                  </div>
                  <div className="text-xs text-purple-600 dark:text-purple-400 font-medium mt-1">Departments</div>
                </div>
                <div className="p-4 rounded-xl bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 border border-blue-100 dark:border-blue-800 text-center">
                  <div className="text-3xl font-bold text-blue-700 dark:text-blue-300">
                    {discovery.progress?.leaders_detected || (discovery.chief_officers.length + (discovery.executive ? 1 : 0))}
                  </div>
                  <div className="text-xs text-blue-600 dark:text-blue-400 font-medium mt-1">Leaders</div>
                </div>
                <div className="p-4 rounded-xl bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-950/30 dark:to-emerald-950/30 border border-green-100 dark:border-green-800 text-center">
                  <div className="text-3xl font-bold text-green-700 dark:text-green-300">
                    {discovery.progress?.services_detected || 0}
                  </div>
                  <div className="text-xs text-green-600 dark:text-green-400 font-medium mt-1">Services</div>
                </div>
                <div className="p-4 rounded-xl bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-950/30 dark:to-orange-950/30 border border-amber-100 dark:border-amber-800 text-center">
                  <div className="text-3xl font-bold text-amber-700 dark:text-amber-300">
                    {discovery.progress?.data_portals_detected || discovery.data_portals.length}
                  </div>
                  <div className="text-xs text-amber-600 dark:text-amber-400 font-medium mt-1">Data Portals</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 4.5: Candidate Selection - Using CandidateAgentsPanel */}
      {step === "candidates" && (
        <div className="space-y-6">
          <CandidateAgentsPanel
            candidates={convertToCandidateAgents(candidates)}
            onSelectionChange={handleCandidateSelectionChange}
            onCreateAgents={handleCreateAgentsFromPanel}
            isLoading={false}
            isCreating={isLoading}
            orgName={discovery?.municipality?.name || orgName}
          />

          {/* Back button */}
          <div className="flex justify-start">
            <Button variant="outline" onClick={() => setStep("start")}>
              <ChevronLeft className="w-4 h-4 mr-2" />
              Start Over
            </Button>
          </div>
        </div>
      )}

      {/* Step 5: Select Agents */}
      {step === "select" && (
        <div className="space-y-6">
          <Card className="border-0 shadow-lg">
            <CardHeader className="border-b bg-muted/30">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Users className="h-5 w-5 text-muted-foreground" />
                    Select Agents to Create
                  </CardTitle>
                  <CardDescription>
                    {discovery
                      ? `Found ${selectedAgents.length} potential agents from ${discovery.source_url}`
                      : `Configure agents for ${orgName}`}
                  </CardDescription>
                </div>
                <Button onClick={addManualAgent} className="bg-gradient-to-r from-purple-500 to-violet-600 hover:from-purple-600 hover:to-violet-700">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Agent
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-6">
              <ScrollArea className="h-[400px] pr-4">
                <div className="space-y-3">
                  {selectedAgents.map((agent, index) => (
                    <div
                      key={agent.id}
                      className={`p-4 rounded-xl border-2 transition-all animate-in fade-in ${
                        agent.enabled
                          ? "bg-gradient-to-r from-green-50/50 to-emerald-50/50 dark:from-green-950/20 dark:to-emerald-950/20 border-green-300 dark:border-green-700"
                          : "bg-muted/30 border-transparent opacity-60"
                      }`}
                      style={{ animationDelay: `${index * 50}ms` }}
                    >
                      <div className="flex items-start gap-4">
                        <Switch
                          checked={agent.enabled}
                          onCheckedChange={() => toggleAgent(agent.id)}
                          className="mt-1"
                        />
                        <div className="flex-1 space-y-3">
                          <div className="flex items-center gap-2">
                            {agent.isExecutive && (
                              <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border-0">
                                Executive
                              </Badge>
                            )}
                            <Input
                              placeholder="Agent Name"
                              value={agent.name}
                              onChange={(e) => updateAgent(agent.id, { name: e.target.value })}
                              className="font-medium"
                            />
                          </div>
                          <div className="flex gap-2">
                            <Input
                              placeholder="Title/Role"
                              value={agent.title}
                              onChange={(e) => updateAgent(agent.id, { title: e.target.value })}
                              className="flex-1"
                            />
                            <Select
                              value={agent.template_id || ""}
                              onValueChange={(v) => updateAgent(agent.id, { template_id: v })}
                            >
                              <SelectTrigger className="w-40">
                                <SelectValue placeholder="Template" />
                              </SelectTrigger>
                              <SelectContent>
                                {(orgType?.templates || ["general"]).map((t) => (
                                  <SelectItem key={t} value={t}>
                                    {t.replace(/-/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          {agent.director_name && agent.director_name !== agent.name && (
                            <div className="text-sm text-muted-foreground flex items-center gap-1">
                              <User className="w-3 h-3" />
                              Led by: {agent.director_name}
                            </div>
                          )}
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => removeAgent(agent.id)}
                          className="text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}

                  {selectedAgents.length === 0 && (
                    <div className="text-center py-12">
                      <div className="inline-flex p-4 rounded-full bg-muted mb-4">
                        <Users className="w-8 h-8 text-muted-foreground" />
                      </div>
                      <p className="font-medium">No agents yet</p>
                      <p className="text-sm text-muted-foreground">Click "Add Agent" to get started.</p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          <div className="flex justify-between">
            <Button variant="outline" onClick={goBack}>
              <ChevronLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            <Button
              onClick={() => setStep("link-gpts")}
              disabled={selectedAgents.filter((a) => a.enabled).length === 0}
              className="bg-gradient-to-r from-purple-500 to-violet-600 hover:from-purple-600 hover:to-violet-700"
            >
              Continue
              <ChevronRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </div>
      )}

      {/* Step 6: Link GPTs */}
      {step === "link-gpts" && (
        <div className="space-y-6">
          <Card className="border-0 shadow-lg">
            <CardHeader className="border-b bg-muted/30">
              <CardTitle className="flex items-center gap-2">
                <Link2 className="h-5 w-5 text-muted-foreground" />
                Link Custom GPTs
              </CardTitle>
              <CardDescription>
                Connect your existing OpenAI Custom GPTs to each agent (optional)
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              {/* Bulk Import */}
              <div className="p-5 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 rounded-xl border border-blue-100 dark:border-blue-800">
                <h4 className="font-semibold mb-2 flex items-center gap-2">
                  <Upload className="w-4 h-4 text-blue-600" />
                  Bulk Import GPT URLs
                </h4>
                <p className="text-sm text-muted-foreground mb-3">
                  Paste one GPT URL per line. They'll be matched to agents in order.
                </p>
                <Textarea
                  placeholder="https://chatgpt.com/g/g-xxx-agent-1&#10;https://chatgpt.com/g/g-xxx-agent-2&#10;..."
                  value={bulkGptUrls}
                  onChange={(e) => setBulkGptUrls(e.target.value)}
                  rows={4}
                  className="bg-white dark:bg-background"
                />
                <Button
                  variant="secondary"
                  size="sm"
                  className="mt-3"
                  onClick={parseBulkGptUrls}
                  disabled={!bulkGptUrls.trim()}
                >
                  <Sparkles className="w-4 h-4 mr-2" />
                  Apply URLs
                </Button>
              </div>

              {/* Individual Agent Links */}
              <div>
                <h4 className="font-semibold mb-3">Link Individually</h4>
                <ScrollArea className="h-[280px] pr-4">
                  <div className="space-y-3">
                    {selectedAgents
                      .filter((a) => a.enabled)
                      .map((agent, index) => (
                        <div
                          key={agent.id}
                          className="flex items-center gap-3 p-3 rounded-lg border bg-card hover:shadow-sm transition-shadow animate-in fade-in"
                          style={{ animationDelay: `${index * 30}ms` }}
                        >
                          <div className="w-48 truncate font-medium text-sm">{agent.name || "Unnamed"}</div>
                          <Input
                            placeholder="https://chatgpt.com/g/..."
                            value={agent.gpt_url}
                            onChange={(e) => updateAgent(agent.id, { gpt_url: e.target.value })}
                            className="flex-1"
                          />
                          {agent.gpt_url && (
                            <a
                              href={agent.gpt_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-2 rounded-lg text-muted-foreground hover:text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-950/30 transition-colors"
                            >
                              <ExternalLink className="w-4 h-4" />
                            </a>
                          )}
                        </div>
                      ))}
                  </div>
                </ScrollArea>
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-between">
            <Button variant="outline" onClick={goBack}>
              <ChevronLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            <Button
              onClick={() => setStep("review")}
              className="bg-gradient-to-r from-purple-500 to-violet-600 hover:from-purple-600 hover:to-violet-700"
            >
              Continue to Review
              <ChevronRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </div>
      )}

      {/* Step 7: Review */}
      {step === "review" && (
        <div className="space-y-6">
          <Card className="border-0 shadow-lg">
            <CardHeader className="border-b bg-muted/30">
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-500" />
                Review Configuration
              </CardTitle>
              <CardDescription>
                Review your setup before deploying
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="p-5 rounded-xl bg-gradient-to-br from-purple-50 to-violet-50 dark:from-purple-950/30 dark:to-violet-950/30 border border-purple-100 dark:border-purple-800 text-center">
                  <div className="text-4xl font-bold text-purple-700 dark:text-purple-300">{selectedAgents.filter((a) => a.enabled).length}</div>
                  <div className="text-sm text-purple-600 dark:text-purple-400 font-medium">Agents</div>
                </div>
                <div className="p-5 rounded-xl bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 border border-blue-100 dark:border-blue-800 text-center">
                  <div className="text-4xl font-bold text-blue-700 dark:text-blue-300">
                    {selectedAgents.filter((a) => a.enabled && a.gpt_url).length}
                  </div>
                  <div className="text-sm text-blue-600 dark:text-blue-400 font-medium">GPTs Linked</div>
                </div>
                <div className="p-5 rounded-xl bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-950/30 dark:to-orange-950/30 border border-amber-100 dark:border-amber-800 text-center">
                  <div className="text-4xl font-bold text-amber-700 dark:text-amber-300">{industry?.compliance.length || 0}</div>
                  <div className="text-sm text-amber-600 dark:text-amber-400 font-medium">Compliance Rules</div>
                </div>
              </div>

              {/* Organization Info */}
              <div className="p-5 bg-gradient-to-br from-muted/50 to-muted rounded-xl border">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-muted-foreground" />
                    <span className="text-muted-foreground">Organization:</span>
                    <span className="font-medium">{orgName || "Not specified"}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Landmark className="w-4 h-4 text-muted-foreground" />
                    <span className="text-muted-foreground">Type:</span>
                    <span className="font-medium">{orgType?.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Briefcase className="w-4 h-4 text-muted-foreground" />
                    <span className="text-muted-foreground">Industry:</span>
                    <span className="font-medium">{industry?.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-muted-foreground" />
                    <span className="text-muted-foreground">Compliance:</span>
                    <span className="font-medium">
                      {industry?.compliance.join(", ").toUpperCase() || "None"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Agent List */}
              <div>
                <h4 className="font-semibold mb-3 flex items-center gap-2">
                  <Users className="w-4 h-4 text-muted-foreground" />
                  Agents to be created:
                </h4>
                <div className="grid grid-cols-2 gap-2">
                  {selectedAgents
                    .filter((a) => a.enabled)
                    .map((agent, index) => (
                      <div
                        key={agent.id}
                        className="flex items-center gap-2 text-sm p-3 rounded-lg bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-800 animate-in fade-in"
                        style={{ animationDelay: `${index * 30}ms` }}
                      >
                        <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0" />
                        <span className="truncate font-medium">{agent.name || "Unnamed Agent"}</span>
                        {agent.gpt_url && (
                          <Link2 className="w-3 h-3 text-purple-500 flex-shrink-0 ml-auto" />
                        )}
                      </div>
                    ))}
                </div>
              </div>

              {/* Compliance Notice */}
              {industry && industry.compliance.length > 0 && (
                <div className="p-5 bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-950/30 dark:to-orange-950/30 rounded-xl border border-amber-200 dark:border-amber-800">
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-amber-100 dark:bg-amber-900/50">
                      <Shield className="w-5 h-5 text-amber-600" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-amber-800 dark:text-amber-200">
                        Compliance Guardrails Applied
                      </h4>
                      <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                        All agents will include {industry.compliance.join(" and ").toUpperCase()} compliance guardrails.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="flex justify-between">
            <Button variant="outline" onClick={goBack}>
              <ChevronLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            <Button
              onClick={deployAgents}
              disabled={isDeploying}
              className="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700"
            >
              {isDeploying ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <Rocket className="w-4 h-4 mr-2" />
              )}
              Submit for Approval
            </Button>
          </div>
        </div>
      )}

      {/* Step 8: Deploy Complete */}
      {step === "deploy" && (
        <Card className="border-0 shadow-lg overflow-hidden">
          <div className="bg-gradient-to-r from-green-500 via-emerald-500 to-teal-500 p-8">
            <div className="flex items-center justify-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/20 backdrop-blur-sm">
                <CheckCircle2 className="w-10 h-10 text-white" />
              </div>
              <div className="text-white">
                <h2 className="text-2xl font-bold">Submission Complete!</h2>
                <p className="text-white/80">{deployStatus}</p>
              </div>
            </div>
          </div>
          <CardContent className="p-8">
            <div className="space-y-6">
              <div className="p-5 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 rounded-xl border border-blue-200 dark:border-blue-800">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/50">
                    <AlertCircle className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-blue-800 dark:text-blue-200">Next Steps</h4>
                    <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                      Your agents have been submitted for approval. Visit the Approvals page to review and approve them before they become active.
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex gap-3 justify-center">
                <Button variant="outline" onClick={resetWizard} size="lg">
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Onboard Another
                </Button>
                <Button asChild size="lg" className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600">
                  <a href="/approvals">
                    <CheckCircle2 className="w-4 h-4 mr-2" />
                    Review Approvals
                  </a>
                </Button>
                <Button asChild variant="outline" size="lg">
                  <a href="/agents">View All Agents</a>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
