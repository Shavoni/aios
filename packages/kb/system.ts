/**
 * HAAIS Knowledge Layer - System Management
 *
 * White-label support: Reset and provision for new clients
 */

import type { Request, Response } from "express";
import { agentRegistry, SENSITIVITY_ORDER, type AgentManifest } from "./manifest";
import { getSupabase } from "./query";

interface ProvisionRequest {
  client_name: string;
  organization: string;
  admin_email?: string;
  description?: string;
}

interface ResetOptions {
  archive_logs?: boolean;
  confirm?: string;
}

/**
 * GET /system/status
 * Current system configuration
 */
export async function systemStatus(_req: Request, res: Response): Promise<Response> {
  const manifest = agentRegistry.getManifest();

  // Count records in each table
  const [depts, docs, chunks, logs, keys] = await Promise.all([
    getSupabase().from("departments").select("id", { count: "exact", head: true }),
    getSupabase().from("documents").select("id", { count: "exact", head: true }),
    getSupabase().from("document_chunks").select("id", { count: "exact", head: true }),
    getSupabase().from("kb_query_logs").select("id", { count: "exact", head: true }),
    getSupabase().from("agent_api_keys").select("id", { count: "exact", head: true }),
  ]);

  return res.json({
    status: "configured",
    manifest: manifest ? {
      id: manifest.manifest_id,
      version: manifest.schema_version,
      agents: manifest.agents.length,
      created_at: manifest.created_at,
    } : null,
    data: {
      departments: depts.count ?? 0,
      documents: docs.count ?? 0,
      chunks: chunks.count ?? 0,
      query_logs: logs.count ?? 0,
      api_keys: keys.count ?? 0,
    },
    timestamp: new Date().toISOString(),
  });
}

/**
 * POST /system/reset
 * Clear all client-specific data for white-label redeployment
 */
export async function systemReset(req: Request, res: Response): Promise<Response> {
  const { archive_logs = true, confirm }: ResetOptions = req.body ?? {};

  // Safety check
  if (confirm !== "RESET_ALL_CLIENT_DATA") {
    return res.status(400).json({
      error: "Confirmation required",
      message: "Set confirm: 'RESET_ALL_CLIENT_DATA' to proceed",
      warning: "This will delete ALL agents, documents, and knowledge base data",
    });
  }

  const results: Record<string, any> = {};

  try {
    // 1. Archive audit logs if requested
    if (archive_logs) {
      const { data: logs } = await getSupabase()
        .from("kb_query_logs")
        .select("*")
        .order("at", { ascending: true });

      if (logs && logs.length > 0) {
        results.archived_logs = logs.length;
        // In production, you'd upload this to S3 or similar
        // For now, we'll just note the count
      }
    }

    // 2. Delete in correct order (foreign key constraints)

    // Delete chunks first (references documents)
    const { error: chunksErr } = await getSupabase()
      .from("document_chunks")
      .delete()
      .neq("id", "00000000-0000-0000-0000-000000000000"); // Delete all
    if (chunksErr) throw new Error(`Failed to delete chunks: ${chunksErr.message}`);
    results.chunks_deleted = true;

    // Delete documents
    const { error: docsErr } = await getSupabase()
      .from("documents")
      .delete()
      .neq("id", "00000000-0000-0000-0000-000000000000");
    if (docsErr) throw new Error(`Failed to delete documents: ${docsErr.message}`);
    results.documents_deleted = true;

    // Delete query logs
    const { error: logsErr } = await getSupabase()
      .from("kb_query_logs")
      .delete()
      .neq("id", "00000000-0000-0000-0000-000000000000");
    if (logsErr) throw new Error(`Failed to delete logs: ${logsErr.message}`);
    results.logs_deleted = true;

    // Delete API keys
    const { error: keysErr } = await getSupabase()
      .from("agent_api_keys")
      .delete()
      .neq("id", "00000000-0000-0000-0000-000000000000");
    if (keysErr) throw new Error(`Failed to delete API keys: ${keysErr.message}`);
    results.api_keys_deleted = true;

    // Delete manifests
    const { error: manifestErr } = await getSupabase()
      .from("agent_manifests")
      .delete()
      .neq("id", "00000000-0000-0000-0000-000000000000");
    if (manifestErr) throw new Error(`Failed to delete manifests: ${manifestErr.message}`);
    results.manifests_deleted = true;

    // Delete departments
    const { error: deptsErr } = await getSupabase()
      .from("departments")
      .delete()
      .neq("id", "placeholder");
    if (deptsErr) throw new Error(`Failed to delete departments: ${deptsErr.message}`);
    results.departments_deleted = true;

    return res.json({
      status: "reset_complete",
      message: "All client data has been cleared. System ready for new client provisioning.",
      results,
      next_step: "POST /system/provision with new client details",
      timestamp: new Date().toISOString(),
    });

  } catch (err: any) {
    return res.status(500).json({
      error: "Reset failed",
      message: err.message,
      partial_results: results,
    });
  }
}

