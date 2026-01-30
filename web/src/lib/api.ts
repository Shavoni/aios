/**
 * API client for AIOS backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  hitl_mode?: string;
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

export function getKnowledgeDownloadUrl(agentId: string, documentId: string): string {
  return `${API_BASE}/agents/${agentId}/knowledge/${documentId}/download`;
}

export async function clearKnowledge(agentId: string): Promise<void> {
  await apiFetch(`/agents/${agentId}/knowledge`, { method: "DELETE" });
}

// =============================================================================
// Web Sources (URL-based Knowledge)
// =============================================================================

export interface WebSource {
  id: string;
  agent_id: string;
  url: string;
  name: string;
  description: string;
  refresh_interval_hours: number;
  last_refreshed: string | null;
  last_refresh_status: string;
  chunk_count: number;
  created_at: string;
  metadata: Record<string, unknown>;
  auto_refresh: boolean;
  selector: string | null;
}

export interface WebSourceCreateRequest {
  url: string;
  name?: string;
  description?: string;
  refresh_interval_hours?: number;
  selector?: string;
  auto_refresh?: boolean;
}

export async function listWebSources(agentId: string): Promise<{ sources: WebSource[]; total: number }> {
  return apiFetch(`/agents/${agentId}/web-sources`);
}

export async function addWebSource(
  agentId: string,
  source: WebSourceCreateRequest
): Promise<WebSource> {
  return apiFetch(`/agents/${agentId}/web-sources`, {
    method: "POST",
    body: JSON.stringify(source),
  });
}

export async function refreshWebSource(agentId: string, sourceId: string): Promise<WebSource> {
  return apiFetch(`/agents/${agentId}/web-sources/${sourceId}/refresh`, {
    method: "POST",
  });
}

export async function deleteWebSource(agentId: string, sourceId: string): Promise<void> {
  await apiFetch(`/agents/${agentId}/web-sources/${sourceId}`, {
    method: "DELETE",
  });
}

export async function listAllWebSources(): Promise<{ sources: WebSource[]; total: number }> {
  return apiFetch("/agents/web-sources/all");
}

export async function refreshAllWebSources(): Promise<{ refreshed: number; results: Record<string, string> }> {
  return apiFetch("/agents/web-sources/refresh-all", { method: "POST" });
}

// =============================================================================
// Intelligent Routing
// =============================================================================

export interface RoutingRequest {
  query: string;
  consider_only_active?: boolean;
}

export interface RoutingResponse {
  primary_agent_id: string;
  primary_domain: string;
  confidence: number;
  alternative_agents: string[];
  requires_clarification: boolean;
  clarification_prompt: string | null;
}

export async function routeQuery(query: string, considerOnlyActive: boolean = true): Promise<RoutingResponse> {
  return apiFetch("/agents/route", {
    method: "POST",
    body: JSON.stringify({
      query,
      consider_only_active: considerOnlyActive,
    }),
  });
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

// =============================================================================
// Analytics
// =============================================================================

export interface AnalyticsSummary {
  total_queries: number;
  total_queries_30d: number;
  total_queries_7d: number;
  total_queries_today: number;
  unique_users_30d: number;
  unique_users_7d: number;
  unique_users_today: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  success_rate: number;
  escalation_rate: number;
  approval_rate: number;
  guardrails_enforced: number;
  total_cost_30d: number;
  total_cost_7d: number;
  avg_cost_per_query: number;
  estimated_savings: number;
  total_tokens_30d: number;
  avg_tokens_per_query: number;
  queries_by_agent: Record<string, number>;
  queries_by_department: Record<string, number>;
  daily_queries: Array<{ date: string; queries: number }>;
  hourly_distribution: Record<number, number>;
  top_agents: Array<{ agent_id: string; queries: number }>;
  top_departments: Array<{ department: string; queries: number }>;
  recent_errors: Array<{ timestamp: string; agent_id: string; error: string; query: string }>;
}

export async function getAnalyticsSummary(days: number = 30): Promise<AnalyticsSummary> {
  return apiFetch(`/analytics/summary?days=${days}`);
}

export async function getAgentAnalytics(agentId: string, days: number = 30): Promise<Record<string, unknown>> {
  return apiFetch(`/analytics/agents/${agentId}?days=${days}`);
}

// =============================================================================
// Sessions
// =============================================================================

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  agent_id?: string;
  agent_name?: string;
  metadata: Record<string, unknown>;
}

export interface Conversation {
  id: string;
  user_id: string;
  department: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
  current_agent_id?: string;
  context: Record<string, unknown>;
  is_active: boolean;
  title?: string;
}

export async function createConversation(userId: string = "anonymous", department: string = "General"): Promise<Conversation> {
  return apiFetch("/sessions/conversations", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, department }),
  });
}

export async function getConversation(convId: string): Promise<Conversation> {
  return apiFetch(`/sessions/conversations/${convId}`);
}

export async function listConversations(userId?: string, limit: number = 50): Promise<{ conversations: Conversation[]; total: number }> {
  const params = new URLSearchParams();
  if (userId) params.append("user_id", userId);
  params.append("limit", String(limit));
  return apiFetch(`/sessions/conversations?${params}`);
}

export async function addMessage(
  convId: string,
  role: "user" | "assistant",
  content: string,
  agentId?: string,
  agentName?: string
): Promise<Message> {
  return apiFetch(`/sessions/conversations/${convId}/messages`, {
    method: "POST",
    body: JSON.stringify({ role, content, agent_id: agentId, agent_name: agentName }),
  });
}

export async function getConversationContext(convId: string): Promise<{ context: string; message_count: number; current_agent_id?: string }> {
  return apiFetch(`/sessions/conversations/${convId}/context`);
}

// =============================================================================
// HITL (Human-in-the-Loop)
// =============================================================================

export interface ApprovalRequest {
  id: string;
  created_at: string;
  expires_at?: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "EXPIRED" | "CANCELLED";
  hitl_mode: "INFORM" | "DRAFT" | "EXECUTE" | "ESCALATE";
  user_id: string;
  user_department: string;
  agent_id: string;
  agent_name: string;
  original_query: string;
  proposed_response: string;
  context: Record<string, unknown>;
  risk_signals: string[];
  guardrails_triggered: string[];
  escalation_reason?: string;
  resolved_at?: string;
  resolved_by?: string;
  reviewer_notes?: string;
  modified_response?: string;
  assigned_to?: string;
  priority: "low" | "normal" | "high" | "urgent";
}

export interface ApprovalQueue {
  pending_count: number;
  pending_by_mode: Record<string, number>;
  pending_by_agent: Record<string, number>;
  pending_by_priority: Record<string, number>;
  oldest_pending?: string;
  avg_resolution_time_hrs?: number;
}

export async function getApprovalQueue(): Promise<ApprovalQueue> {
  return apiFetch("/hitl/queue/summary");
}

export async function listPendingApprovals(limit: number = 100): Promise<{ approvals: ApprovalRequest[]; total: number }> {
  return apiFetch(`/hitl/queue?limit=${limit}`);
}

export async function getApprovalRequest(requestId: string): Promise<ApprovalRequest> {
  return apiFetch(`/hitl/approvals/${requestId}`);
}

export async function approveRequest(
  requestId: string,
  reviewerId: string,
  notes?: string,
  modifiedResponse?: string
): Promise<ApprovalRequest> {
  return apiFetch(`/hitl/approvals/${requestId}/approve`, {
    method: "POST",
    body: JSON.stringify({
      reviewer_id: reviewerId,
      notes,
      modified_response: modifiedResponse,
    }),
  });
}

export async function rejectRequest(
  requestId: string,
  reviewerId: string,
  reason: string
): Promise<ApprovalRequest> {
  return apiFetch(`/hitl/approvals/${requestId}/reject`, {
    method: "POST",
    body: JSON.stringify({ reviewer_id: reviewerId, reason }),
  });
}

// =============================================================================
// Templates
// =============================================================================

export interface AgentTemplate {
  id: string;
  name: string;
  title: string;
  domain: string;
  description: string;
  capabilities: string[];
  guardrails: string[];
  system_prompt: string;
  escalates_to: string;
  category: string;
  tags: string[];
}

export async function listTemplates(category?: string): Promise<{ templates: AgentTemplate[]; total: number }> {
  const params = category ? `?category=${category}` : "";
  return apiFetch(`/templates${params}`);
}

export async function getTemplate(templateId: string): Promise<AgentTemplate> {
  return apiFetch(`/templates/${templateId}`);
}

export async function searchTemplates(query: string): Promise<{ templates: AgentTemplate[]; total: number }> {
  return apiFetch(`/templates/search?query=${encodeURIComponent(query)}`);
}

// =============================================================================
// Audit
// =============================================================================

export interface AuditEvent {
  id: string;
  timestamp: string;
  event_type: string;
  severity: "INFO" | "WARNING" | "ALERT" | "CRITICAL";
  user_id: string;
  user_department: string;
  agent_id?: string;
  agent_name?: string;
  action: string;
  details: Record<string, unknown>;
  pii_detected: string[];
  guardrails_triggered: string[];
  requires_review: boolean;
  reviewed_by?: string;
}

export interface AuditSummary {
  period_start: string;
  period_end: string;
  total_events: number;
  events_by_type: Record<string, number>;
  events_by_severity: Record<string, number>;
  events_by_user: Record<string, number>;
  events_by_agent: Record<string, number>;
  pii_detections: number;
  guardrail_triggers: number;
  escalations: number;
  pending_review: number;
}

export async function getAuditSummary(startDate?: string, endDate?: string): Promise<AuditSummary> {
  const params = new URLSearchParams();
  if (startDate) params.append("start_date", startDate);
  if (endDate) params.append("end_date", endDate);
  return apiFetch(`/audit/summary?${params}`);
}

export async function listAuditEvents(options: {
  startDate?: string;
  endDate?: string;
  eventType?: string;
  severity?: string;
  limit?: number;
}): Promise<{ events: AuditEvent[]; total: number }> {
  const params = new URLSearchParams();
  if (options.startDate) params.append("start_date", options.startDate);
  if (options.endDate) params.append("end_date", options.endDate);
  if (options.eventType) params.append("event_type", options.eventType);
  if (options.severity) params.append("severity", options.severity);
  params.append("limit", String(options.limit || 100));
  return apiFetch(`/audit/events?${params}`);
}

// =============================================================================
// Cache & Rate Limiting
// =============================================================================

export interface CacheStats {
  total_entries: number;
  total_hits: number;
  total_misses: number;
  hit_rate: number;
  memory_estimate_mb: number;
}

export async function getCacheStats(): Promise<CacheStats> {
  return apiFetch("/cache/stats");
}

export async function clearCache(cacheType?: "query" | "embedding" | "response"): Promise<{ cleared_count: number }> {
  const params = cacheType ? `?cache_type=${cacheType}` : "";
  return apiFetch(`/cache/clear${params}`, { method: "POST" });
}

export interface QuotaUsage {
  user_id?: string;
  department?: string;
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  limit_requests: number;
  limit_tokens: number;
  limit_cost: number;
  usage_percent_requests: number;
  usage_percent_tokens: number;
  usage_percent_cost: number;
}

export async function getUserUsage(userId: string): Promise<QuotaUsage> {
  return apiFetch(`/ratelimit/usage/${userId}`);
}

export async function getDepartmentUsage(department: string): Promise<QuotaUsage> {
  return apiFetch(`/ratelimit/usage/department/${department}`);
}

// =============================================================================
// Tenant Management
// =============================================================================

export interface Tenant {
  id: string;
  name: string;
  status: "active" | "suspended" | "pending" | "archived";
  tier: "free" | "starter" | "professional" | "enterprise" | "government";
  admin_email: string;
  admin_name: string;
  created_at: string;
  updated_at: string;
}

export interface TenantSettings {
  preferred_models: Record<string, string>;
  default_temperature: number;
  default_max_tokens: number;
  default_hitl_mode: "INFORM" | "DRAFT" | "EXECUTE" | "ESCALATE";
  require_approval_for_domains: string[];
  prohibited_topics: string[];
  welcome_message: string;
  escalation_email: string;
}

export interface ResourceQuota {
  daily_api_calls: number;
  monthly_api_calls: number;
  max_tokens_per_request: number;
  max_requests_per_minute: number;
  max_agents: number;
  max_active_agents: number;
  max_concurrent_queries: number;
  max_kb_documents: number;
  max_kb_size_mb: number;
  max_attachments_mb: number;
  daily_llm_budget_usd: number;
  monthly_llm_budget_usd: number;
}

export interface TenantUsage {
  tenant_id: string;
  date: string;
  api_calls_today: number;
  api_calls_this_month: number;
  tokens_used_today: number;
  tokens_used_this_month: number;
  llm_cost_today_usd: number;
  llm_cost_this_month_usd: number;
  queries_today: number;
  queries_this_month: number;
}

export interface QuotaStatus {
  quota: ResourceQuota;
  usage: Record<string, number>;
  remaining: Record<string, number>;
  percentage_used: Record<string, number>;
}

export interface CreateTenantRequest {
  name: string;
  tier?: string;
  admin_email?: string;
  admin_name?: string;
  metadata?: Record<string, unknown>;
}

export interface UpdateTenantRequest {
  name?: string;
  tier?: string;
  status?: string;
  admin_email?: string;
}

export async function listTenants(
  status?: string,
  tier?: string
): Promise<{ tenants: Tenant[]; total: number }> {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  if (tier) params.append("tier", tier);
  const query = params.toString() ? `?${params}` : "";
  return apiFetch(`/tenants${query}`);
}

export async function getTenant(tenantId: string): Promise<Tenant & { settings: TenantSettings; quota: ResourceQuota }> {
  return apiFetch(`/tenants/${tenantId}`);
}

export async function createTenant(data: CreateTenantRequest): Promise<Tenant> {
  return apiFetch("/tenants", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateTenant(tenantId: string, data: UpdateTenantRequest): Promise<Tenant> {
  return apiFetch(`/tenants/${tenantId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteTenant(tenantId: string): Promise<{ status: string; message: string }> {
  return apiFetch(`/tenants/${tenantId}`, { method: "DELETE" });
}

export async function getTenantSettings(tenantId: string): Promise<TenantSettings> {
  return apiFetch(`/tenants/${tenantId}/settings`);
}

export async function updateTenantSettings(
  tenantId: string,
  settings: Partial<TenantSettings>
): Promise<TenantSettings> {
  return apiFetch(`/tenants/${tenantId}/settings`, {
    method: "PUT",
    body: JSON.stringify(settings),
  });
}

export async function getTenantQuota(tenantId: string): Promise<ResourceQuota & { is_custom: boolean; tier_default: string }> {
  return apiFetch(`/tenants/${tenantId}/quota`);
}

export async function updateTenantQuota(
  tenantId: string,
  quota: Partial<ResourceQuota>
): Promise<ResourceQuota> {
  return apiFetch(`/tenants/${tenantId}/quota`, {
    method: "PUT",
    body: JSON.stringify(quota),
  });
}

export async function resetTenantQuota(tenantId: string): Promise<{ status: string; message: string }> {
  return apiFetch(`/tenants/${tenantId}/quota`, { method: "DELETE" });
}

export async function getTenantUsage(tenantId: string): Promise<TenantUsage> {
  return apiFetch(`/tenants/${tenantId}/usage`);
}

export async function getTenantQuotaStatus(tenantId: string): Promise<QuotaStatus> {
  return apiFetch(`/tenants/${tenantId}/quota-status`);
}

export async function getTenantContext(tenantId: string): Promise<Record<string, unknown>> {
  return apiFetch(`/tenants/${tenantId}/context`);
}

// =============================================================================
// Pending Agents (HITL for Onboarding)
// =============================================================================

export interface PendingAgentData {
  id: string;
  name: string;
  title: string;
  domain: string;
  description: string;
  capabilities: string[];
  guardrails: string[];
  gpt_url?: string;
  system_prompt?: string;
  source: string;
}

export interface PendingAgent {
  pending_id: string;
  agent: PendingAgentData;
  submitted_at: string;
  status: "pending" | "approved" | "rejected";
  source: string;
}

export async function listPendingAgents(): Promise<{ pending: PendingAgent[]; total: number }> {
  return apiFetch("/system/pending-agents");
}

export interface PendingAgentRequest {
  id: string;
  name: string;
  title?: string;
  domain?: string;
  description?: string;
  capabilities?: string[];
  guardrails?: string[];
  gpt_url?: string;
  system_prompt?: string;
  source?: string;
}

export async function addPendingAgentsBulk(agents: PendingAgentRequest[]): Promise<{ added: number; agents: Array<{ pending_id: string; name: string }> }> {
  return apiFetch("/system/pending-agents/bulk", {
    method: "POST",
    body: JSON.stringify(agents),
  });
}

export async function approvePendingAgent(pendingId: string): Promise<{ success: boolean; agent: AgentConfig; message: string }> {
  return apiFetch(`/system/pending-agents/${pendingId}/approve`, {
    method: "POST",
  });
}

export async function rejectPendingAgent(pendingId: string, reason?: string): Promise<{ success: boolean; message: string; reason?: string }> {
  return apiFetch(`/system/pending-agents/${pendingId}/reject?reason=${encodeURIComponent(reason || "")}`, {
    method: "POST",
  });
}

export async function approveAllPendingAgents(): Promise<{ approved: number; agents: string[] }> {
  return apiFetch("/system/pending-agents/approve-all", {
    method: "POST",
  });
}

// =============================================================================
// System Templates
// =============================================================================

export interface SystemTemplate {
  id: string;
  name: string;
  description: string;
  organization_type: string;
  created_at: string;
  agent_count: number;
  agents: AgentConfig[];
}

export async function listSystemTemplates(): Promise<{ templates: SystemTemplate[]; total: number }> {
  return apiFetch("/system/templates");
}

export async function exportAsTemplate(name: string, description?: string): Promise<SystemTemplate> {
  return apiFetch("/system/export-template", {
    method: "POST",
    body: JSON.stringify({ template_name: name, description: description || "" }),
  });
}

export interface ImportTemplateResult {
  success: boolean;
  template_name: string;
  created: number;
  skipped: number;
  created_agents: string[];
  skipped_agents: string[];
  message: string;
}

export async function importFromTemplate(templateId: string, merge: boolean = false): Promise<ImportTemplateResult> {
  return apiFetch("/system/import-template", {
    method: "POST",
    body: JSON.stringify({ template_id: templateId, merge }),
  });
}

export async function deleteSystemTemplate(templateId: string): Promise<{ success: boolean; message: string }> {
  return apiFetch(`/system/templates/${templateId}`, {
    method: "DELETE",
  });
}

// =============================================================================
// Governance API
// =============================================================================

export interface GovernanceSummary {
  version: number;
  policy_hash: string;
  require_approval: boolean;
  rules: {
    constitutional: number;
    organization: number;
    department: number;
  };
  immutable_rules: number;
  pending_changes: number;
  prohibited_topics: number;
  drift_status: string;
}

export interface PolicyVersion {
  version_id: string;
  version_number: number;
  created_at: string;
  created_by: string;
  change_description: string;
  policy_hash: string;
  policy_snapshot: Record<string, unknown>;
}

export interface PolicyChange {
  change_id: string;
  change_type: string;
  description: string;
  proposed_by: string;
  data: Record<string, unknown>;
  status: string;
  created_at: string;
  reviewed_by?: string;
  reviewed_at?: string;
  review_notes?: string;
}

export interface DriftReport {
  timestamp: string;
  current_version: number;
  policy_hash: string;
  memory_drift: { drift_detected: boolean; status: string; message: string };
  file_drift: { drift_detected: boolean; status: string; message: string };
  overall_status: string;
}

export async function getGovernanceSummary(): Promise<GovernanceSummary> {
  return apiFetch("/governance/summary");
}

export async function getGovernanceVersions(limit: number = 50): Promise<{ current_version: number; versions: PolicyVersion[] }> {
  return apiFetch(`/governance/versions?limit=${limit}`);
}

export async function rollbackToVersion(versionId: string, rolledBackBy: string = "admin"): Promise<{ success: boolean; rolled_back_to: string; new_version: number }> {
  return apiFetch(`/governance/versions/${versionId}/rollback`, {
    method: "POST",
    body: JSON.stringify({ rolled_back_by: rolledBackBy }),
  });
}

export async function getPendingPolicyChanges(): Promise<{ pending: PolicyChange[] }> {
  return apiFetch("/governance/approval/pending");
}

export async function approvePolicyChange(changeId: string, reviewedBy: string, reviewNotes: string = ""): Promise<{ success: boolean; message: string }> {
  return apiFetch(`/governance/approval/changes/${changeId}/approve`, {
    method: "POST",
    body: JSON.stringify({ reviewed_by: reviewedBy, review_notes: reviewNotes }),
  });
}

export async function rejectPolicyChange(changeId: string, reviewedBy: string, reviewNotes: string = ""): Promise<{ success: boolean; message: string }> {
  return apiFetch(`/governance/approval/changes/${changeId}/reject`, {
    method: "POST",
    body: JSON.stringify({ reviewed_by: reviewedBy, review_notes: reviewNotes }),
  });
}

export async function getDriftReport(): Promise<DriftReport> {
  return apiFetch("/governance/drift");
}

export async function syncPoliciesFromFile(): Promise<{ success: boolean; old_hash: string; new_hash: string; message: string }> {
  return apiFetch("/governance/drift/sync", { method: "POST" });
}

export async function getImmutableRules(): Promise<{ immutable_rules: string[] }> {
  return apiFetch("/governance/rules/immutable");
}

export async function markRuleImmutable(ruleId: string): Promise<{ success: boolean; rule_id: string; immutable: boolean }> {
  return apiFetch(`/governance/rules/${ruleId}/immutable`, { method: "POST" });
}

export async function unmarkRuleImmutable(ruleId: string): Promise<{ success: boolean; rule_id: string; immutable: boolean }> {
  return apiFetch(`/governance/rules/${ruleId}/immutable`, { method: "DELETE" });
}

// =============================================================================
// Branding
// =============================================================================

export interface BrandingSettings {
  app_name: string;
  tagline: string;
  organization: string;
  support_email: string;
  logo_url: string;
  favicon_url: string;
}

export interface LogoUploadResponse {
  success: boolean;
  filename: string;
  url: string;
  size: number;
  message: string;
}

export async function getBranding(): Promise<BrandingSettings> {
  return apiFetch("/system/branding");
}

export async function updateBranding(settings: Partial<BrandingSettings>): Promise<BrandingSettings & { success: boolean; message: string }> {
  return apiFetch("/system/branding", {
    method: "PUT",
    body: JSON.stringify(settings),
  });
}

export async function uploadLogo(file: File): Promise<LogoUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const url = `${API_BASE}/system/branding/upload-logo`;
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

export async function deleteLogo(): Promise<{ success: boolean; deleted: number; message: string }> {
  return apiFetch("/system/branding/logo", { method: "DELETE" });
}

export function getLogoUrl(logoPath: string): string {
  if (!logoPath) return "";
  if (logoPath.startsWith("http")) return logoPath;
  return `${API_BASE}${logoPath}`;
}

// =============================================================================
// Shared Canon (Organization-wide Knowledge)
// =============================================================================

export interface CanonStats {
  document_count: number;
  web_source_count: number;
  total_document_chunks: number;
  total_web_chunks: number;
  total_chunks: number;
  documents: Array<{ id: string; filename: string; chunks: number }>;
  web_sources: Array<{ id: string; name: string; url: string; chunks: number }>;
}

export interface CanonDocument {
  id: string;
  agent_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  uploaded_at: string;
  metadata: Record<string, unknown>;
}

export interface CanonWebSource {
  id: string;
  agent_id: string;
  url: string;
  name: string;
  description: string;
  refresh_interval_hours: number;
  last_refreshed: string | null;
  last_refresh_status: string;
  chunk_count: number;
  created_at: string;
  auto_refresh: boolean;
  selector: string | null;
}

export async function getCanonStats(): Promise<CanonStats> {
  return apiFetch("/system/canon");
}

export async function listCanonDocuments(): Promise<{ documents: CanonDocument[]; total: number }> {
  return apiFetch("/system/canon/documents");
}

export async function uploadCanonDocument(file: File): Promise<{ success: boolean; document: CanonDocument; message: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const url = `${API_BASE}/system/canon/documents`;
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

export async function deleteCanonDocument(documentId: string): Promise<{ success: boolean; message: string }> {
  return apiFetch(`/system/canon/documents/${documentId}`, { method: "DELETE" });
}

export async function clearCanon(): Promise<{ success: boolean; cleared: number; message: string }> {
  return apiFetch("/system/canon", { method: "DELETE" });
}

export async function listCanonWebSources(): Promise<{ sources: CanonWebSource[]; total: number }> {
  return apiFetch("/system/canon/web-sources");
}

export interface AddCanonWebSourceRequest {
  url: string;
  name?: string;
  description?: string;
  refresh_interval_hours?: number;
  selector?: string;
  auto_refresh?: boolean;
}

export async function addCanonWebSource(request: AddCanonWebSourceRequest): Promise<{ success: boolean; source: CanonWebSource; message: string }> {
  return apiFetch("/system/canon/web-sources", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function refreshCanonWebSource(sourceId: string): Promise<{ success: boolean; source: CanonWebSource; message: string }> {
  return apiFetch(`/system/canon/web-sources/${sourceId}/refresh`, { method: "POST" });
}

export async function deleteCanonWebSource(sourceId: string): Promise<{ success: boolean; message: string }> {
  return apiFetch(`/system/canon/web-sources/${sourceId}`, { method: "DELETE" });
}

// =============================================================================
// LLM Configuration
// =============================================================================

export interface LLMConfig {
  provider: "openai" | "anthropic" | "local";
  default_model: string;
  api_key_set: boolean;
  endpoint_url: string;
  max_tokens: number;
  temperature: number;
}

export interface LLMConfigUpdate {
  provider?: "openai" | "anthropic" | "local";
  api_key?: string;
  default_model?: string;
  endpoint_url?: string;
  max_tokens?: number;
  temperature?: number;
}

export interface LLMUsageStats {
  period: string;
  total_cost_usd: number;
  total_tokens: number;
  total_queries: number;
  avg_cost_per_query: number;
  avg_tokens_per_query: number;
  cost_by_day: Array<{ date: string; cost: number }>;
}

export async function getLLMConfig(): Promise<LLMConfig> {
  return apiFetch("/system/llm-config");
}

export async function updateLLMConfig(config: LLMConfigUpdate): Promise<{
  success: boolean;
  message: string;
  provider: string;
  default_model: string;
  api_key_set: boolean;
  endpoint_url: string;
}> {
  return apiFetch("/system/llm-config", {
    method: "PUT",
    body: JSON.stringify(config),
  });
}

export async function deleteLLMApiKey(): Promise<{ success: boolean; message: string }> {
  return apiFetch("/system/llm-config/api-key", { method: "DELETE" });
}

export async function getLLMUsageStats(): Promise<LLMUsageStats> {
  return apiFetch("/system/llm-config/usage");
}

// =============================================================================
// Notification Preferences
// =============================================================================

export interface NotificationChannel {
  email: boolean;
  push: boolean;
  in_app: boolean;
}

export interface NotificationPreferences {
  escalation_alerts: NotificationChannel;
  draft_pending: NotificationChannel;
  policy_changes: NotificationChannel;
  weekly_summary: NotificationChannel;
  sla_warnings: NotificationChannel;
  agent_errors: NotificationChannel;
  enabled: boolean;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
}

export interface NotificationChannelUpdate {
  email?: boolean;
  push?: boolean;
  in_app?: boolean;
}

export interface NotificationPreferencesUpdate {
  escalation_alerts?: NotificationChannelUpdate;
  draft_pending?: NotificationChannelUpdate;
  policy_changes?: NotificationChannelUpdate;
  weekly_summary?: NotificationChannelUpdate;
  sla_warnings?: NotificationChannelUpdate;
  agent_errors?: NotificationChannelUpdate;
  enabled?: boolean;
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
}

export async function getNotificationPreferences(userId: string): Promise<NotificationPreferences> {
  return apiFetch(`/sessions/users/${userId}/notifications`);
}

export async function updateNotificationPreferences(
  userId: string,
  prefs: NotificationPreferencesUpdate
): Promise<NotificationPreferences> {
  return apiFetch(`/sessions/users/${userId}/notifications`, {
    method: "PUT",
    body: JSON.stringify(prefs),
  });
}

export async function resetNotificationPreferences(userId: string): Promise<{ status: string; message: string }> {
  return apiFetch(`/sessions/users/${userId}/notifications/reset`, { method: "POST" });
}
