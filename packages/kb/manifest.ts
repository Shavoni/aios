/**
 * HAAIS Agent Manifest Schema
 */

export type Sensitivity = "public" | "internal" | "confidential" | "restricted" | "privileged";

export interface ActionProfile {
  can_draft: boolean;
  can_submit: boolean;
  can_query_external: boolean;
  can_schedule: boolean;
}

export interface AgentDefinition {
  agent_id: string;
  display_name: string;
  department_id: string;
  gpt_name_in_openai: string;
  public_description: string;
  instruction_kernel: string;
  default_max_sensitivity: Sensitivity;
  include_citywide: boolean;
  allowed_scopes: string[];
  knowledge_profile: string[];
  action_profile: ActionProfile;
}

export interface AgentManifest {
  schema_version: string;
  manifest_id: string;
  created_at: string;
  agents: AgentDefinition[];
  sensitivity_levels: Sensitivity[];
  citywide_knowledge_base: string[];
}

export const SENSITIVITY_ORDER: Sensitivity[] = [
  "public", "internal", "confidential", "restricted", "privileged"
];

export function getEffectiveSensitivity(
  requested: Sensitivity | undefined,
  ceiling: Sensitivity
): Sensitivity {
  const requestedLevel = SENSITIVITY_ORDER.indexOf(requested ?? "internal");
  const ceilingLevel = SENSITIVITY_ORDER.indexOf(ceiling);
  return SENSITIVITY_ORDER[Math.min(
    requestedLevel >= 0 ? requestedLevel : 1,
    ceilingLevel >= 0 ? ceilingLevel : 1
  )];
}

export interface APIKeyConfig {
  agent: AgentDefinition;
  enabled: boolean;
}

class AgentRegistry {
  private manifest: AgentManifest | null = null;
  private keyToAgent: Map<string, APIKeyConfig> = new Map();
  private agentById: Map<string, AgentDefinition> = new Map();

  loadManifest(manifest: AgentManifest): void {
    this.manifest = manifest;
    this.agentById.clear();
    for (const agent of manifest.agents) {
      this.agentById.set(agent.agent_id, agent);
    }
    console.log(`Loaded manifest: ${manifest.manifest_id} with ${manifest.agents.length} agents`);
  }

  registerKey(apiKey: string, agentId: string, enabled = true): boolean {
    const agent = this.agentById.get(agentId);
    if (!agent) return false;
    this.keyToAgent.set(apiKey, { agent, enabled });
    return true;
  }

  validateKey(authHeader: string | undefined): APIKeyConfig | null {
    if (!authHeader?.startsWith("Bearer ")) return null;
    const token = authHeader.slice(7);
    const config = this.keyToAgent.get(token);
    return config?.enabled ? config : null;
  }

  getAgent(agentId: string): AgentDefinition | undefined {
    return this.agentById.get(agentId);
  }

  getAllAgents(): AgentDefinition[] {
    return Array.from(this.agentById.values());
  }

  getManifest(): AgentManifest | null {
    return this.manifest;
  }

  getCitywideKnowledge(): string[] {
    return this.manifest?.citywide_knowledge_base ?? [];
  }

  getAccessibleKnowledge(agentId: string): string[] {
    const agent = this.agentById.get(agentId);
    if (!agent) return [];
    const profiles = [...agent.knowledge_profile];
    if (agent.include_citywide && this.manifest) {
      profiles.push(...this.manifest.citywide_knowledge_base);
    }
    return [...new Set(profiles)];
  }
}

export const agentRegistry = new AgentRegistry();