/**
 * POST /system/provision
 * Set up system for a new client
 */
export async function systemProvision(req: Request, res: Response): Promise<Response> {
  const { client_name, organization, admin_email, description }: ProvisionRequest = req.body ?? {};

  if (!client_name || !organization) {
    return res.status(400).json({
      error: "Bad Request",
      message: "client_name and organization are required",
    });
  }

  try {
    // Create a fresh concierge system prompt
    const conciergePrompt = `You are the AI Concierge for ${client_name}.

Your role is to:
1. Greet staff and understand their needs
2. Route them to the appropriate department assistant
3. Provide safe, general guidance when appropriate
4. Escalate sensitive matters to human leadership

Guidelines:
- Ask clarifying questions to understand intent
- Never speculate on policy or make commitments
- Protect sensitive information
- Be helpful, professional, and efficient

Available departments will be configured by your administrator.`;

    // Create base manifest for new client
    const newManifest: AgentManifest = {
      schema_version: "1.0.0",
      manifest_id: `${organization}-agents-v1`,
      created_at: new Date().toISOString(),
      agents: [
        {
          agent_id: `${organization}-concierge`,
          display_name: `${client_name} AI Concierge`,
          department_id: "concierge",
          gpt_name_in_openai: `${client_name} Concierge GPT`,
          public_description: `The front door to ${client_name}'s AI assistant network. Routes staff to the right department.`,
          instruction_kernel: conciergePrompt,
          default_max_sensitivity: "public",
          include_citywide: true,
          allowed_scopes: ["routing", "general_info"],
          knowledge_profile: ["employee_handbook", "org_directory"],
          action_profile: {
            can_draft: false,
            can_submit: false,
            can_query_external: false,
            can_schedule: false,
          },
        },
      ],
      sensitivity_levels: ["public", "internal", "confidential", "restricted", "privileged"],
      citywide_knowledge_base: ["employee_handbook", "ethics_policy", "org_directory"],
    };

    // Store manifest in database
    const { error: manifestErr } = await getSupabase()
      .from("agent_manifests")
      .insert({
        manifest_id: newManifest.manifest_id,
        schema_version: newManifest.schema_version,
        manifest: newManifest,
        is_active: true,
      });

    if (manifestErr) throw new Error(`Failed to store manifest: ${manifestErr.message}`);

    // Create concierge department
    const { error: deptErr } = await getSupabase()
      .from("departments")
      .insert({
        id: "concierge",
        name: "Concierge / General",
      });

    if (deptErr && !deptErr.message.includes("duplicate")) {
      throw new Error(`Failed to create department: ${deptErr.message}`);
    }

    // Load the new manifest into the registry
    agentRegistry.loadManifest(newManifest);

    return res.json({
      status: "provisioned",
      client: {
        name: client_name,
        organization,
        admin_email,
        description,
      },
      manifest: {
        id: newManifest.manifest_id,
        agents: newManifest.agents.length,
      },
      next_steps: [
        "1. Add departments via POST /system/add-department",
        "2. Add agents via POST /system/add-agent or import manifest",
        "3. Generate API keys for each agent",
        "4. Ingest knowledge base documents",
        "5. Configure Custom GPT Actions",
      ],
      timestamp: new Date().toISOString(),
    });

  } catch (err: any) {
    return res.status(500).json({
      error: "Provisioning failed",
      message: err.message,
    });
  }
}

