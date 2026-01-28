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
import { resetForNewClient, regenerateConcierge, listAgents } from "@/lib/api";
import { config } from "@/lib/config";

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

  // Load current agent count
  useEffect(() => {
    loadAgentCount();
  }, []);

  async function loadAgentCount() {
    try {
      const data = await listAgents();
      setAgentCount(data.total);
    } catch (error) {
      console.error("Failed to load agents:", error);
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
                  </label>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Input
                        type={showApiKey ? "text" : "password"}
                        placeholder={
                          provider === "local"
                            ? "http://localhost:11434"
                            : "sk-..."
                        }
                        defaultValue={
                          provider === "local" ? "http://localhost:11434" : ""
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
                    <Button className={`bg-gradient-to-r ${currentProviderConfig.gradient}`}>
                      <Save className="mr-2 h-4 w-4" />
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
                      defaultValue={
                        provider === "openai" ? "gpt-4o" : "claude-sonnet-4-20250514"
                      }
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
              <CardDescription>Current billing period usage</CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-green-50 to-emerald-100 dark:from-green-950/50 dark:to-emerald-900/30 p-4">
                  <div className="absolute right-0 top-0 h-16 w-16 translate-x-4 -translate-y-4 rounded-full bg-green-500/20"></div>
                  <div className="relative">
                    <div className="text-3xl font-bold text-green-700 dark:text-green-300">$47.82</div>
                    <div className="text-sm text-green-600/70 dark:text-green-400">Total spend this month</div>
                  </div>
                </div>
                <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-purple-50 to-violet-100 dark:from-purple-950/50 dark:to-violet-900/30 p-4">
                  <div className="absolute right-0 top-0 h-16 w-16 translate-x-4 -translate-y-4 rounded-full bg-purple-500/20"></div>
                  <div className="relative">
                    <div className="text-3xl font-bold text-purple-700 dark:text-purple-300">1.2M</div>
                    <div className="text-sm text-purple-600/70 dark:text-purple-400">Tokens used</div>
                  </div>
                </div>
                <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-blue-950/50 dark:to-indigo-900/30 p-4">
                  <div className="absolute right-0 top-0 h-16 w-16 translate-x-4 -translate-y-4 rounded-full bg-blue-500/20"></div>
                  <div className="relative">
                    <div className="text-3xl font-bold text-blue-700 dark:text-blue-300">2,847</div>
                    <div className="text-sm text-blue-600/70 dark:text-blue-400">API calls</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Governance Tab */}
        <TabsContent value="governance" className="space-y-6">
          <Card className="border-0 shadow-lg">
            <CardHeader className="border-b bg-muted/30 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500 text-white">
                    <Shield className="h-4 w-4" />
                  </div>
                  Governance Policies
                </CardTitle>
                <CardDescription>
                  Rules that control AI behavior and human oversight
                </CardDescription>
              </div>
              <Dialog>
                <DialogTrigger asChild>
                  <Button className="bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600">
                    <Plus className="mr-2 h-4 w-4" />
                    Add Policy
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create New Policy</DialogTitle>
                    <DialogDescription>
                      Define a governance rule for AI requests
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Policy Name</label>
                      <Input placeholder="e.g., External Communications Review" className="bg-muted/50" />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Trigger Condition</label>
                      <Input placeholder="e.g., domain = Comms AND audience = public" className="bg-muted/50 font-mono text-sm" />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Action</label>
                      <Input placeholder="e.g., DRAFT" className="bg-muted/50" />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline">Cancel</Button>
                    <Button className="bg-gradient-to-r from-blue-500 to-indigo-500">Create Policy</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/30">
                    <TableHead>Policy</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead className="hidden md:table-cell">Domain</TableHead>
                    <TableHead className="hidden lg:table-cell">Trigger</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead className="w-[100px]">Status</TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mockPolicies.map((policy) => (
                    <TableRow key={policy.id} className="hover:bg-muted/50">
                      <TableCell className="font-medium">{policy.name}</TableCell>
                      <TableCell>
                        <Badge
                          className={
                            policy.type === "constitutional"
                              ? "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300 border-0"
                              : "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 border-0"
                          }
                        >
                          {policy.type}
                        </Badge>
                      </TableCell>
                      <TableCell className="hidden md:table-cell">
                        <Badge variant="outline" className="bg-muted/50">{policy.domain}</Badge>
                      </TableCell>
                      <TableCell className="hidden lg:table-cell font-mono text-xs text-muted-foreground">
                        {policy.trigger}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="font-mono">{policy.action}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          className={
                            policy.enabled
                              ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 border-0"
                              : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border-0"
                          }
                        >
                          {policy.enabled ? "Active" : "Disabled"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
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
              {[
                {
                  title: "Escalation Alerts",
                  description: "Get notified when requests are escalated for review",
                  badge: "Email + Push",
                  badgeColor: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
                  icon: AlertTriangle,
                  iconColor: "text-amber-500",
                  enabled: true,
                },
                {
                  title: "Draft Pending",
                  description: "Notifications for drafts awaiting approval",
                  badge: "Push only",
                  badgeColor: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
                  icon: FileText,
                  iconColor: "text-blue-500",
                  enabled: true,
                },
                {
                  title: "Policy Changes",
                  description: "Alerts when governance policies are modified",
                  badge: "Email only",
                  badgeColor: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300",
                  icon: Shield,
                  iconColor: "text-purple-500",
                  enabled: true,
                },
                {
                  title: "Weekly Summary",
                  description: "Weekly digest of AI activity and metrics",
                  badge: "Disabled",
                  badgeColor: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
                  icon: Mail,
                  iconColor: "text-slate-400",
                  enabled: false,
                },
              ].map((item, index) => (
                <div key={index} className={`flex items-center justify-between p-4 rounded-xl ${item.enabled ? "bg-muted/30" : "bg-muted/10"}`}>
                  <div className="flex items-center gap-3">
                    <div className={`flex h-10 w-10 items-center justify-center rounded-lg bg-muted`}>
                      <item.icon className={`h-5 w-5 ${item.iconColor}`} />
                    </div>
                    <div>
                      <div className="font-medium">{item.title}</div>
                      <div className="text-sm text-muted-foreground">
                        {item.description}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge className={`${item.badgeColor} border-0`}>{item.badge}</Badge>
                    <Switch checked={item.enabled} />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Branding Tab */}
        <TabsContent value="branding" className="space-y-6">
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
                  <div className="flex items-center justify-center h-32 rounded-xl border-2 border-dashed border-muted-foreground/25 bg-muted/30">
                    {config.logoUrl ? (
                      <img
                        src={config.logoUrl}
                        alt="Organization logo"
                        className="max-h-24 max-w-full object-contain"
                      />
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
                  <div className="flex flex-col items-center justify-center h-32 rounded-xl border-2 border-dashed border-pink-200 dark:border-pink-800 bg-pink-50/50 dark:bg-pink-950/20 hover:bg-pink-100/50 dark:hover:bg-pink-950/30 transition-colors cursor-pointer">
                    <Upload className="h-8 w-8 text-pink-400 mb-2" />
                    <p className="text-sm text-muted-foreground">Click to upload or drag and drop</p>
                    <p className="text-xs text-muted-foreground">PNG, JPG, SVG (max 2MB)</p>
                  </div>
                </div>
              </div>

              <Separator />

              <div className="space-y-2">
                <label className="text-sm font-medium">Logo URL (Alternative)</label>
                <div className="flex gap-2">
                  <Input
                    placeholder="https://example.com/logo.png"
                    className="bg-muted/50"
                  />
                  <Button className="bg-gradient-to-r from-pink-500 to-rose-500 hover:from-pink-600 hover:to-rose-600">
                    <Save className="mr-2 h-4 w-4" />
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
                    defaultValue={config.appName}
                    className="bg-muted/50"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Tagline</label>
                  <Input
                    placeholder="e.g., City Employee Support"
                    defaultValue={config.tagline}
                    className="bg-muted/50"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Organization Name</label>
                  <Input
                    placeholder="e.g., City of Cleveland"
                    defaultValue={config.organization}
                    className="bg-muted/50"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Support Email</label>
                  <Input
                    placeholder="support@example.com"
                    defaultValue={config.supportEmail}
                    className="bg-muted/50"
                  />
                </div>
              </div>

              <Separator />

              <div className="space-y-2">
                <label className="text-sm font-medium">Favicon URL</label>
                <Input
                  placeholder="https://example.com/favicon.ico"
                  className="bg-muted/50"
                />
                <p className="text-xs text-muted-foreground">
                  Custom favicon shown in browser tabs
                </p>
              </div>

              <div className="flex justify-end">
                <Button className="bg-gradient-to-r from-violet-500 to-purple-500 hover:from-violet-600 hover:to-purple-600">
                  <Save className="mr-2 h-4 w-4" />
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
        </TabsContent>
      </Tabs>
    </div>
  );
}
