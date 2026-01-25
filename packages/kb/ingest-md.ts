/**
 * HAAIS Knowledge Layer - Markdown Ingestion CLI
 *
 * Usage:
 *   npx ts-node ingest-md.ts <rootFolder> <department_id> <visibility> <sensitivity> [knowledge_profile]
 */

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import OpenAI from "openai";
import { createClient } from "@supabase/supabase-js";

const VALID_VIS = ["private", "citywide", "shared"] as const;
const VALID_SENS = ["public", "internal", "confidential", "restricted", "privileged"] as const;

function validateArgs() {
  const [root, dept, vis, sens, profile] = process.argv.slice(2);
  if (!root || !dept || !vis || !sens) {
    console.error("Usage: npx ts-node ingest-md.ts <rootFolder> <department_id> <visibility> <sensitivity> [knowledge_profile]");
    process.exit(1);
  }
  if (!VALID_VIS.includes(vis as any)) { console.error(`Invalid visibility: ${vis}`); process.exit(1); }
  if (!VALID_SENS.includes(sens as any)) { console.error(`Invalid sensitivity: ${sens}`); process.exit(1); }
  if (!fs.existsSync(root)) { console.error(`Directory not found: ${root}`); process.exit(1); }
  return { root, department_id: dept, visibility_scope: vis, sensitivity_tier: sens, knowledge_profile: profile };
}

for (const name of ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]) {
  if (!process.env[name]) { console.error(`Missing: ${name}`); process.exit(1); }
}

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!);

const sha256 = (text: string) => crypto.createHash("sha256").update(text, "utf8").digest("hex");

function walk(dir: string): string[] {
  const out: string[] = [];
  for (const item of fs.readdirSync(dir)) {
    const p = path.join(dir, item);
    const st = fs.statSync(p);
    if (st.isDirectory()) out.push(...walk(p));
    else if (st.isFile() && [".md", ".markdown"].includes(path.extname(p).toLowerCase())) out.push(p);
  }
  return out;
}

function splitByHeadings(md: string) {
  const lines = md.split("\n"), out: { heading: string; text: string }[] = [];
  let heading = "", buf: string[] = [];
  for (const line of lines) {
    const m = line.match(/^(#{1,6})\s+(.*)$/);
    if (m) { if (buf.length) out.push({ heading, text: buf.join("\n").trim() }); heading = m[2].trim(); buf = [line]; }
    else buf.push(line);
  }
  if (buf.length) out.push({ heading, text: buf.join("\n").trim() });
  return out.filter(s => s.text.length > 0);
}

function chunkText(text: string, maxChars = 3500, overlap = 300): string[] {
  if (text.length <= maxChars) return [text];
  const chunks: string[] = [];
  let i = 0;
  while (i < text.length) {
    const end = Math.min(i + maxChars, text.length);
    chunks.push(text.slice(i, end).trim());
    if (end === text.length) break;
    i = Math.max(0, end - overlap);
  }
  return chunks.filter(c => c.length > 0);
}

async function embedBatch(inputs: string[], retries = 3): Promise<number[][]> {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const resp = await openai.embeddings.create({ model: "text-embedding-3-small", input: inputs });
      return resp.data.map(d => d.embedding);
    } catch (err: any) {
      if (err?.status === 429 && attempt < retries) {
        await new Promise(r => setTimeout(r, 1000 * attempt));
      } else throw err;
    }
  }
  throw new Error("Failed to embed");
}

async function upsertDocument(params: any): Promise<string> {
  const { raw, ...doc } = params;
  const fileSha = sha256(raw);
  const { data: existing } = await supabase.from("documents").select("id,sha256").eq("source_path", doc.source_path).maybeSingle();
  if (existing?.sha256 === fileSha) return existing.id;
  if (existing?.id) {
    await supabase.from("documents").update({ ...doc, sha256: fileSha, updated_at: new Date().toISOString() }).eq("id", existing.id);
    await supabase.from("document_chunks").delete().eq("document_id", existing.id);
    return existing.id;
  }
  const { data: inserted, error } = await supabase.from("documents").insert({ ...doc, sha256: fileSha }).select("id").single();
  if (error) throw error;
  return inserted.id as string;
}

async function ingestFile(root: string, filePath: string, opts: any) {
  let raw: string;
  try { raw = fs.readFileSync(filePath, "utf8"); } catch (err: any) { console.error(`Skipping ${filePath}: ${err.message}`); return; }
  const rel = path.relative(root, filePath).replace(/\\/g, "/");
  const title = path.basename(filePath, path.extname(filePath));

  const document_id = await upsertDocument({
    department_id: opts.department_id, title, source_path: rel, visibility_scope: opts.visibility_scope,
    sensitivity_tier: opts.sensitivity_tier, knowledge_profile: opts.knowledge_profile, shared_with: [], raw,
  });

  const { data: existingChunks } = await supabase.from("document_chunks").select("id").eq("document_id", document_id).limit(1);
  if (existingChunks && existingChunks.length > 0) { console.log(`⏭️  ${rel} (unchanged)`); return; }

  const sections = splitByHeadings(raw);
  const allChunks: { heading: string; content: string }[] = [];
  for (const s of sections) for (const c of chunkText(s.text)) allChunks.push({ heading: s.heading, content: c });
  if (allChunks.length === 0) { console.log(`⚠️  ${rel} (no content)`); return; }

  const rows: any[] = [];
  for (let i = 0; i < allChunks.length; i += 64) {
    const batch = allChunks.slice(i, i + 64);
    const embeddings = await embedBatch(batch.map(b => b.content));
    for (let j = 0; j < batch.length; j++) {
      rows.push({
        document_id, department_id: opts.department_id, chunk_index: i + j, heading: batch[j].heading || "",
        content: batch[j].content, embedding: embeddings[j], metadata: { source_path: rel, title, heading: batch[j].heading || "" },
      });
    }
    if (i + 64 < allChunks.length) await new Promise(r => setTimeout(r, 100));
  }

  for (let i = 0; i < rows.length; i += 200) {
    const { error } = await supabase.from("document_chunks").insert(rows.slice(i, i + 200));
    if (error) throw error;
  }
  console.log(`✅ ${rel} -> ${rows.length} chunks`);
}

async function main() {
  const args = validateArgs();
  console.log(`\nIngesting: ${args.root}\nDept: ${args.department_id}\nVis: ${args.visibility_scope}\nSens: ${args.sensitivity_tier}\nProfile: ${args.knowledge_profile || "(none)"}\n`);
  const files = walk(args.root);
  console.log(`Found ${files.length} markdown files\n`);
  let ok = 0, fail = 0;
  for (const f of files) {
    try { await ingestFile(args.root, f, args); ok++; } catch (err: any) { console.error(`❌ ${f}: ${err.message}`); fail++; }
  }
  console.log(`\nDone! Processed: ${ok}, Errors: ${fail}`);
}

main().catch(err => { console.error("Fatal:", err); process.exit(1); });