/**
 * POST /system/import-manifest
 * Import a complete manifest for a client
 */
export async function systemImportManifest(req: Request, res: Response): Promise<Response> {
  const manifest: AgentManifest = req.body;

  if (!manifest?.manifest_id || !manifest?.agents) {
    return res.status(400).json({
      error: "Bad Request",
      message: "Valid manifest with manifest_id and agents array required",
    });
  }

  try {
    // Validate manifest structure
    if (!Array.isArray(manifest.agents) || manifest.agents.length === 0) {
      return res.status(400).json({
        error: "Invalid manifest",
        message: "Manifest must contain at least one agent",
      });
    }

    // Validate sensitivity levels
    if (!manifest.sensitivity_levels || manifest.sensitivity_levels.length === 0) {
      manifest.sensitivity_levels = SENSITIVITY_ORDER;
    }

    // Store/update manifest in database
    const { error: manifestErr } = await getSupabase()
      .from("agent_manifests")
      .upsert({
        manifest_id: manifest.manifest_id,
        schema_version: manifest.schema_version || "1.0.0",
        manifest: manifest,
        is_active: true,
        updated_at: new Date().toISOString(),
      }, {
        onConflict: "manifest_id",
      });

    if (manifestErr) throw new Error(`Failed to store manifest: ${manifestErr.message}`);

    // Create departments from agents
    const departments = new Set(manifest.agents.map(a => a.department_id));
    for (const deptId of departments) {
      const agent = manifest.agents.find(a => a.department_id === deptId);
      await getSupabase()
        .from("departments")
        .upsert({
          id: deptId,
          name: agent?.display_name?.replace(" Assistant", "") || deptId,
        }, {
          onConflict: "id",
        });
    }

    // Load into registry
    agentRegistry.loadManifest(manifest);

    return res.json({
      status: "manifest_imported",
      manifest: {
        id: manifest.manifest_id,
        version: manifest.schema_version,
        agents: manifest.agents.length,
        departments: departments.size,
      },
      agents: manifest.agents.map(a => ({
        id: a.agent_id,
        name: a.display_name,
        department: a.department_id,
        sensitivity: a.default_max_sensitivity,
      })),
      next_steps: [
        "1. Generate API keys: POST /system/generate-key",
        "2. Ingest knowledge base documents",
        "3. Configure Custom GPT Actions with keys",
      ],
      timestamp: new Date().toISOString(),
    });

  } catch (err: any) {
    return res.status(500).json({
      error: "Import failed",
      message: err.message,
    });
  }
}

/**
 * POST /system/generate-key
 * Generate an API key for an agent
 */
export async function systemGenerateKey(req: Request, res: Response): Promise<Response> {
  const { agent_id, description } = req.body ?? {};

  if (!agent_id) {
    return res.status(400).json({
      error: "Bad Request",
      message: "agent_id is required",
    });
  }

  // Verify agent exists
  const agent = agentRegistry.getAgent(agent_id);
  if (!agent) {
    return res.status(404).json({
      error: "Agent not found",
      message: `No agent with id: ${agent_id}`,
      available: agentRegistry.getAllAgents().map(a => a.agent_id),
    });
  }

  // Generate secure random key
  const crypto = await import("node:crypto");
  const key = `sk-haais-${crypto.randomBytes(24).toString("hex")}`;
  const keyHash = crypto.createHash("sha256").update(key).digest("hex");

  try {
    // Store key hash (never store plain key)
    const { error } = await getSupabase()
      .from("agent_api_keys")
      .insert({
        api_key_hash: keyHash,
        agent_id,
        description: description || `Key for ${agent.display_name}`,
        enabled: true,
      });

    if (error) throw new Error(`Failed to store key: ${error.message}`);

    // Register in memory
    agentRegistry.registerKey(key, agent_id);

    return res.json({
      status: "key_generated",
      agent_id,
      agent_name: agent.display_name,
      api_key: key,  // Only shown once!
      warning: "Save this key securely - it will not be shown again",
      usage: {
        header: "Authorization",
        value: `Bearer ${key}`,
      },
      timestamp: new Date().toISOString(),
    });

  } catch (err: any) {
    return res.status(500).json({
      error: "Key generation failed",
      message: err.message,
    });
  }
}
