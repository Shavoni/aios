/**
 * HAAIS Knowledge Layer - Express Server
 */

import { config } from "dotenv";
import { resolve } from "path";

// Load env from root .env file
config({ path: resolve(__dirname, "../../.env") });

import express from "express";
import cors from "cors";
import { kbQuery, kbHealth, kbAgentInfo } from "./query";
import { systemStatus, systemReset, systemProvision, systemImportManifest, systemGenerateKey } from "./system";

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors({
  origin: ["http://localhost:3000", "http://localhost:3001", "http://localhost:3002",
           "http://127.0.0.1:3000", "http://127.0.0.1:3001", "http://127.0.0.1:3002",
           "https://chat.openai.com", "https://chatgpt.com"],
  credentials: true,
}));
app.use(express.json({ limit: "10mb" }));

app.use((req, _res, next) => {
  console.log(`${new Date().toISOString()} ${req.method} ${req.path}`);
  next();
});

app.post("/kb/query", kbQuery);
app.get("/kb/health", kbHealth);
app.get("/kb/agent", kbAgentInfo);

// System management endpoints (white-label support)
app.get("/system/status", systemStatus);
app.post("/system/reset", systemReset);
app.post("/system/provision", systemProvision);
app.post("/system/import-manifest", systemImportManifest);
app.post("/system/generate-key", systemGenerateKey);

app.get("/", (_req, res) => res.redirect("/kb/health"));

app.use((_req, res) => {
  res.status(404).json({
    error: "Not Found",
    endpoints: {
      kb: ["POST /kb/query", "GET /kb/health", "GET /kb/agent"],
      system: ["GET /system/status", "POST /system/reset", "POST /system/provision", "POST /system/import-manifest", "POST /system/generate-key"],
    },
  });
});

app.listen(PORT, () => {
  console.log(`
╔═══════════════════════════════════════════════════════════╗
║           HAAIS Knowledge Layer API                       ║
╠═══════════════════════════════════════════════════════════╣
║  Server:    http://localhost:${PORT}                         ║
║  Health:    http://localhost:${PORT}/kb/health               ║
║  Query:     POST http://localhost:${PORT}/kb/query           ║
╠═══════════════════════════════════════════════════════════╣
║  System Management (White-Label)                          ║
║  Status:    GET  /system/status                           ║
║  Reset:     POST /system/reset                            ║
║  Provision: POST /system/provision                        ║
║  Import:    POST /system/import-manifest                  ║
║  Gen Key:   POST /system/generate-key                     ║
╚═══════════════════════════════════════════════════════════╝
`);
});

export default app;
