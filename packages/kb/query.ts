/**
 * HAAIS Knowledge Layer - Query Endpoint
 */

import type { Request, Response } from "express";
import OpenAI from "openai";
import { createClient } from "@supabase/supabase-js";
import { agentRegistry, getEffectiveSensitivity, CLEVELAND_MANIFEST, type Sensitivity, type AgentDefinition } from "./manifest";

// Lazy initialization - clients are created on first use
let openai: OpenAI | null = null;
let supabase: ReturnType<typeof createClient> | null = null;
let initialized = false;

function initClients() {
  if (initialized) return;
  const REQUIRED_ENV = ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"];
  for (const name of REQUIRED_ENV) {
    if (!process.env[name]) throw new Error(`Missing required env var: ${name}`);
  }
  openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!, { auth: { persistSession: false } });
  agentRegistry.loadManifest(CLEVELAND_MANIFEST);
  initialized = true;
}

export function getSupabase() {
  initClients();
  return supabase!;
}

export function getOpenAI() {
  initClients();
  return openai!;
}

function registerDevKeys() {
  if (process.env.NODE_ENV !== "production") {
    agentRegistry.registerKey("sk-dev-public-safety", "cle-public-safety-001");
    agentRegistry.registerKey("sk-dev-public-works", "cle-public-works-002");
    agentRegistry.registerKey("sk-dev-hr", "cle-hr-003");
    agentRegistry.registerKey("sk-dev-finance", "cle-finance-004");
    agentRegistry.registerKey("sk-dev-community-dev", "cle-community-dev-005");
    agentRegistry.registerKey("sk-dev-public-health", "cle-public-health-006");
    agentRegistry.registerKey("sk-dev-law", "cle-law-007");
    agentRegistry.registerKey("sk-dev-it", "cle-it-008");
    console.log("Registered development API keys");
  }
}

interface KBQueryRequest {
  question: string;
  include_citywide?: boolean;
  max_sensitivity?: Sensitivity;
  top_k?: number;
}

export async function kbQuery(req: Request, res: Response): Promise<Response> {
  initClients();
  registerDevKeys();

  const keyConfig = agentRegistry.validateKey(req.headers.authorization);
  if (!keyConfig) {
    return res.status(401).json({ error: "Unauthorized", message: "Missing or invalid Authorization header" });
  }

  const agent: AgentDefinition = keyConfig.agent;
  const { question, include_citywide, max_sensitivity, top_k = 8 }: KBQueryRequest = req.body ?? {};

  if (!question || typeof question !== "string" || question.trim().length === 0) {
    return res.status(400).json({ error: "Bad Request", message: "question is required" });
  }

  const effectiveIncludeCitywide = include_citywide ?? agent.include_citywide;
  const effectiveSensitivity = getEffectiveSensitivity(max_sensitivity, agent.default_max_sensitivity);
  const effectiveTopK = Math.min(Math.max(top_k, 1), 20);
  const accessibleProfiles = agentRegistry.getAccessibleKnowledge(agent.agent_id);

  let queryEmbedding: number[];
  try {
    const embResponse = await getOpenAI().embeddings.create({ model: "text-embedding-3-small", input: question.trim() });
    queryEmbedding = embResponse.data[0].embedding;
  } catch (err) {
    console.error("OpenAI embedding error:", err);
    return res.status(502).json({ error: "Embedding Service Unavailable" });
  }

  const { data, error: dbError } = accessibleProfiles.length > 0
    ? await getSupabase().rpc("kb_match_chunks_by_profile", {
        query_embedding: queryEmbedding,
        dept: agent.department_id,
        include_citywide: effectiveIncludeCitywide,
        max_sensitivity: effectiveSensitivity,
        allowed_profiles: accessibleProfiles,
        match_count: effectiveTopK,
      })
    : await getSupabase().rpc("kb_match_chunks", {
        query_embedding: queryEmbedding,
        dept: agent.department_id,
        include_citywide: effectiveIncludeCitywide,
        max_sensitivity: effectiveSensitivity,
        match_count: effectiveTopK,
      });

  if (dbError) {
    console.error("Supabase query error:", dbError);
    return res.status(500).json({ error: "Database Error", message: dbError.message });
  }

  const results = data ?? [];

  await getSupabase().from("kb_query_logs").insert({
    requester: `gpt:${agent.agent_id}`,
    agent_id: agent.agent_id,
    department_id: agent.department_id,
    max_sensitivity: effectiveSensitivity,
    query: question.trim(),
    retrieved_chunk_ids: results.map((r: any) => r.chunk_id),
    retrieved_document_ids: [...new Set(results.map((r: any) => r.document_id))],
    knowledge_profiles_used: [...new Set(results.map((r: any) => r.knowledge_profile).filter(Boolean))],
  });

  return res.json({
    evidence: results.map((r: any) => ({
      title: r.title, heading: r.heading ?? "", content: r.content,
      similarity: r.similarity, knowledge_profile: r.knowledge_profile ?? "", metadata: r.metadata,
    })),
    citations: results.map((r: any) => ({
      title: r.title, heading: r.heading ?? "", source_path: r.source_path ?? "",
      knowledge_profile: r.knowledge_profile ?? "", document_id: r.document_id, chunk_id: r.chunk_id,
    })),
    agent: { agent_id: agent.agent_id, display_name: agent.display_name, department_id: agent.department_id },
  });
}

export async function kbHealth(_req: Request, res: Response): Promise<Response> {
  initClients();
  registerDevKeys();

  let openaiOk = false, supabaseOk = false;
  try { await getOpenAI().models.list(); openaiOk = true; } catch {}
  try { const { error } = await getSupabase().from("departments").select("id").limit(1); supabaseOk = !error; } catch {}
  const healthy = openaiOk && supabaseOk;
  const manifest = agentRegistry.getManifest();
  return res.status(healthy ? 200 : 503).json({
    status: healthy ? "ok" : "degraded",
    openai: openaiOk ? "ok" : "unavailable",
    supabase: supabaseOk ? "ok" : "unavailable",
    manifest: manifest ? { id: manifest.manifest_id, version: manifest.schema_version, agents: manifest.agents.length } : null,
    timestamp: new Date().toISOString(),
  });
}

export async function kbAgentInfo(req: Request, res: Response): Promise<Response> {
  initClients();
  registerDevKeys();

  const keyConfig = agentRegistry.validateKey(req.headers.authorization);
  if (!keyConfig) return res.status(401).json({ error: "Unauthorized" });
  const agent = keyConfig.agent;
  return res.json({
    agent_id: agent.agent_id, display_name: agent.display_name, department_id: agent.department_id,
    gpt_name: agent.gpt_name_in_openai, description: agent.public_description,
    default_max_sensitivity: agent.default_max_sensitivity, include_citywide: agent.include_citywide,
    allowed_scopes: agent.allowed_scopes, knowledge_profiles: agentRegistry.getAccessibleKnowledge(agent.agent_id),
    action_profile: agent.action_profile,
  });
}
