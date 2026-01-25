/**
 * API client for AIOS backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

/**
 * Generic fetch wrapper with error handling
 */
async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  return res.json();
}

// =============================================================================
// Types
// =============================================================================

export interface AgentConfig {
  id: string;
  name: string;
  title: string;
  domain: string;
  description: string;
  capabilities: string[];
  guardrails: string[];
  escalates_to: string;
  gpt_url: string;
  system_prompt: string;
  status: "active" | "inactive" | "degraded";
  is_router: boolean;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeDocument {
  id: string;
  agent_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  uploaded_at: string;
  metadata: Record<string, unknown>;
}

export interface AgentQueryResponse {
  response: string;
  agent_id: string;
  agent_name: string;
  sources: Array<{
    text: string;
    metadata: Record<string, unknown>;
    relevance: number;
  }>;
  hitl_mode: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  policies_loaded: boolean;
  llm_available: boolean;
  llm_provider: string;
}

// =============================================================================
// Health
// =============================================================================

export async function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

// =============================================================================
// Agents
// =============================================================================

export async function listAgents(): Promise<{ agents: AgentConfig[]; total: number }> {
  return apiFetch("/agents");
}

export async function getAgent(agentId: string): Promise<AgentConfig> {
  return apiFetch(`/agents/${agentId}`);
}

export async function updateAgent(
  agentId: string,
  updates: Partial<AgentConfig>
): Promise<AgentConfig> {
  return apiFetch(`/agents/${agentId}`, {
    method: "PUT",
    body: JSON.stringify(updates),
  });
}

export async function enableAgent(agentId: string): Promise<AgentConfig> {
  return apiFetch(`/agents/${agentId}/enable`, { method: "POST" });
}

export async function disableAgent(agentId: string): Promise<AgentConfig> {
  return apiFetch(`/agents/${agentId}/disable`, { method: "POST" });
}

export async function deleteAgent(agentId: string): Promise<void> {
  await apiFetch(`/agents/${agentId}`, { method: "DELETE" });
}

export interface CreateAgentRequest {
  id: string;
  name: string;
  title?: string;
  domain?: string;
  description?: string;
  capabilities?: string[];
  guardrails?: string[];
  escalates_to?: string;
  system_prompt?: string;
  gpt_url?: string;
  is_router?: boolean;
}

export async function createAgent(agent: CreateAgentRequest): Promise<AgentConfig> {
  return apiFetch("/agents", {
    method: "POST",
    body: JSON.stringify(agent),
  });
}

// =============================================================================
// Knowledge Base
// =============================================================================

export async function listKnowledge(agentId: string): Promise<KnowledgeDocument[]> {
  return apiFetch(`/agents/${agentId}/knowledge`);
}

export async function uploadKnowledge(
  agentId: string,
  file: File
): Promise<KnowledgeDocument> {
  const formData = new FormData();
  formData.append("file", file);

  const url = `${API_BASE}/agents/${agentId}/knowledge`;
  const res = await fetch(url, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Upload failed: ${res.status}`);
  }

  return res.json();
}

export async function deleteKnowledge(
  agentId: string,
  documentId: string
): Promise<void> {
  await apiFetch(`/agents/${agentId}/knowledge/${documentId}`, {
    method: "DELETE",
  });
}

export async function clearKnowledge(agentId: string): Promise<void> {
  await apiFetch(`/agents/${agentId}/knowledge`, { method: "DELETE" });
}

// =============================================================================
// Agent Query
// =============================================================================

export async function queryAgent(
  agentId: string,
  query: string,
  useKnowledgeBase: boolean = true
): Promise<AgentQueryResponse> {
  return apiFetch(`/agents/${agentId}/query`, {
    method: "POST",
    body: JSON.stringify({
      query,
      use_knowledge_base: useKnowledgeBase,
    }),
  });
}

// =============================================================================
// Governance (Ask endpoint)
// =============================================================================

export interface AskRequest {
  text: string;
  tenant_id: string;
  user_id?: string;
  role?: string;
  department?: string;
  use_llm_classification?: boolean;
}

export interface AskResponse {
  response: string;
  intent: {
    domain: string;
    task: string;
    audience: string;
    impact: string;
    confidence: number;
  };
  risk_signals: string[];
  hitl_mode: string;
  requires_approval: boolean;
  model_used: string;
  governance_triggers: string[];
}

export async function askAssistant(request: AskRequest): Promise<AskResponse> {
  return apiFetch("/ask", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

// =============================================================================
// System Management
// =============================================================================

export interface ClientSetupRequest {
  client_name: string;
  organization: string;
  description?: string;
}

export async function resetForNewClient(setup: ClientSetupRequest): Promise<{ message: string; concierge: AgentConfig }> {
  return apiFetch("/system/reset", {
    method: "POST",
    body: JSON.stringify(setup),
  });
}

export async function regenerateConcierge(): Promise<AgentConfig> {
  return apiFetch("/system/regenerate-concierge", {
    method: "POST",
  });
}
