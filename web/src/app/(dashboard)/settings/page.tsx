"use client";

import { useState, useEffect } from "react";
import {
  Key,
  Shield,
  Bell,
  Save,
  Eye,
  EyeOff,
  Plus,
  Trash2,
  Building2,
  AlertTriangle,
  RefreshCw,
  Sparkles,
  Loader2,
  CheckCircle2,
  Settings,
  Cog,
  Database,
  Cpu,
  Zap,
  Lock,
  Mail,
  BellRing,
  FileText,
  Cloud,
  Palette,
  ImageIcon,
  Upload,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import {
  resetForNewClient,
  regenerateConcierge,
  listAgents,
  getGovernanceSummary,
  getGovernanceVersions,
  rollbackToVersion,
  getPendingPolicyChanges,
  approvePolicyChange,
  rejectPolicyChange,
  getDriftReport,
  syncPoliciesFromFile,
  getImmutableRules,
  getBranding,
  updateBranding,
  uploadLogo,
  deleteLogo,
  getLogoUrl,
  getCanonStats,
  listCanonDocuments,
  uploadCanonDocument,
  deleteCanonDocument,
  clearCanon,
  listCanonWebSources,
  addCanonWebSource,
  refreshCanonWebSource,
  deleteCanonWebSource,
  getLLMConfig,
  updateLLMConfig,
  getLLMUsageStats,
  getNotificationPreferences,
  updateNotificationPreferences,
  type GovernanceSummary,
  type PolicyVersion,
  type PolicyChange,
  type DriftReport,
  type BrandingSettings,
  type CanonStats,
  type CanonDocument,
  type CanonWebSource,
  type LLMConfig,
  type LLMUsageStats,
  type NotificationPreferences,
} from "@/lib/api";
import { config } from "@/lib/config";
import { History, GitBranch, AlertCircle, RotateCcw, FileCheck, ShieldCheck } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";

interface Policy {
  id: string;
  name: string;
  type: "constitutional" | "departmental";
  domain: string;
  trigger: string;
  action: string;
  enabled: boolean;
}

const mockPolicies: Policy[] = [
  {
    id: "pol_001",
    name: "Public Statement Draft",
    type: "constitutional",
    domain: "All",
    trigger: "audience = public",
    action: "DRAFT mode",
    enabled: true,
  },
  {
    id: "pol_002",
    name: "Legal Contract Escalation",
    type: "constitutional",
    domain: "Legal",
    trigger: "risk.contains(legal_contract)",
    action: "ESCALATE",
    enabled: true,
  },
  {
    id: "pol_003",
    name: "PII Data Protection",
    type: "constitutional",
    domain: "All",
    trigger: "risk.contains(pii)",
    action: "local_only = true",
    enabled: true,
  },
  {
    id: "pol_004",
    name: "HR Employment Actions",
    type: "departmental",
    domain: "HR",
    trigger: "task = employment_action",
    action: "DRAFT mode",
    enabled: true,
  },
  {
    id: "pol_005",
    name: "Finance High Value",
    type: "departmental",
    domain: "Finance",
    trigger: "impact = high",
    action: "ESCALATE",
    enabled: false,
  },
];

const providerConfigs = {
  openai: {
    name: "OpenAI",
    gradient: "from-emerald-500 to-teal-500",
    bg: "bg-emerald-50 dark:bg-emerald-950/30",
    text: "text-emerald-700 dark:text-emerald-300",
  },
  anthropic: {
    name: "Anthropic",
    gradient: "from-orange-500 to-amber-500",
    bg: "bg-orange-50 dark:bg-orange-950/30",
    text: "text-orange-700 dark:text-orange-300",
  },
  local: {
    name: "Local LLM",
    gradient: "from-purple-500 to-indigo-500",
    bg: "bg-purple-50 dark:bg-purple-950/30",
    text: "text-purple-700 dark:text-purple-300",
  },
};

export default function SettingsPage() {
  const [showApiKey, setShowApiKey] = useState(false);
  const [provider, setProvider] = useState<"openai" | "anthropic" | "local">("openai");

  // Client setup state
  const [clientName, setClientName] = useState("");
  const [organization, setOrganization] = useState("");
  const [description, setDescription] = useState("");
  const [isResetting, setIsResetting] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [agentCount, setAgentCount] = useState(0);

  // LLM config state
  const [llmConfig, setLlmConfig] = useState<LLMConfig | null>(null);
  const [llmUsage, setLlmUsage] = useState<LLMUsageStats | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [defaultModel, setDefaultModel] = useState("");
  const [endpointUrl, setEndpointUrl] = useState("");
  const [isSavingLLM, setIsSavingLLM] = useState(false);

  // Notification preferences state
  const [notificationPrefs, setNotificationPrefs] = useState<NotificationPreferences | null>(null);
  const [isSavingNotifs, setIsSavingNotifs] = useState(false);

  // Load current agent count and LLM config
  useEffect(() => {
    loadAgentCount();
    loadLLMConfig();
    loadNotificationPreferences();
  }, []);

  async function loadAgentCount() {
    try {
      const data = await listAgents();
      setAgentCount(data.total);
    } catch (error) {
      console.error("Failed to load agents:", error);
    }
  }

  async function loadLLMConfig() {
    try {
      const [configData, usageData] = await Promise.all([
        getLLMConfig(),
        getLLMUsageStats(),
      ]);
      setLlmConfig(configData);
      setLlmUsage(usageData);
      setProvider(configData.provider);
      setDefaultModel(configData.default_model);
      setEndpointUrl(configData.endpoint_url || "");
    } catch (error) {
      console.error("Failed to load LLM config:", error);
    }
  }

  async function loadNotificationPreferences() {
    try {
      // Use "current" as placeholder - in production, get from auth context
      const prefs = await getNotificationPreferences("current");
      setNotificationPrefs(prefs);
    } catch (error) {
      console.error("Failed to load notification preferences:", error);
      // Set defaults if API not available
      setNotificationPrefs({
        escalation_alerts: { email: true, push: true, in_app: true },
        draft_pending: { email: false, push: true, in_app: true },
        policy_changes: { email: true, push: false, in_app: true },
        weekly_summary: { email: false, push: false, in_app: false },
        sla_warnings: { email: true, push: true, in_app: true },
        agent_errors: { email: true, push: false, in_app: true },
        enabled: true,
        quiet_hours_start: null,
        quiet_hours_end: null,
      });
    }
  }

  async function handleSaveLLMConfig() {
    setIsSavingLLM(true);
    try {
      await updateLLMConfig({
        provider,
        api_key: apiKeyInput || undefined,
        default_model: defaultModel || undefined,
        endpoint_url: endpointUrl || undefined,
      });
      toast.success("LLM configuration saved");
      setApiKeyInput(""); // Clear the input after save
      loadLLMConfig(); // Reload to get updated state
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to save LLM config";
      toast.error(message);
    } finally {
      setIsSavingLLM(false);
    }
  }

  async function handleToggleNotification(
    notificationType: keyof NotificationPreferences,
    channel?: "email" | "push" | "in_app"
  ) {
    if (!notificationPrefs) return;
    setIsSavingNotifs(true);

    try {
      let updates: Record<string, unknown> = {};

      if (notificationType === "enabled") {
        updates = { enabled: !notificationPrefs.enabled };
      } else if (channel && typeof notificationPrefs[notificationType] === "object") {
        const currentChannel = notificationPrefs[notificationType] as { email: boolean; push: boolean; in_app: boolean };
        updates = {
          [notificationType]: {
            [channel]: !currentChannel[channel],
          },
        };
      }

      const updated = await updateNotificationPreferences("current", updates);
      setNotificationPrefs(updated);
      toast.success("Notification preferences updated");
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to update notifications";
      toast.error(message);
    } finally {
      setIsSavingNotifs(false);
    }
  }

  async function handleReset() {
    if (!clientName.trim() || !organization.trim()) {
      toast.error("Client name and organization are required");
      return;
    }

    setIsResetting(true);
    try {
      const result = await resetForNewClient({
        client_name: clientName.trim(),
        organization: organization.trim(),
        description: description.trim(),
      });

      toast.success(result.message);
      setClientName("");
      setOrganization("");
      setDescription("");
      loadAgentCount();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Reset failed";
      toast.error(message);
    } finally {
      setIsResetting(false);
    }
  }

  async function handleRegenerateConcierge() {
    setIsRegenerating(true);
    try {
      await regenerateConcierge();
      toast.success("Concierge updated with current agent knowledge");
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Regeneration failed";
      toast.error(message);
    } finally {
      setIsRegenerating(false);
    }
  }

  const currentProviderConfig = providerConfigs[provider];

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Gradient Header */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-slate-700 via-zinc-800 to-slate-900 p-8 text-white shadow-2xl">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDM0aDR2MmgtNHYtMnptMC04aDR2Nmg0djJoLTh2LTh6bTAgMTZoOHYyaC04di0yem0tMTYgMGg0djJoLTR2LTJ6bTAtOGg0djZoNHYyaC04di04em0wIDE2aDh2MmgtOHYtMnoiLz48L2c+PC9nPjwvc3ZnPg==')] opacity-30"></div>
        <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-white/5 blur-3xl"></div>
        <div className="absolute -bottom-20 -left-20 h-64 w-64 rounded-full bg-zinc-400/10 blur-3xl"></div>
        <div className="relative">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/10 backdrop-blur-sm">
                  <Cog className="h-7 w-7" />
                </div>
                <div>
                  <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
                  <p className="text-slate-300">System Configuration</p>
                </div>
              </div>
              <p className="mt-4 max-w-xl text-white/70">
                Configure {config.appName} instance, manage API keys, set up governance policies,
                and customize notification preferences.
              </p>
            </div>
            <div className="hidden lg:flex items-center gap-2">
              <Badge className="bg-white/10 text-white border-0 px-3 py-1.5">
                <Sparkles className="h-3 w-3 mr-1" />
                {config.organization}
              </Badge>
            </div>
          </div>
        </div>
      </div>

      <Tabs defaultValue="client" className="space-y-6">
        <TabsList className="bg-muted/50 p-1">
          <TabsTrigger value="client" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-slate-600 data-[state=active]:to-zinc-600 data-[state=active]:text-white">
            <Building2 className="mr-2 h-4 w-4" />
            Client Setup
          </TabsTrigger>
          <TabsTrigger value="api" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-emerald-500 data-[state=active]:to-teal-500 data-[state=active]:text-white">
            <Key className="mr-2 h-4 w-4" />
            API Keys
          </TabsTrigger>
          <TabsTrigger value="governance" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-blue-500 data-[state=active]:to-indigo-500 data-[state=active]:text-white">
            <Shield className="mr-2 h-4 w-4" />
            Governance
          </TabsTrigger>
          <TabsTrigger value="notifications" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-amber-500 data-[state=active]:to-orange-500 data-[state=active]:text-white">
            <Bell className="mr-2 h-4 w-4" />
            Notifications
          </TabsTrigger>
          <TabsTrigger value="branding" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-pink-500 data-[state=active]:to-rose-500 data-[state=active]:text-white">
            <Palette className="mr-2 h-4 w-4" />
            Branding
          </TabsTrigger>
          <TabsTrigger value="canon" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-cyan-500 data-[state=active]:to-teal-500 data-[state=active]:text-white">
            <Database className="mr-2 h-4 w-4" />
            Shared Canon
          </TabsTrigger>
        </TabsList>

        {/* Client Setup Tab */}
        <TabsContent value="client" className="space-y-6">
          {/* Current Status */}
          <Card className="border-0 shadow-lg">
            <CardHeader className="border-b bg-muted/30">
              <CardTitle className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500 text-white">
                  <Sparkles className="h-4 w-4" />
                </div>
                Current Deployment
              </CardTitle>
              <CardDescription>
                System status and Concierge management
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6 space-y-6">
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-blue-950/50 dark:to-indigo-900/30 p-4">
                  <div className="absolute right-0 top-0 h-16 w-16 translate-x-4 -translate-y-4 rounded-full bg-blue-500/20"></div>
                  <div className="relative">
                    <div className="text-3xl font-bold text-blue-700 dark:text-blue-300">{agentCount}</div>
                    <div className="text-sm text-blue-600/70 dark:text-blue-400">Total Agents</div>
                  </div>
                </div>
                <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-green-50 to-emerald-100 dark:from-green-950/50 dark:to-emerald-900/30 p-4">
                  <div className="absolute right-0 top-0 h-16 w-16 translate-x-4 -translate-y-4 rounded-full bg-green-500/20"></div>
                  <div className="relative">
                    <div className="text-3xl font-bold text-green-700 dark:text-green-300">Active</div>
                    <div className="text-sm text-green-600/70 dark:text-green-400">Concierge Status</div>
                  </div>
                </div>
                <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-purple-50 to-violet-100 dark:from-purple-950/50 dark:to-violet-900/30 p-4">
                  <div className="absolute right-0 top-0 h-16 w-16 translate-x-4 -translate-y-4 rounded-full bg-purple-500/20"></div>
                  <div className="relative">
                    <div className="text-3xl font-bold text-purple-700 dark:text-purple-300 truncate">{config.organization}</div>
                    <div className="text-sm text-purple-600/70 dark:text-purple-400">Organization</div>
                  </div>
                </div>
              </div>

              <Separator />

              <div className="flex items-center justify-between p-4 rounded-xl bg-muted/50">
                <div>
                  <div className="font-medium flex items-center gap-2">
                    <RefreshCw className="h-4 w-4 text-primary" />
                    Update Concierge
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Regenerate the Concierge with awareness of all current agents.
                  </div>
                </div>
                <Button
                  onClick={handleRegenerateConcierge}
                  disabled={isRegenerating}
                  className="bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600"
                >
                  {isRegenerating ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="mr-2 h-4 w-4" />
                  )}
                  Update
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* New Client Setup */}
          <Card className="border-0 shadow-lg border-l-4 border-l-amber-500">
            <CardHeader className="bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-950/30 dark:to-orange-950/30">
              <CardTitle className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 text-white">
                  <AlertTriangle className="h-4 w-4" />
                </div>
                New Client Setup
              </CardTitle>
              <CardDescription className="text-amber-600 dark:text-amber-500">
                Reset the system for a new client deployment. This will DELETE all existing agents and knowledge bases.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Client Name *</label>
                  <Input
                    value={clientName}
                    onChange={(e) => setClientName(e.target.value)}
                    placeholder="e.g., Cleveland Production"
                    className="bg-muted/50"
                  />
                  <p className="text-xs text-muted-foreground">
                    Internal name for this deployment
                  </p>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Organization *</label>
                  <Input
                    value={organization}
                    onChange={(e) => setOrganization(e.target.value)}
                    placeholder="e.g., City of Cleveland"
                    className="bg-muted/50"
                  />
                  <p className="text-xs text-muted-foreground">
                    Displayed to end users
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Description</label>
                <Textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional description of this deployment..."
                  rows={2}
                  className="bg-muted/50"
                />
              </div>

              <Separator />

              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button
                    variant="destructive"
                    disabled={!clientName.trim() || !organization.trim() || isResetting}
                    className="w-full bg-gradient-to-r from-red-500 to-rose-500 hover:from-red-600 hover:to-rose-600"
                  >
                    {isResetting ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="mr-2 h-4 w-4" />
                    )}
                    Reset System for New Client
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle className="flex items-center gap-2">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-100 dark:bg-red-900">
                        <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400" />
                      </div>
                      Confirm System Reset
                    </AlertDialogTitle>
                    <AlertDialogDescription className="space-y-2">
                      <p>This action will permanently delete:</p>
                      <ul className="list-disc list-inside space-y-1 text-sm">
                        <li><strong>{agentCount} agents</strong> and their configurations</li>
                        <li><strong>All knowledge base documents</strong></li>
                        <li><strong>All vector embeddings</strong></li>
                      </ul>
                      <p className="pt-2">
                        A fresh Concierge will be created for <strong>{organization || "the new client"}</strong>.
                      </p>
                      <p className="font-medium text-destructive pt-2">
                        This cannot be undone.
                      </p>
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={handleReset}
                      className="bg-gradient-to-r from-red-500 to-rose-500 hover:from-red-600 hover:to-rose-600"
                    >
                      Yes, Reset Everything
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>

              <div className="flex items-start gap-2 text-sm text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 p-3 rounded-lg">
                <CheckCircle2 className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <span>
                  After reset, a new AI Concierge will be automatically created.
                  Add your agents and the Concierge will learn about them.
                </span>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* API Keys Tab */}
        <TabsContent value="api" className="space-y-6">
          <Card className="border-0 shadow-lg">
            <CardHeader className="border-b bg-muted/30">
              <CardTitle className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 text-white">
                  <Cloud className="h-4 w-4" />
                </div>
                LLM Provider
              </CardTitle>
              <CardDescription>
                Select and configure your AI provider
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6 space-y-6">
              <div className="grid gap-3 sm:grid-cols-3">
                {(Object.keys(providerConfigs) as Array<keyof typeof providerConfigs>).map((key) => {
                  const cfg = providerConfigs[key];
                  const isSelected = provider === key;
                  return (
                    <button
                      key={key}
                      onClick={() => setProvider(key)}
                      className={`relative overflow-hidden rounded-xl p-4 text-left transition-all ${
                        isSelected
                          ? `bg-gradient-to-br ${cfg.gradient} text-white shadow-lg scale-[1.02]`
                          : `${cfg.bg} ${cfg.text} hover:scale-[1.01]`
                      }`}
                    >
                      <div className="absolute right-0 top-0 h-16 w-16 translate-x-4 -translate-y-4 rounded-full bg-white/10"></div>
                      <div className="relative">
                        <div className="font-semibold">{cfg.name}</div>
                        <div className={`text-sm ${isSelected ? "text-white/70" : "opacity-70"}`}>
                          {key === "openai" && "GPT-4o, GPT-4"}
                          {key === "anthropic" && "Claude 3.5, Claude 3"}
                          {key === "local" && "Ollama, LM Studio"}
                        </div>
                      </div>
                      {isSelected && (
                        <div className="absolute top-2 right-2">
                          <CheckCircle2 className="h-5 w-5" />
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>

              <Separator />

              <div className="space-y-4 p-4 rounded-xl bg-muted/50">
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center gap-2">
                    <Key className="h-4 w-4 text-primary" />
                    {provider === "openai"
                      ? "OpenAI API Key"
                      : provider === "anthropic"
                      ? "Anthropic API Key"
                      : "Ollama Endpoint"}
                    {llmConfig?.api_key_set && provider !== "local" && (
                      <Badge className="bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 border-0">
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                        Configured
                      </Badge>
                    )}
                  </label>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Input
                        type={showApiKey ? "text" : "password"}
                        placeholder={
                          provider === "local"
                            ? "http://localhost:11434"
                            : llmConfig?.api_key_set
                            ? "••••••••••••••••"
                            : "sk-..."
                        }
                        value={provider === "local" ? endpointUrl : apiKeyInput}
                        onChange={(e) =>
                          provider === "local"
                            ? setEndpointUrl(e.target.value)
                            : setApiKeyInput(e.target.value)
                        }
                        className="bg-background"
                      />
                      <Button
                        variant="ghost"
                        size="icon"
                        className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
                        onClick={() => setShowApiKey(!showApiKey)}
                      >
                        {showApiKey ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                    <Button
                      className={`bg-gradient-to-r ${currentProviderConfig.gradient}`}
                      onClick={handleSaveLLMConfig}
                      disabled={isSavingLLM}
                    >
                      {isSavingLLM ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <Save className="mr-2 h-4 w-4" />
                      )}
                      Save
                    </Button>
                  </div>
                </div>
                {provider !== "local" && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium flex items-center gap-2">
                      <Cpu className="h-4 w-4 text-primary" />
                      Default Model
                    </label>
                    <Input
                      placeholder={
                        provider === "openai" ? "gpt-4o" : "claude-sonnet-4-20250514"
                      }
                      value={defaultModel}
                      onChange={(e) => setDefaultModel(e.target.value)}
                      className="bg-background"
                    />
                  </div>
                )}
                {provider === "local" && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium flex items-center gap-2">
                      <Cpu className="h-4 w-4 text-primary" />
                      Model Name
                    </label>
                    <Input
                      placeholder="llama3"
                      value={defaultModel}
                      onChange={(e) => setDefaultModel(e.target.value)}
                      className="bg-background"
                    />
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-lg">
            <CardHeader className="border-b bg-muted/30">
              <CardTitle className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500 to-blue-500 text-white">
                  <Database className="h-4 w-4" />
                </div>
                API Usage
              </CardTitle>
              <CardDescription>Last 30 days usage statistics</CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-green-50 to-emerald-100 dark:from-green-950/50 dark:to-emerald-900/30 p-4">
                  <div className="absolute right-0 top-0 h-16 w-16 translate-x-4 -translate-y-4 rounded-full bg-green-500/20"></div>
                  <div className="relative">
                    <div className="text-3xl font-bold text-green-700 dark:text-green-300">
                      ${llmUsage?.total_cost_usd?.toFixed(2) ?? "0.00"}
                    </div>
                    <div className="text-sm text-green-600/70 dark:text-green-400">Total spend (30 days)</div>
                  </div>
                </div>
                <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-purple-50 to-violet-100 dark:from-purple-950/50 dark:to-violet-900/30 p-4">
                  <div className="absolute right-0 top-0 h-16 w-16 translate-x-4 -translate-y-4 rounded-full bg-purple-500/20"></div>
                  <div className="relative">
                    <div className="text-3xl font-bold text-purple-700 dark:text-purple-300">
                      {llmUsage?.total_tokens
                        ? llmUsage.total_tokens >= 1000000
                          ? `${(llmUsage.total_tokens / 1000000).toFixed(1)}M`
                          : llmUsage.total_tokens >= 1000
                          ? `${(llmUsage.total_tokens / 1000).toFixed(1)}K`
                          : llmUsage.total_tokens.toLocaleString()
                        : "0"}
                    </div>
                    <div className="text-sm text-purple-600/70 dark:text-purple-400">Tokens used</div>
                  </div>
                </div>
                <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-blue-950/50 dark:to-indigo-900/30 p-4">
                  <div className="absolute right-0 top-0 h-16 w-16 translate-x-4 -translate-y-4 rounded-full bg-blue-500/20"></div>
                  <div className="relative">
                    <div className="text-3xl font-bold text-blue-700 dark:text-blue-300">
                      {llmUsage?.total_queries?.toLocaleString() ?? "0"}
                    </div>
                    <div className="text-sm text-blue-600/70 dark:text-blue-400">API calls</div>
                  </div>
                </div>
              </div>
              {llmUsage && llmUsage.avg_cost_per_query > 0 && (
                <div className="mt-4 p-3 rounded-lg bg-muted/50 text-sm text-muted-foreground">
                  <span className="font-medium">Avg cost per query:</span> ${llmUsage.avg_cost_per_query.toFixed(4)} |{" "}
                  <span className="font-medium">Avg tokens:</span> {llmUsage.avg_tokens_per_query.toFixed(0)}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Governance Tab */}
        <TabsContent value="governance" className="space-y-6">
          <GovernanceTab />
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications" className="space-y-6">
          <Card className="border-0 shadow-lg">
            <CardHeader className="border-b bg-muted/30">
              <CardTitle className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 text-white">
                  <BellRing className="h-4 w-4" />
                </div>
                Notification Preferences
              </CardTitle>
              <CardDescription>
                Configure how you receive alerts and updates
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              {/* Global Toggle */}
              <div className="flex items-center justify-between p-4 rounded-xl bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-950/30 dark:to-orange-950/30">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100 dark:bg-amber-900">
                    <Bell className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                  </div>
                  <div>
                    <div className="font-medium">All Notifications</div>
                    <div className="text-sm text-muted-foreground">
                      Master toggle for all notification types
                    </div>
                  </div>
                </div>
                <Switch
                  checked={notificationPrefs?.enabled ?? true}
                  onCheckedChange={() => handleToggleNotification("enabled")}
                  disabled={isSavingNotifs}
                />
              </div>

              <Separator />

              {/* Individual notification types */}
              {[
                {
                  key: "escalation_alerts" as const,
                  title: "Escalation Alerts",
                  description: "Get notified when requests are escalated for review",
                  icon: AlertTriangle,
                  iconColor: "text-amber-500",
                },
                {
                  key: "draft_pending" as const,
                  title: "Draft Pending",
                  description: "Notifications for drafts awaiting approval",
                  icon: FileText,
                  iconColor: "text-blue-500",
                },
                {
                  key: "policy_changes" as const,
                  title: "Policy Changes",
                  description: "Alerts when governance policies are modified",
                  icon: Shield,
                  iconColor: "text-purple-500",
                },
                {
                  key: "sla_warnings" as const,
                  title: "SLA Warnings",
                  description: "Alerts when approval requests approach SLA deadlines",
                  icon: Zap,
                  iconColor: "text-red-500",
                },
                {
                  key: "weekly_summary" as const,
                  title: "Weekly Summary",
                  description: "Weekly digest of AI activity and metrics",
                  icon: Mail,
                  iconColor: "text-slate-500",
                },
              ].map((item) => {
                const prefs = notificationPrefs?.[item.key];
                const hasAnyEnabled = prefs ? (prefs.email || prefs.push || prefs.in_app) : false;
                const channelBadge = prefs
                  ? [prefs.email && "Email", prefs.push && "Push", prefs.in_app && "In-App"]
                      .filter(Boolean)
                      .join(" + ") || "Disabled"
                  : "Loading...";
                const badgeColor = hasAnyEnabled
                  ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                  : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400";

                return (
                  <div
                    key={item.key}
                    className={`flex items-center justify-between p-4 rounded-xl ${
                      hasAnyEnabled ? "bg-muted/30" : "bg-muted/10"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                        <item.icon className={`h-5 w-5 ${item.iconColor}`} />
                      </div>
                      <div>
                        <div className="font-medium">{item.title}</div>
                        <div className="text-sm text-muted-foreground">{item.description}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge className={`${badgeColor} border-0`}>{channelBadge}</Badge>
                      <div className="flex gap-1">
                        <Button
                          variant={prefs?.email ? "default" : "outline"}
                          size="sm"
                          className="h-7 px-2 text-xs"
                          onClick={() => handleToggleNotification(item.key, "email")}
                          disabled={isSavingNotifs || !notificationPrefs?.enabled}
                        >
                          <Mail className="h-3 w-3" />
                        </Button>
                        <Button
                          variant={prefs?.push ? "default" : "outline"}
                          size="sm"
                          className="h-7 px-2 text-xs"
                          onClick={() => handleToggleNotification(item.key, "push")}
                          disabled={isSavingNotifs || !notificationPrefs?.enabled}
                        >
                          <Bell className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Branding Tab */}
        <TabsContent value="branding" className="space-y-6">
          <BrandingTab />
        </TabsContent>

        {/* Shared Canon Tab */}
        <TabsContent value="canon" className="space-y-6">
          <CanonTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// =============================================================================
// Governance Tab Component
// =============================================================================

function GovernanceTab() {
  const [summary, setSummary] = useState<GovernanceSummary | null>(null);
  const [versions, setVersions] = useState<PolicyVersion[]>([]);
  const [pendingChanges, setPendingChanges] = useState<PolicyChange[]>([]);
  const [driftReport, setDriftReport] = useState<DriftReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<PolicyVersion | null>(null);

  useEffect(() => {
    loadGovernanceData();
  }, []);

  async function loadGovernanceData() {
    try {
      setLoading(true);
      const [summaryData, versionsData, pendingData, driftData] = await Promise.all([
        getGovernanceSummary(),
        getGovernanceVersions(20),
        getPendingPolicyChanges(),
        getDriftReport(),
      ]);
      setSummary(summaryData);
      setVersions(versionsData.versions);
      setPendingChanges(pendingData.pending);
      setDriftReport(driftData);
    } catch (error) {
      console.error("Failed to load governance data:", error);
      toast.error("Failed to load governance data");
    } finally {
      setLoading(false);
    }
  }

  async function handleSync() {
    setSyncing(true);
    try {
      await syncPoliciesFromFile();
      toast.success("Policies synced from file");
      loadGovernanceData();
    } catch (error) {
      toast.error("Failed to sync policies");
    } finally {
      setSyncing(false);
    }
  }

  async function handleRollback(versionId: string) {
    try {
      await rollbackToVersion(versionId, "admin");
      toast.success("Rolled back to previous version");
      setSelectedVersion(null);
      loadGovernanceData();
    } catch (error) {
      toast.error("Failed to rollback");
    }
  }

  async function handleApproveChange(changeId: string) {
    try {
      await approvePolicyChange(changeId, "admin");
      toast.success("Change approved and applied");
      loadGovernanceData();
    } catch (error) {
      toast.error("Failed to approve change");
    }
  }

  async function handleRejectChange(changeId: string) {
    try {
      await rejectPolicyChange(changeId, "admin");
      toast.success("Change rejected");
      loadGovernanceData();
    } catch (error) {
      toast.error("Failed to reject change");
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Governance Summary */}
      <Card className="border-0 shadow-lg">
        <CardHeader className="border-b bg-muted/30">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500 text-white">
                  <Shield className="h-4 w-4" />
                </div>
                Governance Status
              </CardTitle>
              <CardDescription>
                Policy versioning, approval workflow, and drift detection
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={loadGovernanceData}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-6">
          {summary && (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border bg-muted/30 p-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <GitBranch className="h-4 w-4" />
                  Version
                </div>
                <p className="text-2xl font-bold mt-1">v{summary.version}</p>
                <p className="text-xs text-muted-foreground font-mono">{summary.policy_hash}</p>
              </div>
              <div className="rounded-lg border bg-muted/30 p-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Shield className="h-4 w-4" />
                  Rules
                </div>
                <p className="text-2xl font-bold mt-1">{summary.rules.constitutional + summary.rules.organization + summary.rules.department}</p>
                <p className="text-xs text-muted-foreground">
                  {summary.rules.constitutional} constitutional, {summary.rules.organization} org
                </p>
              </div>
              <div className="rounded-lg border bg-muted/30 p-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Lock className="h-4 w-4" />
                  Immutable
                </div>
                <p className="text-2xl font-bold mt-1">{summary.immutable_rules}</p>
                <p className="text-xs text-muted-foreground">Protected rules</p>
              </div>
              <div className="rounded-lg border bg-muted/30 p-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  {driftReport?.overall_status === "ok" ? (
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-amber-500" />
                  )}
                  Drift Status
                </div>
                <p className={`text-2xl font-bold mt-1 ${driftReport?.overall_status === "ok" ? "text-green-600" : "text-amber-600"}`}>
                  {driftReport?.overall_status === "ok" ? "Synced" : "Drift Detected"}
                </p>
                {driftReport?.overall_status !== "ok" && (
                  <Button size="sm" variant="outline" className="mt-2" onClick={handleSync} disabled={syncing}>
                    {syncing ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <RefreshCw className="h-3 w-3 mr-1" />}
                    Sync
                  </Button>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pending Changes */}
      {pendingChanges.length > 0 && (
        <Card className="border-0 shadow-lg border-l-4 border-l-amber-500">
          <CardHeader className="border-b bg-amber-50 dark:bg-amber-950/30">
            <CardTitle className="flex items-center gap-2 text-amber-700 dark:text-amber-300">
              <AlertCircle className="h-5 w-5" />
              Pending Policy Changes ({pendingChanges.length})
            </CardTitle>
            <CardDescription>
              These changes require approval before being applied
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/30">
                  <TableHead>Change</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Proposed By</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pendingChanges.map((change) => (
                  <TableRow key={change.change_id}>
                    <TableCell className="font-medium">{change.description}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{change.change_type}</Badge>
                    </TableCell>
                    <TableCell>{change.proposed_by}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(change.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right space-x-2">
                      <Button
                        size="sm"
                        className="bg-gradient-to-r from-green-500 to-emerald-500"
                        onClick={() => handleApproveChange(change.change_id)}
                      >
                        Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-red-600 border-red-300 hover:bg-red-50"
                        onClick={() => handleRejectChange(change.change_id)}
                      >
                        Reject
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Version History */}
      <Card className="border-0 shadow-lg">
        <CardHeader className="border-b bg-muted/30">
          <CardTitle className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 text-white">
              <History className="h-4 w-4" />
            </div>
            Version History
          </CardTitle>
          <CardDescription>
            Track policy changes and rollback if needed
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea className="h-[300px]">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/30">
                  <TableHead>Version</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Changed By</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {versions.map((version, index) => (
                  <TableRow key={version.version_id}>
                    <TableCell>
                      <Badge className={index === 0 ? "bg-green-100 text-green-700 border-0" : "bg-muted"}>
                        v{version.version_number}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-medium max-w-xs truncate">
                      {version.change_description}
                    </TableCell>
                    <TableCell>{version.created_by}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(version.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      {index > 0 && (
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button size="sm" variant="outline">
                              <RotateCcw className="h-3 w-3 mr-1" />
                              Rollback
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Rollback to v{version.version_number}?</AlertDialogTitle>
                              <AlertDialogDescription>
                                This will revert all policies to the state from "{version.change_description}".
                                A new version will be created to track this rollback.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction
                                onClick={() => handleRollback(version.version_id)}
                                className="bg-gradient-to-r from-amber-500 to-orange-500"
                              >
                                Rollback
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      )}
                      {index === 0 && (
                        <Badge className="bg-green-100 text-green-700 border-0">Current</Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                {versions.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                      No version history yet
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Approval Settings */}
      <Card className="border-0 shadow-lg">
        <CardHeader className="border-b bg-muted/30">
          <CardTitle className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 text-white">
              <FileCheck className="h-4 w-4" />
            </div>
            Approval Settings
          </CardTitle>
          <CardDescription>
            Configure policy change approval requirements
          </CardDescription>
        </CardHeader>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Require Approval for Policy Changes</p>
              <p className="text-sm text-muted-foreground">
                When enabled, policy changes must be approved before taking effect
              </p>
            </div>
            <Switch checked={summary?.require_approval ?? true} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// =============================================================================
// Branding Tab Component
// =============================================================================

function BrandingTab() {
  const [branding, setBranding] = useState<BrandingSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  // Form state
  const [appName, setAppName] = useState("");
  const [tagline, setTagline] = useState("");
  const [organization, setOrganization] = useState("");
  const [supportEmail, setSupportEmail] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [faviconUrl, setFaviconUrl] = useState("");

  useEffect(() => {
    loadBranding();
  }, []);

  async function loadBranding() {
    try {
      setLoading(true);
      const data = await getBranding();
      setBranding(data);
      setAppName(data.app_name || "");
      setTagline(data.tagline || "");
      setOrganization(data.organization || "");
      setSupportEmail(data.support_email || "");
      setLogoUrl(data.logo_url || "");
      setFaviconUrl(data.favicon_url || "");
    } catch (error) {
      console.error("Failed to load branding:", error);
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveBranding() {
    setSaving(true);
    try {
      await updateBranding({
        app_name: appName,
        tagline,
        organization,
        support_email: supportEmail,
        logo_url: logoUrl,
        favicon_url: faviconUrl,
      });
      toast.success("Branding settings saved");
      loadBranding();
    } catch (error) {
      toast.error("Failed to save branding settings");
    } finally {
      setSaving(false);
    }
  }

  async function handleFileUpload(file: File) {
    // Validate file type
    const validTypes = ["image/png", "image/jpeg", "image/svg+xml", "image/webp"];
    if (!validTypes.includes(file.type)) {
      toast.error("Invalid file type. Please upload PNG, JPG, SVG, or WebP");
      return;
    }

    // Validate file size (2MB)
    if (file.size > 2 * 1024 * 1024) {
      toast.error("File too large. Maximum size is 2MB");
      return;
    }

    setUploading(true);
    try {
      const result = await uploadLogo(file);
      setLogoUrl(result.url);
      toast.success("Logo uploaded successfully");
      loadBranding();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Upload failed";
      toast.error(message);
    } finally {
      setUploading(false);
    }
  }

  async function handleDeleteLogo() {
    try {
      await deleteLogo();
      setLogoUrl("");
      toast.success("Logo deleted");
      loadBranding();
    } catch (error) {
      toast.error("Failed to delete logo");
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileUpload(file);
    }
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(true);
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const currentLogoUrl = branding?.logo_url ? getLogoUrl(branding.logo_url) : "";

  return (
    <div className="space-y-6">
      <Card className="border-0 shadow-lg">
        <CardHeader className="border-b bg-muted/30">
          <CardTitle className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-pink-500 to-rose-500 text-white">
              <ImageIcon className="h-4 w-4" />
            </div>
            Organization Logo
          </CardTitle>
          <CardDescription>
            Upload your organization's logo to personalize the dashboard
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6 space-y-6">
          <div className="grid gap-6 sm:grid-cols-2">
            {/* Current Logo Preview */}
            <div className="space-y-4">
              <p className="text-sm font-medium">Current Logo</p>
              <div className="flex items-center justify-center h-32 rounded-xl border-2 border-dashed border-muted-foreground/25 bg-muted/30 relative">
                {currentLogoUrl ? (
                  <>
                    <img
                      src={currentLogoUrl}
                      alt="Organization logo"
                      className="max-h-24 max-w-full object-contain"
                    />
                    <Button
                      variant="destructive"
                      size="icon"
                      className="absolute top-2 right-2 h-6 w-6"
                      onClick={handleDeleteLogo}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </>
                ) : (
                  <div className="text-center">
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 text-white mx-auto mb-2">
                      <Sparkles className="h-6 w-6" />
                    </div>
                    <p className="text-xs text-muted-foreground">Using default icon</p>
                  </div>
                )}
              </div>
            </div>

            {/* Upload Area */}
            <div className="space-y-4">
              <p className="text-sm font-medium">Upload New Logo</p>
              <label
                className={`flex flex-col items-center justify-center h-32 rounded-xl border-2 border-dashed transition-colors cursor-pointer ${
                  dragOver
                    ? "border-pink-500 bg-pink-100 dark:bg-pink-950/50"
                    : "border-pink-200 dark:border-pink-800 bg-pink-50/50 dark:bg-pink-950/20 hover:bg-pink-100/50 dark:hover:bg-pink-950/30"
                }`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
              >
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/svg+xml,image/webp"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleFileUpload(file);
                  }}
                  disabled={uploading}
                />
                {uploading ? (
                  <Loader2 className="h-8 w-8 text-pink-500 animate-spin" />
                ) : (
                  <>
                    <Upload className="h-8 w-8 text-pink-400 mb-2" />
                    <p className="text-sm text-muted-foreground">Click to upload or drag and drop</p>
                    <p className="text-xs text-muted-foreground">PNG, JPG, SVG, WebP (max 2MB)</p>
                  </>
                )}
              </label>
            </div>
          </div>

          <Separator />

          <div className="space-y-2">
            <label className="text-sm font-medium">Logo URL (Alternative)</label>
            <div className="flex gap-2">
              <Input
                placeholder="https://example.com/logo.png"
                value={logoUrl}
                onChange={(e) => setLogoUrl(e.target.value)}
                className="bg-muted/50"
              />
              <Button
                onClick={handleSaveBranding}
                disabled={saving}
                className="bg-gradient-to-r from-pink-500 to-rose-500 hover:from-pink-600 hover:to-rose-600"
              >
                {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                Save
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Enter a direct URL to your logo if you prefer not to upload
            </p>
          </div>
        </CardContent>
      </Card>

      <Card className="border-0 shadow-lg">
        <CardHeader className="border-b bg-muted/30">
          <CardTitle className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-purple-500 text-white">
              <Palette className="h-4 w-4" />
            </div>
            Brand Settings
          </CardTitle>
          <CardDescription>
            Customize the look and feel of your deployment
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">Application Name</label>
              <Input
                placeholder="e.g., Cleveland AI Gateway"
                value={appName}
                onChange={(e) => setAppName(e.target.value)}
                className="bg-muted/50"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Tagline</label>
              <Input
                placeholder="e.g., City Employee Support"
                value={tagline}
                onChange={(e) => setTagline(e.target.value)}
                className="bg-muted/50"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Organization Name</label>
              <Input
                placeholder="e.g., City of Cleveland"
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
                className="bg-muted/50"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Support Email</label>
              <Input
                placeholder="support@example.com"
                value={supportEmail}
                onChange={(e) => setSupportEmail(e.target.value)}
                className="bg-muted/50"
              />
            </div>
          </div>

          <Separator />

          <div className="space-y-2">
            <label className="text-sm font-medium">Favicon URL</label>
            <Input
              placeholder="https://example.com/favicon.ico"
              value={faviconUrl}
              onChange={(e) => setFaviconUrl(e.target.value)}
              className="bg-muted/50"
            />
            <p className="text-xs text-muted-foreground">
              Custom favicon shown in browser tabs
            </p>
          </div>

          <div className="flex justify-end">
            <Button
              onClick={handleSaveBranding}
              disabled={saving}
              className="bg-gradient-to-r from-violet-500 to-purple-500 hover:from-violet-600 hover:to-purple-600"
            >
              {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
              Save Brand Settings
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-0 shadow-lg">
        <CardHeader className="border-b bg-muted/30">
          <CardTitle className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 text-white">
              <Building2 className="h-4 w-4" />
            </div>
            Agent Branding
          </CardTitle>
          <CardDescription>
            Customize logos and avatars for individual agents
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="text-center py-8 text-muted-foreground">
            <ImageIcon className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">
              Agent avatars and logos can be configured in the{" "}
              <a href="/agents" className="text-primary hover:underline">
                Agents
              </a>{" "}
              section
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// =============================================================================
// Canon Tab Component (Shared Knowledge Base)
// =============================================================================

function CanonTab() {
  const [stats, setStats] = useState<CanonStats | null>(null);
  const [documents, setDocuments] = useState<CanonDocument[]>([]);
  const [webSources, setWebSources] = useState<CanonWebSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [addingUrl, setAddingUrl] = useState(false);
  const [newUrl, setNewUrl] = useState("");
  const [newUrlName, setNewUrlName] = useState("");

  useEffect(() => {
    loadCanonData();
  }, []);

  async function loadCanonData() {
    try {
      setLoading(true);
      const [statsData, docsData, sourcesData] = await Promise.all([
        getCanonStats(),
        listCanonDocuments(),
        listCanonWebSources(),
      ]);
      setStats(statsData);
      setDocuments(docsData.documents);
      setWebSources(sourcesData.sources);
    } catch (error) {
      console.error("Failed to load canon data:", error);
      toast.error("Failed to load canon data");
    } finally {
      setLoading(false);
    }
  }

  async function handleFileUpload(file: File) {
    setUploading(true);
    try {
      const result = await uploadCanonDocument(file);
      toast.success(result.message);
      loadCanonData();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Upload failed";
      toast.error(message);
    } finally {
      setUploading(false);
    }
  }

  async function handleAddWebSource() {
    if (!newUrl.trim()) {
      toast.error("Please enter a URL");
      return;
    }

    setAddingUrl(true);
    try {
      const result = await addCanonWebSource({
        url: newUrl.trim(),
        name: newUrlName.trim() || undefined,
      });
      toast.success(result.message);
      setNewUrl("");
      setNewUrlName("");
      loadCanonData();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to add web source";
      toast.error(message);
    } finally {
      setAddingUrl(false);
    }
  }

  async function handleDeleteDocument(docId: string) {
    try {
      await deleteCanonDocument(docId);
      toast.success("Document deleted from canon");
      loadCanonData();
    } catch (error) {
      toast.error("Failed to delete document");
    }
  }

  async function handleDeleteWebSource(sourceId: string) {
    try {
      await deleteCanonWebSource(sourceId);
      toast.success("Web source deleted from canon");
      loadCanonData();
    } catch (error) {
      toast.error("Failed to delete web source");
    }
  }

  async function handleRefreshWebSource(sourceId: string) {
    try {
      const result = await refreshCanonWebSource(sourceId);
      toast.success(result.message);
      loadCanonData();
    } catch (error) {
      toast.error("Failed to refresh web source");
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileUpload(file);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Canon Overview */}
      <Card className="border-0 shadow-lg">
        <CardHeader className="border-b bg-muted/30">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500 to-teal-500 text-white">
                  <Database className="h-4 w-4" />
                </div>
                Shared Canon
              </CardTitle>
              <CardDescription>
                Organization-wide knowledge accessible to ALL agents. Add policies, FAQs, and public information here.
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={loadCanonData}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-6">
          {stats && (
            <div className="grid gap-4 md:grid-cols-4">
              <div className="rounded-lg border bg-muted/30 p-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <FileText className="h-4 w-4" />
                  Documents
                </div>
                <p className="text-2xl font-bold mt-1">{stats.document_count}</p>
                <p className="text-xs text-muted-foreground">{stats.total_document_chunks} chunks</p>
              </div>
              <div className="rounded-lg border bg-muted/30 p-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Cloud className="h-4 w-4" />
                  Web Sources
                </div>
                <p className="text-2xl font-bold mt-1">{stats.web_source_count}</p>
                <p className="text-xs text-muted-foreground">{stats.total_web_chunks} chunks</p>
              </div>
              <div className="rounded-lg border bg-muted/30 p-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Zap className="h-4 w-4" />
                  Total Chunks
                </div>
                <p className="text-2xl font-bold mt-1">{stats.total_chunks}</p>
                <p className="text-xs text-muted-foreground">searchable segments</p>
              </div>
              <div className="rounded-lg border bg-gradient-to-br from-cyan-50 to-teal-50 dark:from-cyan-950/30 dark:to-teal-950/30 p-4">
                <div className="flex items-center gap-2 text-sm text-cyan-600 dark:text-cyan-400">
                  <CheckCircle2 className="h-4 w-4" />
                  Coverage
                </div>
                <p className="text-2xl font-bold mt-1 text-cyan-700 dark:text-cyan-300">All Agents</p>
                <p className="text-xs text-cyan-600/70 dark:text-cyan-400/70">have access</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Upload Documents */}
      <Card className="border-0 shadow-lg">
        <CardHeader className="border-b bg-muted/30">
          <CardTitle className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500 text-white">
              <Upload className="h-4 w-4" />
            </div>
            Add Documents
          </CardTitle>
          <CardDescription>
            Upload documents that ALL agents should know about
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6 space-y-4">
          <label
            className={`flex flex-col items-center justify-center h-32 rounded-xl border-2 border-dashed transition-colors cursor-pointer ${
              dragOver
                ? "border-cyan-500 bg-cyan-100 dark:bg-cyan-950/50"
                : "border-cyan-200 dark:border-cyan-800 bg-cyan-50/50 dark:bg-cyan-950/20 hover:bg-cyan-100/50 dark:hover:bg-cyan-950/30"
            }`}
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={(e) => { e.preventDefault(); setDragOver(false); }}
          >
            <input
              type="file"
              accept=".txt,.pdf,.docx,.doc"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFileUpload(file);
              }}
              disabled={uploading}
            />
            {uploading ? (
              <Loader2 className="h-8 w-8 text-cyan-500 animate-spin" />
            ) : (
              <>
                <Upload className="h-8 w-8 text-cyan-400 mb-2" />
                <p className="text-sm text-muted-foreground">Drop files here or click to upload</p>
                <p className="text-xs text-muted-foreground">PDF, DOCX, TXT</p>
              </>
            )}
          </label>

          {/* Document List */}
          {documents.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium">Canon Documents</p>
              <div className="space-y-2">
                {documents.map((doc) => (
                  <div key={doc.id} className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                    <div className="flex items-center gap-3">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <p className="font-medium text-sm">{doc.filename}</p>
                        <p className="text-xs text-muted-foreground">{doc.chunk_count} chunks • {(doc.file_size / 1024).toFixed(1)}KB</p>
                      </div>
                    </div>
                    <Button variant="ghost" size="icon" onClick={() => handleDeleteDocument(doc.id)}>
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Web Sources */}
      <Card className="border-0 shadow-lg">
        <CardHeader className="border-b bg-muted/30">
          <CardTitle className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 text-white">
              <Cloud className="h-4 w-4" />
            </div>
            Web Sources
          </CardTitle>
          <CardDescription>
            Add your organization's website, policy pages, or public information URLs
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6 space-y-4">
          {/* Add URL Form */}
          <div className="flex gap-2">
            <Input
              placeholder="https://example.com/policies"
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              className="flex-1 bg-muted/50"
            />
            <Input
              placeholder="Name (optional)"
              value={newUrlName}
              onChange={(e) => setNewUrlName(e.target.value)}
              className="w-48 bg-muted/50"
            />
            <Button
              onClick={handleAddWebSource}
              disabled={addingUrl || !newUrl.trim()}
              className="bg-gradient-to-r from-purple-500 to-pink-500"
            >
              {addingUrl ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            </Button>
          </div>

          {/* Web Sources List */}
          {webSources.length > 0 && (
            <div className="space-y-2">
              {webSources.map((source) => (
                <div key={source.id} className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <Cloud className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="font-medium text-sm truncate">{source.name}</p>
                      <p className="text-xs text-muted-foreground truncate">{source.url}</p>
                      <p className="text-xs text-muted-foreground">{source.chunk_count} chunks • {source.last_refresh_status}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <Button variant="ghost" size="icon" onClick={() => handleRefreshWebSource(source.id)}>
                      <RefreshCw className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => handleDeleteWebSource(source.id)}>
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {webSources.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <Cloud className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p className="text-sm">No web sources yet</p>
              <p className="text-xs">Add your organization's website to populate the shared canon</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="border-0 shadow-lg border-l-4 border-l-cyan-500">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-100 dark:bg-cyan-900 flex-shrink-0">
              <CheckCircle2 className="h-4 w-4 text-cyan-600 dark:text-cyan-400" />
            </div>
            <div>
              <p className="font-medium text-cyan-700 dark:text-cyan-300">How the Shared Canon Works</p>
              <p className="text-sm text-muted-foreground mt-1">
                When any agent receives a query, it automatically searches both its own knowledge base AND the shared canon.
                This ensures consistent answers across all agents without duplicate uploads.
              </p>
              <ul className="text-sm text-muted-foreground mt-2 list-disc list-inside space-y-1">
                <li>Upload documents once, available to all agents</li>
                <li>Add your organization's website for consistent information</li>
                <li>Results are merged and ranked by relevance</li>
                <li>Citations show whether info came from canon or agent-specific knowledge</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