export const CLEVELAND_MANIFEST: AgentManifest = {
  schema_version: "1.0.0",
  manifest_id: "cleveland-municipal-agents-v1",
  created_at: new Date().toISOString(),
  agents: [
    {
      agent_id: "cle-public-safety-001",
      display_name: "Public Safety Assistant",
      department_id: "dept-public-safety",
      gpt_name_in_openai: "Cleveland Public Safety GPT",
      public_description: "Assists Cleveland Division of Police and Fire with policy lookup and incident report drafting.",
      instruction_kernel: "You are a public safety assistant for Cleveland. Prioritize officer and citizen safety. Never disclose sensitive operational details.",
      default_max_sensitivity: "confidential",
      include_citywide: true,
      allowed_scopes: ["policy_read", "report_draft", "training_access", "scheduling_read"],
      knowledge_profile: ["orc_criminal", "use_of_force_policy", "cle_fire_sops", "mutual_aid_agreements"],
      action_profile: { can_draft: true, can_submit: false, can_query_external: false, can_schedule: true },
    },
    {
      agent_id: "cle-public-works-002",
      display_name: "Public Works Assistant",
      department_id: "dept-public-works",
      gpt_name_in_openai: "Cleveland Public Works GPT",
      public_description: "Supports streets, utilities, and infrastructure teams.",
      instruction_kernel: "You assist Public Works staff with infrastructure operations. Reference GIS asset data when available.",
      default_max_sensitivity: "internal",
      include_citywide: true,
      allowed_scopes: ["asset_read", "workorder_draft", "vendor_lookup", "gis_query", "scheduling_write"],
      knowledge_profile: ["infrastructure_standards", "odot_specs", "seasonal_ops", "fleet_maintenance"],
      action_profile: { can_draft: true, can_submit: true, can_query_external: true, can_schedule: true },
    },
    {
      agent_id: "cle-hr-003",
      display_name: "Human Resources Assistant",
      department_id: "dept-human-resources",
      gpt_name_in_openai: "Cleveland HR GPT",
      public_description: "Provides HR policy guidance and labor agreement interpretation.",
      instruction_kernel: "You are an HR assistant for Cleveland. Protect employee privacy absolutely. Reference collective bargaining agreements accurately.",
      default_max_sensitivity: "restricted",
      include_citywide: true,
      allowed_scopes: ["policy_read", "benefits_lookup", "cba_interpret", "onboarding_guide"],
      knowledge_profile: ["afscme_cba", "fop_cba", "iaff_cba", "fmla_ada", "civil_service_rules"],
      action_profile: { can_draft: true, can_submit: false, can_query_external: false, can_schedule: false },
    },
    {
      agent_id: "cle-finance-004",
      display_name: "Finance & Budget Assistant",
      department_id: "dept-finance",
      gpt_name_in_openai: "Cleveland Finance GPT",
      public_description: "Assists with budget tracking and procurement guidance.",
      instruction_kernel: "You support Finance department operations. Ensure accuracy in all financial figures. Reference Ohio Auditor standards.",
      default_max_sensitivity: "confidential",
      include_citywide: true,
      allowed_scopes: ["budget_read", "expenditure_query", "grant_lookup", "procurement_guide", "report_generate"],
      knowledge_profile: ["gaap_municipal", "ohio_auditor_standards", "federal_grant_compliance", "procurement_code"],
      action_profile: { can_draft: true, can_submit: false, can_query_external: true, can_schedule: false },
    },
    {
      agent_id: "cle-community-dev-005",
      display_name: "Community Development Assistant",
      department_id: "dept-community-development",
      gpt_name_in_openai: "Cleveland Community Dev GPT",
      public_description: "Supports housing programs and neighborhood initiatives.",
      instruction_kernel: "You assist Community Development with housing and neighborhood programs. Reference HUD guidelines and Cleveland zoning code.",
      default_max_sensitivity: "internal",
      include_citywide: true,
      allowed_scopes: ["zoning_lookup", "hud_compliance", "permit_status", "neighborhood_data", "grant_tracking"],
      knowledge_profile: ["hud_cdbg", "housing_rehab", "cle_zoning_code", "land_bank_procedures"],
      action_profile: { can_draft: true, can_submit: true, can_query_external: true, can_schedule: true },
    },
    {
      agent_id: "cle-public-health-006",
      display_name: "Public Health Assistant",
      department_id: "dept-public-health",
      gpt_name_in_openai: "Cleveland Public Health GPT",
      public_description: "Supports public health program guidance and inspection protocols.",
      instruction_kernel: "You assist Public Health staff. Adhere strictly to HIPAA. Reference CDC and ODH guidelines.",
      default_max_sensitivity: "restricted",
      include_citywide: false,
      allowed_scopes: ["protocol_read", "epi_data_query", "inspection_guide", "program_lookup", "outreach_draft"],
      knowledge_profile: ["cdc_guidelines", "odh_regulations", "hipaa_compliance", "food_safety_code", "lead_safe_protocols"],
      action_profile: { can_draft: true, can_submit: false, can_query_external: true, can_schedule: true },
    },
    {
      agent_id: "cle-law-007",
      display_name: "Law Department Assistant",
      department_id: "dept-law",
      gpt_name_in_openai: "Cleveland Law GPT",
      public_description: "Assists city attorneys with legal research and ordinance drafting.",
      instruction_kernel: "You support the Law Department with legal research and drafting. Maintain attorney-client privilege. Cite sources precisely.",
      default_max_sensitivity: "privileged",
      include_citywide: false,
      allowed_scopes: ["legal_research", "ordinance_draft", "contract_review", "litigation_support", "orc_query"],
      knowledge_profile: ["orc_full", "cle_codified_ordinances", "case_law_ohio", "municipal_liability", "public_records_law"],
      action_profile: { can_draft: true, can_submit: false, can_query_external: true, can_schedule: false },
    },
    {
      agent_id: "cle-it-008",
      display_name: "IT Services Assistant",
      department_id: "dept-information-technology",
      gpt_name_in_openai: "Cleveland IT GPT",
      public_description: "Supports city IT staff with helpdesk triage and security policy guidance.",
      instruction_kernel: "You assist IT Services staff. Never expose credentials or system vulnerabilities. Reference NIST and Ohio IT security standards.",
      default_max_sensitivity: "confidential",
      include_citywide: true,
      allowed_scopes: ["helpdesk_triage", "docs_lookup", "security_policy", "project_tracking", "vendor_lookup"],
      knowledge_profile: ["nist_csf", "ohio_it_standards", "microsoft_365_admin", "network_architecture", "incident_response"],
      action_profile: { can_draft: true, can_submit: true, can_query_external: false, can_schedule: true },
    },
  ],
  sensitivity_levels: ["public", "internal", "confidential", "restricted", "privileged"],
  citywide_knowledge_base: ["cle_employee_handbook", "ethics_policy", "public_records_guide", "ada_compliance"],
};
