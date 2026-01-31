"use client";

import { useEffect, useState, useRef } from "react";
import {
  MoreVertical,
  Power,
  Settings,
  ExternalLink,
  Shield,
  Route,
  Users,
  Building2,
  Phone,
  DollarSign,
  HeartPulse,
  Lightbulb,
  Globe,
  Play,
  Upload,
  Trash2,
  FileText,
  Mic,
  MicOff,
  Loader2,
  X,
  Send,
  Bot,
  Sparkles,
  Search,
  Filter,
  RefreshCw,
  Brain,
  Cpu,
  Layers,
  MessageSquare,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  listAgents,
  updateAgent,
  enableAgent,
  disableAgent,
  deleteAgent,
  listKnowledge,
  uploadKnowledge,
  deleteKnowledge,
  getKnowledgeDownloadUrl,
  queryAgent,
  createAgent,
  listWebSources,
  addWebSource,
  refreshWebSource,
  deleteWebSource,
  regenerateConcierge,
  exportAsTemplate,
  type AgentConfig,
  type KnowledgeDocument,
  type CreateAgentRequest,
  type WebSource,
} from "@/lib/api";
import { toast } from "sonner";
import { config } from "@/lib/config";
import { Plus, AlertTriangle, CheckSquare, Square, XSquare, Globe2, Link2, Download, Save, FolderDown } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

type AgentDomain = "Router" | "Strategy" | "PublicHealth" | "HR" | "Finance" | "Building" | "311" | "Regional" | string;

const domainConfig: Record<string, { icon: React.ElementType; gradient: string; color: string }> = {
  Router: { icon: Route, gradient: "from-indigo-500 to-purple-500", color: "text-indigo-600" },
  Strategy: { icon: Lightbulb, gradient: "from-violet-500 to-purple-500", color: "text-violet-600" },
  PublicHealth: { icon: HeartPulse, gradient: "from-red-500 to-rose-500", color: "text-red-600" },
  HR: { icon: Users, gradient: "from-green-500 to-emerald-500", color: "text-green-600" },
  Finance: { icon: DollarSign, gradient: "from-cyan-500 to-blue-500", color: "text-cyan-600" },
  Building: { icon: Building2, gradient: "from-amber-500 to-orange-500", color: "text-amber-600" },
  "311": { icon: Phone, gradient: "from-blue-500 to-indigo-500", color: "text-blue-600" },
  Regional: { icon: Globe, gradient: "from-purple-500 to-pink-500", color: "text-purple-600" },
  General: { icon: Brain, gradient: "from-gray-500 to-slate-500", color: "text-gray-600" },
  Legal: { icon: Shield, gradient: "from-rose-500 to-red-500", color: "text-rose-600" },
  IT: { icon: Cpu, gradient: "from-teal-500 to-cyan-500", color: "text-teal-600" },
};

const statusConfig = {
  active: { label: "Active", color: "bg-green-500/10 text-green-600 border-green-300" },
  inactive: { label: "Inactive", color: "bg-gray-500/10 text-gray-600 border-gray-300" },
  degraded: { label: "Degraded", color: "bg-amber-500/10 text-amber-600 border-amber-300" },
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<AgentConfig | null>(null);
  const [editingAgent, setEditingAgent] = useState<AgentConfig | null>(null);
  const [testingAgent, setTestingAgent] = useState<AgentConfig | null>(null);
  const [creatingAgent, setCreatingAgent] = useState(false);
  const [knowledge, setKnowledge] = useState<KnowledgeDocument[]>([]);
  const [knowledgeLoading, setKnowledgeLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [domainFilter, setDomainFilter] = useState<string>("all");

  // Web sources state
  const [webSources, setWebSources] = useState<WebSource[]>([]);
  const [webSourcesLoading, setWebSourcesLoading] = useState(false);
  const [addingWebSource, setAddingWebSource] = useState(false);
  const [newWebSourceUrl, setNewWebSourceUrl] = useState("");
  const [newWebSourceName, setNewWebSourceName] = useState("");
  const [refreshingSource, setRefreshingSource] = useState<string | null>(null);

  // Test console state
  const [testQuery, setTestQuery] = useState("");
  const [testResponse, setTestResponse] = useState<string | null>(null);
  const [testSources, setTestSources] = useState<Array<{ text: string; metadata: Record<string, unknown> }>>([]);
  const [testLoading, setTestLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

  // Concierge regeneration state
  const [regenerating, setRegenerating] = useState(false);

  // Save as template state
  const [showSaveTemplate, setShowSaveTemplate] = useState(false);
  const [templateName, setTemplateName] = useState("");
  const [templateDescription, setTemplateDescription] = useState("");
  const [savingTemplate, setSavingTemplate] = useState(false);

  // Delete confirmation state
  const [agentToDelete, setAgentToDelete] = useState<AgentConfig | null>(null);

  // Load agents
  useEffect(() => {
    loadAgents();
  }, []);

  async function loadAgents() {
    try {
      setLoading(true);
      const data = await listAgents();
      setAgents(data.agents);
    } catch (error) {
      toast.error("Failed to load agents");
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  async function handleRegenerateConcierge() {
    setRegenerating(true);
    try {
      await regenerateConcierge();
      toast.success("Concierge updated with knowledge of all agents", {
        description: `Now aware of ${agents.filter(a => !a.is_router).length} specialist agents`,
      });
      loadAgents(); // Reload to get updated concierge
    } catch (error) {
      toast.error("Failed to update Concierge");
      console.error(error);
    } finally {
      setRegenerating(false);
    }
  }

  async function handleSaveAsTemplate() {
    if (!templateName.trim()) {
      toast.error("Please enter a template name");
      return;
    }
    setSavingTemplate(true);
    try {
      const result = await exportAsTemplate(templateName.trim(), templateDescription.trim());
      toast.success(`Template "${result.name}" saved`, {
        description: `Exported ${result.agent_count} agents`,
      });
      setShowSaveTemplate(false);
      setTemplateName("");
      setTemplateDescription("");
    } catch (error) {
      toast.error("Failed to save template");
      console.error(error);
    } finally {
      setSavingTemplate(false);
    }
  }

  async function loadKnowledge(agentId: string) {
    try {
      setKnowledgeLoading(true);
      const docs = await listKnowledge(agentId);
      setKnowledge(docs);
    } catch (error) {
      toast.error("Failed to load knowledge base");
      console.error(error);
    } finally {
      setKnowledgeLoading(false);
    }
  }

  async function loadWebSources(agentId: string) {
    try {
      setWebSourcesLoading(true);
      const data = await listWebSources(agentId);
      setWebSources(data.sources);
    } catch (error) {
      toast.error("Failed to load web sources");
      console.error(error);
    } finally {
      setWebSourcesLoading(false);
    }
  }

  async function handleAddWebSource() {
    if (!selectedAgent || !newWebSourceUrl.trim()) return;
    try {
      setAddingWebSource(true);
      const source = await addWebSource(selectedAgent.id, {
        url: newWebSourceUrl.trim(),
        name: newWebSourceName.trim() || undefined,
      });
      setWebSources((prev) => [...prev, source]);
      setNewWebSourceUrl("");
      setNewWebSourceName("");
      toast.success(`Web source added: ${source.name}`);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to add web source";
      toast.error(message);
    } finally {
      setAddingWebSource(false);
    }
  }

  async function handleRefreshWebSource(sourceId: string) {
    if (!selectedAgent) return;
    try {
      setRefreshingSource(sourceId);
      const updated = await refreshWebSource(selectedAgent.id, sourceId);
      setWebSources((prev) => prev.map((s) => (s.id === sourceId ? updated : s)));
      toast.success("Web source refreshed");
    } catch (error) {
      toast.error("Failed to refresh web source");
    } finally {
      setRefreshingSource(null);
    }
  }

  async function handleDeleteWebSource(sourceId: string) {
    if (!selectedAgent) return;
    try {
      await deleteWebSource(selectedAgent.id, sourceId);
      setWebSources((prev) => prev.filter((s) => s.id !== sourceId));
      toast.success("Web source deleted");
    } catch (error) {
      toast.error("Failed to delete web source");
    }
  }

  async function handleToggleStatus(agent: AgentConfig) {
    try {
      const updated = agent.status === "active"
        ? await disableAgent(agent.id)
        : await enableAgent(agent.id);
      setAgents(agents.map((a) => (a.id === agent.id ? updated : a)));
      toast.success(`Agent ${updated.status === "active" ? "enabled" : "disabled"}`);
    } catch (error) {
      toast.error("Failed to update agent status");
    }
  }

  async function handleSaveAgent(updates: Partial<AgentConfig>) {
    if (!editingAgent) return;
    try {
      const updated = await updateAgent(editingAgent.id, updates);
      setAgents(agents.map((a) => (a.id === updated.id ? updated : a)));
      setEditingAgent(null);
      toast.success("Agent updated");
    } catch (error) {
      toast.error("Failed to update agent");
    }
  }

  async function handleCreateAgent(newAgent: CreateAgentRequest) {
    try {
      const created = await createAgent(newAgent);
      setAgents([...agents, created]);
      setCreatingAgent(false);
      toast.success(`Agent "${created.name}" created`);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to create agent";
      toast.error(message);
    }
  }

  async function handleDeleteAgent(agentId: string) {
    try {
      await deleteAgent(agentId);
      setAgents(agents.filter((a) => a.id !== agentId));
      toast.success("Agent deleted");
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to delete agent";
      toast.error(message);
    }
  }

  async function handleUploadKnowledge(file: File) {
    if (!selectedAgent) return;
    const doc = await uploadKnowledge(selectedAgent.id, file);
    setKnowledge((prev) => [...prev, doc]);
    return doc;
  }

  async function handleBatchUpload(files: File[]) {
    if (!selectedAgent || files.length === 0) return;

    setUploading(true);
    const validExts = [".txt", ".pdf", ".docx", ".doc", ".md"];
    const validFiles = files.filter((f) =>
      validExts.some((ext) => f.name.toLowerCase().endsWith(ext))
    );

    if (validFiles.length === 0) {
      toast.error("No valid files. Supported: PDF, DOCX, TXT, MD");
      setUploading(false);
      return;
    }

    toast.info(`Uploading ${validFiles.length} file(s)...`);

    let successCount = 0;
    let failCount = 0;

    for (const file of validFiles) {
      try {
        await handleUploadKnowledge(file);
        successCount++;
      } catch {
        failCount++;
      }
    }

    setUploading(false);

    if (successCount > 0) {
      toast.success(`Uploaded ${successCount} file(s) successfully`);
    }
    if (failCount > 0) {
      toast.error(`Failed to upload ${failCount} file(s)`);
    }
  }

  async function handleDeleteKnowledge(docId: string) {
    if (!selectedAgent) return;
    try {
      await deleteKnowledge(selectedAgent.id, docId);
      setKnowledge(knowledge.filter((d) => d.id !== docId));
      toast.success("Document deleted");
    } catch (error) {
      toast.error("Failed to delete document");
    }
  }

  async function handleTestQuery() {
    if (!testingAgent || !testQuery.trim()) return;
    try {
      setTestLoading(true);
      setTestResponse(null);
      const result = await queryAgent(testingAgent.id, testQuery);
      setTestResponse(result.response);
      setTestSources(result.sources || []);
    } catch (error) {
      toast.error("Failed to query agent");
      console.error(error);
    } finally {
      setTestLoading(false);
    }
  }

  async function toggleRecording() {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      setIsRecording(false);
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;

        const chunks: Blob[] = [];
        mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
        mediaRecorder.onstop = async () => {
          stream.getTracks().forEach((t) => t.stop());
          toast.info("Voice input captured - speech-to-text coming soon");
        };

        mediaRecorder.start();
        setIsRecording(true);
        toast.info("Recording... Click again to stop");
      } catch (error) {
        toast.error("Could not access microphone");
      }
    }
  }

  const router = agents.find((a) => a.is_router);
  const departmentAgents = agents.filter((a) => !a.is_router);

  const filteredAgents = departmentAgents.filter((agent) => {
    const matchesSearch = agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesDomain = domainFilter === "all" || agent.domain === domainFilter;
    return matchesSearch && matchesDomain;
  });

  const domains = [...new Set(departmentAgents.map((a) => a.domain))];

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Loading agents...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header with Gradient */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-emerald-600 via-green-600 to-teal-600 p-6 text-white shadow-xl">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDM0aDR2MmgtNHYtMnptMC04aDR2Nmg0djJoLTh2LTh6bTAgMTZoOHYyaC04di0yem0tMTYgMGg0djJoLTR2LTJ6bTAtOGg0djZoNHYyaC04di04em0wIDE2aDh2Mmgtxdi0yeiIvPjwvZz48L2c+PC9zdmc+')] opacity-30"></div>
        <div className="relative">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/20 backdrop-blur-sm">
                <Bot className="h-8 w-8" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight">AI Agents</h1>
                <p className="text-white/80">{config.appName} agents - Create, test, and manage knowledge bases</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                onClick={() => setShowSaveTemplate(true)}
                variant="secondary"
                className="bg-white/20 text-white hover:bg-white/30 border-0"
              >
                <FolderDown className="mr-2 h-4 w-4" />
                Save as Template
              </Button>
              <Button
                onClick={() => setCreatingAgent(true)}
                className="bg-white text-green-600 hover:bg-white/90 shadow-lg"
              >
                <Plus className="mr-2 h-4 w-4" />
                Create Agent
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border-0 shadow-md">
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/30">
              <Layers className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Total Agents</p>
              <p className="text-xl font-bold">{agents.length}</p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-0 shadow-md">
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900/30">
              <Power className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Active</p>
              <p className="text-xl font-bold">{agents.filter((a) => a.status === "active").length}</p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-0 shadow-md">
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/30">
              <Route className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Routers</p>
              <p className="text-xl font-bold">{agents.filter((a) => a.is_router).length}</p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-0 shadow-md">
          <CardContent className="flex items-center gap-4 p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100 dark:bg-amber-900/30">
              <Globe className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Domains</p>
              <p className="text-xl font-bold">{domains.length}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Concierge Router Card - The Master Orchestrator */}
      {router && (
        <Card className="border-0 shadow-xl overflow-hidden">
          <div className="bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/20 backdrop-blur-sm shadow-lg">
                  <Sparkles className="h-8 w-8 text-white" />
                </div>
                <div className="text-white">
                  <div className="flex items-center gap-2 mb-1">
                    <h2 className="text-xl font-bold">{router.name}</h2>
                    <Badge className="bg-white/20 text-white border-0 text-xs">
                      Master Orchestrator
                    </Badge>
                  </div>
                  <p className="text-white/80 text-sm">{router.title}</p>
                  <p className="text-white/70 text-xs mt-1">
                    The intelligent front door that knows all your specialists
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge className={`border-0 ${router.status === "active" ? "bg-green-500/80" : "bg-gray-500/80"} text-white`}>
                  {router.status}
                </Badge>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" className="text-white hover:bg-white/20">
                      <MoreVertical className="h-5 w-5" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => setEditingAgent(router)}>
                      <Settings className="mr-2 h-4 w-4" />
                      Configure Concierge
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => {
                      setSelectedAgent(router);
                      loadKnowledge(router.id);
                      loadWebSources(router.id);
                    }}>
                      <Upload className="mr-2 h-4 w-4" />
                      Manage Knowledge Base
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => {
                      setTestingAgent(router);
                      setTestQuery("");
                      setTestResponse(null);
                    }}>
                      <Play className="mr-2 h-4 w-4" />
                      Test Concierge
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem asChild>
                      <a href="/chat" target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="mr-2 h-4 w-4" />
                        Open Public Chat
                      </a>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </div>
          <CardContent className="p-5">
            <p className="text-sm text-muted-foreground mb-4">{router.description}</p>

            {/* Agent Awareness Stats */}
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="text-center p-3 rounded-lg bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-950/30 dark:to-orange-950/30">
                <div className="text-2xl font-bold text-amber-600">{departmentAgents.length}</div>
                <div className="text-xs text-muted-foreground">Specialists Known</div>
              </div>
              <div className="text-center p-3 rounded-lg bg-gradient-to-br from-emerald-50 to-green-50 dark:from-emerald-950/30 dark:to-green-950/30">
                <div className="text-2xl font-bold text-emerald-600">{agents.filter(a => a.status === "active" && !a.is_router).length}</div>
                <div className="text-xs text-muted-foreground">Active Routes</div>
              </div>
              <div className="text-center p-3 rounded-lg bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30">
                <div className="text-2xl font-bold text-blue-600">{domains.length}</div>
                <div className="text-xs text-muted-foreground">Domains</div>
              </div>
            </div>

            {/* Capabilities */}
            <div className="flex flex-wrap gap-2 mb-4">
              {router.capabilities.map((cap) => (
                <Badge key={cap} variant="secondary" className="text-xs">{cap}</Badge>
              ))}
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-between pt-4 border-t">
              <div className="text-xs text-muted-foreground">
                <span className="font-medium">Tip:</span> Update the Concierge after adding or removing agents
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSelectedAgent(router);
                    loadKnowledge(router.id);
                    loadWebSources(router.id);
                  }}
                >
                  <Upload className="mr-2 h-4 w-4" />
                  Knowledge
                </Button>
                <Button
                  size="sm"
                  onClick={handleRegenerateConcierge}
                  disabled={regenerating}
                  className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600"
                >
                  {regenerating ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="mr-2 h-4 w-4" />
                  )}
                  Sync Agents
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Department Agents */}
      <Card className="border-0 shadow-lg">
        <CardHeader className="border-b bg-muted/30">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Sparkles className="h-5 w-5 text-amber-500" />
              Department Agents
            </CardTitle>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search agents..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 sm:w-64"
                />
              </div>
              <select
                value={domainFilter}
                onChange={(e) => setDomainFilter(e.target.value)}
                className="h-10 rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="all">All Domains</option>
                {domains.map((domain) => (
                  <option key={domain} value={domain}>{domain}</option>
                ))}
              </select>
              <Button variant="outline" size="icon" onClick={loadAgents}>
                <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-4">
          {filteredAgents.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Bot className="h-12 w-12 text-muted-foreground/50 mb-4" />
              <p className="text-lg font-medium text-muted-foreground">No agents found</p>
              <p className="text-sm text-muted-foreground">
                {searchQuery ? "Try adjusting your search" : "Create your first agent to get started"}
              </p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {filteredAgents.map((agent, index) => {
                const domainCfg = domainConfig[agent.domain] || domainConfig.General;
                const Icon = domainCfg.icon;
                const status = statusConfig[agent.status];

                return (
                  <Card
                    key={agent.id}
                    className="group relative overflow-hidden border hover:border-primary/50 hover:shadow-md transition-all"
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <div className={`absolute left-0 top-0 h-full w-1 bg-gradient-to-b ${domainCfg.gradient}`} />
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br ${domainCfg.gradient} text-white shadow-sm`}>
                            <Icon className="h-5 w-5" />
                          </div>
                          <div>
                            <CardTitle className="text-base">{agent.name}</CardTitle>
                            <p className="text-xs text-muted-foreground">{agent.title}</p>
                          </div>
                        </div>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => setEditingAgent(agent)}>
                              <Settings className="mr-2 h-4 w-4" />
                              Edit Agent
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => {
                              setSelectedAgent(agent);
                              loadKnowledge(agent.id);
                              loadWebSources(agent.id);
                            }}>
                              <Upload className="mr-2 h-4 w-4" />
                              Manage Knowledge
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => {
                              setTestingAgent(agent);
                              setTestQuery("");
                              setTestResponse(null);
                            }}>
                              <Play className="mr-2 h-4 w-4" />
                              Test Agent
                            </DropdownMenuItem>
                            {agent.gpt_url && (
                              <DropdownMenuItem onClick={() => window.open(agent.gpt_url, "_blank")}>
                                <ExternalLink className="mr-2 h-4 w-4" />
                                Open in ChatGPT
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onClick={() => handleToggleStatus(agent)}>
                              <Power className="mr-2 h-4 w-4" />
                              {agent.status === "active" ? "Disable" : "Enable"}
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => setAgentToDelete(agent)}
                              className="text-destructive focus:text-destructive"
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Delete Agent
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="secondary">{agent.domain}</Badge>
                        <Badge variant="outline" className={status.color}>{status.label}</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-2">{agent.description}</p>
                      <Separator />
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1"
                          onClick={() => {
                            setTestingAgent(agent);
                            setTestQuery("");
                            setTestResponse(null);
                          }}
                        >
                          <Play className="mr-1 h-3 w-3" />
                          Test
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1"
                          onClick={() => {
                            setSelectedAgent(agent);
                            loadKnowledge(agent.id);
                            loadWebSources(agent.id);
                          }}
                        >
                          <Upload className="mr-1 h-3 w-3" />
                          Knowledge
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit Agent Dialog */}
      <Dialog open={!!editingAgent} onOpenChange={() => setEditingAgent(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          {editingAgent && (
            <EditAgentForm
              agent={editingAgent}
              onSave={handleSaveAgent}
              onCancel={() => setEditingAgent(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Knowledge Base Sheet */}
      <Sheet open={!!selectedAgent} onOpenChange={() => setSelectedAgent(null)}>
        <SheetContent className="w-full sm:max-w-xl">
          {selectedAgent && (
            <>
              <SheetHeader>
                <SheetTitle>Knowledge Base: {selectedAgent.name}</SheetTitle>
                <SheetDescription>
                  Manage documents and web sources for this agent
                </SheetDescription>
              </SheetHeader>

              <Tabs defaultValue="documents" className="mt-4">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="documents">
                    <FileText className="mr-2 h-4 w-4" />
                    Documents ({knowledge.length})
                  </TabsTrigger>
                  <TabsTrigger value="web-sources">
                    <Globe2 className="mr-2 h-4 w-4" />
                    Web Sources ({webSources.length})
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="documents" className="space-y-4 mt-4">
                  <div
                    className={`relative border-2 border-dashed rounded-xl p-6 text-center transition-colors ${
                      isDragging
                        ? "border-primary bg-primary/5"
                        : "border-muted-foreground/25 hover:border-muted-foreground/50"
                    } ${uploading ? "opacity-50 pointer-events-none" : ""}`}
                    onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                    onDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }}
                    onDrop={(e) => {
                      e.preventDefault();
                      setIsDragging(false);
                      handleBatchUpload(Array.from(e.dataTransfer.files));
                    }}
                  >
                    {uploading ? (
                      <div className="flex flex-col items-center gap-2">
                        <Loader2 className="h-8 w-8 animate-spin text-primary" />
                        <p className="text-sm text-muted-foreground">Uploading files...</p>
                      </div>
                    ) : (
                      <>
                        <Upload className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                        <p className="text-sm font-medium">Drag & drop files here</p>
                        <p className="text-xs text-muted-foreground mt-1">or click to browse</p>
                        <Input
                          type="file"
                          accept=".txt,.pdf,.docx,.doc,.md"
                          multiple
                          className="absolute inset-0 opacity-0 cursor-pointer"
                          onChange={(e) => {
                            if (e.target.files) handleBatchUpload(Array.from(e.target.files));
                            e.target.value = "";
                          }}
                        />
                      </>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground text-center">Supported: PDF, DOCX, TXT, MD</p>

                  <Separator />

                  {knowledgeLoading ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin" />
                    </div>
                  ) : knowledge.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-8">
                      No documents yet. Upload files to build the knowledge base.
                    </p>
                  ) : (
                    <div className="space-y-2 max-h-[400px] overflow-y-auto">
                      {knowledge.map((doc) => (
                        <div key={doc.id} className="flex items-center justify-between p-3 rounded-lg border">
                          <div className="flex items-center gap-3">
                            <FileText className="h-5 w-5 text-muted-foreground" />
                            <div>
                              <p className="font-medium text-sm">{doc.filename}</p>
                              <p className="text-xs text-muted-foreground">
                                {doc.chunk_count} chunks · {(doc.file_size / 1024).toFixed(1)}KB
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-1">
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => {
                                      if (selectedAgent) {
                                        window.open(getKnowledgeDownloadUrl(selectedAgent.id, doc.id), "_blank");
                                      }
                                    }}
                                  >
                                    <Download className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Download</TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                            <Button variant="ghost" size="icon" onClick={() => handleDeleteKnowledge(doc.id)}>
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="web-sources" className="space-y-4 mt-4">
                  <div className="space-y-3 p-4 border rounded-xl bg-muted/50">
                    <div className="flex gap-2">
                      <Input
                        placeholder="https://example.com/page"
                        value={newWebSourceUrl}
                        onChange={(e) => setNewWebSourceUrl(e.target.value)}
                        className="flex-1"
                      />
                      <Button onClick={handleAddWebSource} disabled={addingWebSource || !newWebSourceUrl.trim()}>
                        {addingWebSource ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                      </Button>
                    </div>
                    <Input
                      placeholder="Optional: Custom name for this source"
                      value={newWebSourceName}
                      onChange={(e) => setNewWebSourceName(e.target.value)}
                    />
                    <p className="text-xs text-muted-foreground">
                      Add a URL to automatically fetch and index its content.
                    </p>
                  </div>

                  <Separator />

                  {webSourcesLoading ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin" />
                    </div>
                  ) : webSources.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-8">
                      No web sources yet. Add URLs to automatically ingest web content.
                    </p>
                  ) : (
                    <div className="space-y-2 max-h-[400px] overflow-y-auto">
                      {webSources.map((source) => (
                        <div key={source.id} className="flex items-center justify-between p-3 rounded-lg border">
                          <div className="flex items-center gap-3 min-w-0 flex-1">
                            <Globe2 className="h-5 w-5 text-muted-foreground shrink-0" />
                            <div className="min-w-0">
                              <p className="font-medium text-sm truncate">{source.name}</p>
                              <p className="text-xs text-muted-foreground truncate">{source.url}</p>
                              <div className="flex items-center gap-2 mt-1">
                                <Badge
                                  variant={source.last_refresh_status === "success" ? "default" : "destructive"}
                                  className="text-xs"
                                >
                                  {source.last_refresh_status === "success" ? "OK" : "Error"}
                                </Badge>
                                <span className="text-xs text-muted-foreground">{source.chunk_count} chunks</span>
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-1 shrink-0">
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => handleRefreshWebSource(source.id)}
                                    disabled={refreshingSource === source.id}
                                  >
                                    {refreshingSource === source.id ? (
                                      <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                      <RefreshCw className="h-4 w-4" />
                                    )}
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Refresh now</TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button variant="ghost" size="icon" onClick={() => window.open(source.url, "_blank")}>
                                    <Link2 className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Open URL</TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                            <Button variant="ghost" size="icon" onClick={() => handleDeleteWebSource(source.id)}>
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* Test Console Dialog */}
      <Dialog open={!!testingAgent} onOpenChange={() => setTestingAgent(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh]">
          {testingAgent && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5 text-green-500" />
                  Test: {testingAgent.name}
                </DialogTitle>
                <DialogDescription>
                  Query this agent and see how it responds with its knowledge base
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4">
                <div className="flex gap-2">
                  <Textarea
                    placeholder="Type your question..."
                    value={testQuery}
                    onChange={(e) => setTestQuery(e.target.value)}
                    className="flex-1 min-h-[80px]"
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleTestQuery();
                      }
                    }}
                  />
                  <div className="flex flex-col gap-2">
                    <Button
                      variant={isRecording ? "destructive" : "outline"}
                      size="icon"
                      onClick={toggleRecording}
                    >
                      {isRecording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                    </Button>
                    <Button
                      onClick={handleTestQuery}
                      disabled={testLoading || !testQuery.trim()}
                      className="bg-gradient-to-r from-green-500 to-emerald-500"
                    >
                      {testLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>

                {testResponse && (
                  <div className="space-y-4">
                    <div className="p-4 rounded-xl bg-muted">
                      <p className="text-sm font-medium text-muted-foreground mb-2">Response:</p>
                      <p className="text-sm whitespace-pre-wrap">{testResponse}</p>
                    </div>

                    {testSources.length > 0 && (
                      <div>
                        <p className="text-sm font-medium text-muted-foreground mb-2">
                          Sources Used ({testSources.length}):
                        </p>
                        <div className="space-y-2 max-h-48 overflow-y-auto">
                          {testSources.map((source, i) => (
                            <div key={i} className="p-2 rounded border text-xs">
                              <p className="font-medium">{(source.metadata?.filename as string) || "Unknown source"}</p>
                              <p className="text-muted-foreground line-clamp-2">{source.text}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Create Agent Dialog */}
      <Dialog open={creatingAgent} onOpenChange={setCreatingAgent}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <CreateAgentForm onSave={handleCreateAgent} onCancel={() => setCreatingAgent(false)} />
        </DialogContent>
      </Dialog>

      {/* Delete Agent Confirmation Dialog */}
      <AlertDialog open={!!agentToDelete} onOpenChange={(open) => !open && setAgentToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              Delete Agent
            </AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{agentToDelete?.name}</strong>?
              This will also delete all knowledge base documents for this agent.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (agentToDelete) {
                  handleDeleteAgent(agentToDelete.id);
                  setAgentToDelete(null);
                }
              }}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Save as Template Dialog */}
      <Dialog open={showSaveTemplate} onOpenChange={setShowSaveTemplate}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FolderDown className="h-5 w-5 text-blue-500" />
              Save as Template
            </DialogTitle>
            <DialogDescription>
              Export your current agent configuration as a reusable template.
              This saves {departmentAgents.length} agent(s) (excluding the Concierge).
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Template Name *</label>
              <Input
                placeholder="e.g., Cleveland Municipal Setup"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Description (optional)</label>
              <Textarea
                placeholder="Describe what this template includes..."
                value={templateDescription}
                onChange={(e) => setTemplateDescription(e.target.value)}
                rows={3}
              />
            </div>

            {/* Preview of what will be saved */}
            <div className="p-3 rounded-lg bg-muted">
              <p className="text-sm font-medium mb-2">Agents to Export:</p>
              <div className="max-h-32 overflow-y-auto space-y-1">
                {departmentAgents.slice(0, 5).map((agent) => (
                  <div key={agent.id} className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Bot className="h-3 w-3" />
                    <span>{agent.name}</span>
                    <Badge variant="outline" className="text-[10px] px-1">{agent.domain}</Badge>
                  </div>
                ))}
                {departmentAgents.length > 5 && (
                  <p className="text-xs text-muted-foreground">
                    +{departmentAgents.length - 5} more agents
                  </p>
                )}
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSaveTemplate(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSaveAsTemplate}
              disabled={savingTemplate || !templateName.trim()}
              className="bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600"
            >
              {savingTemplate ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-2 h-4 w-4" />
              )}
              Save Template
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Edit Agent Form Component
const hitlModeOptions = [
  { value: "AUTO", label: "Auto", description: "Response sent immediately", color: "bg-green-500" },
  { value: "DRAFT", label: "Draft", description: "Saved for review before sending", color: "bg-blue-500" },
  { value: "REVIEW", label: "Review", description: "Requires approval before delivery", color: "bg-amber-500" },
  { value: "ESCALATE", label: "Escalate", description: "Routes to supervisor", color: "bg-red-500" },
];

function EditAgentForm({ agent, onSave, onCancel }: { agent: AgentConfig; onSave: (updates: Partial<AgentConfig>) => void; onCancel: () => void }) {
  const [name, setName] = useState(agent.name);
  const [title, setTitle] = useState(agent.title);
  const [description, setDescription] = useState(agent.description);
  const [systemPrompt, setSystemPrompt] = useState(agent.system_prompt);
  const [capabilities, setCapabilities] = useState(agent.capabilities.join("\n"));
  const [guardrails, setGuardrails] = useState(agent.guardrails.join("\n"));
  const [escalatesTo, setEscalatesTo] = useState(agent.escalates_to);
  const [hitlMode, setHitlMode] = useState(agent.hitl_mode || "AUTO");
  const [gptUrl, setGptUrl] = useState(agent.gpt_url || "");

  return (
    <>
      <DialogHeader>
        <DialogTitle>Edit Agent: {agent.name}</DialogTitle>
        <DialogDescription>Update the agent configuration</DialogDescription>
      </DialogHeader>

      <Tabs defaultValue="basic" className="mt-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="basic">Basic Info</TabsTrigger>
          <TabsTrigger value="prompt">System Prompt</TabsTrigger>
          <TabsTrigger value="guardrails">Guardrails</TabsTrigger>
        </TabsList>

        <TabsContent value="basic" className="space-y-4 mt-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Name</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Title</label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Description</label>
            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Escalates To</label>
            <Input value={escalatesTo} onChange={(e) => setEscalatesTo(e.target.value)} />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Capabilities (one per line)</label>
            <Textarea value={capabilities} onChange={(e) => setCapabilities(e.target.value)} rows={4} />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">GPT/Copilot URL (optional)</label>
            <Input value={gptUrl} onChange={(e) => setGptUrl(e.target.value)} placeholder="https://chat.openai.com/g/..." />
            <p className="text-xs text-muted-foreground">External URL to a ChatGPT or Copilot agent</p>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium flex items-center gap-2">
              <Shield className="h-4 w-4 text-amber-500" />
              HITL Mode (Human-in-the-Loop)
            </label>
            <div className="grid grid-cols-2 gap-2">
              {hitlModeOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setHitlMode(option.value)}
                  className={`p-3 rounded-lg border-2 text-left transition-all ${
                    hitlMode === option.value
                      ? "border-primary bg-primary/10"
                      : "border-muted hover:border-muted-foreground/50"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${option.color}`}></div>
                    <span className="font-medium text-sm">{option.label}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">{option.description}</p>
                </button>
              ))}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="prompt" className="space-y-4 mt-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">System Prompt</label>
            <Textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} rows={15} className="font-mono text-sm" />
          </div>
        </TabsContent>

        <TabsContent value="guardrails" className="space-y-4 mt-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Guardrails (one per line)</label>
            <Textarea value={guardrails} onChange={(e) => setGuardrails(e.target.value)} rows={10} />
          </div>
        </TabsContent>
      </Tabs>

      <DialogFooter className="mt-6">
        <Button variant="outline" onClick={onCancel}>Cancel</Button>
        <Button onClick={() => onSave({
          name, title, description, system_prompt: systemPrompt,
          capabilities: capabilities.split("\n").filter((c) => c.trim()),
          guardrails: guardrails.split("\n").filter((g) => g.trim()),
          escalates_to: escalatesTo,
          hitl_mode: hitlMode,
          gpt_url: gptUrl,
        })} className="bg-gradient-to-r from-green-500 to-emerald-500">
          Save Changes
        </Button>
      </DialogFooter>
    </>
  );
}

// Create Agent Form Component
const domainOptions = ["General", "Router", "Strategy", "PublicHealth", "HR", "Finance", "Building", "311", "Regional", "Legal", "IT", "Custom"];

function CreateAgentForm({ onSave, onCancel }: { onSave: (agent: CreateAgentRequest) => void; onCancel: () => void }) {
  const [id, setId] = useState("");
  const [name, setName] = useState("");
  const [title, setTitle] = useState("");
  const [domain, setDomain] = useState("General");
  const [description, setDescription] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [capabilities, setCapabilities] = useState("");
  const [guardrails, setGuardrails] = useState("");
  const [escalatesTo, setEscalatesTo] = useState("");
  const [isRouter, setIsRouter] = useState(false);

  useEffect(() => {
    if (name && !id) {
      setId(name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/-+$/, ""));
    }
  }, [name, id]);

  return (
    <>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-green-500" />
          Create New Agent
        </DialogTitle>
        <DialogDescription>Configure a new AI agent</DialogDescription>
      </DialogHeader>

      <Tabs defaultValue="basic" className="mt-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="basic">Basic Info</TabsTrigger>
          <TabsTrigger value="prompt">System Prompt</TabsTrigger>
          <TabsTrigger value="guardrails">Guardrails</TabsTrigger>
        </TabsList>

        <TabsContent value="basic" className="space-y-4 mt-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Agent ID *</label>
              <Input value={id} onChange={(e) => setId(e.target.value)} placeholder="hr-assistant" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Name *</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="HR Assistant" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Title</label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Human Resources Specialist" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Domain</label>
              <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" value={domain} onChange={(e) => setDomain(e.target.value)}>
                {domainOptions.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Description</label>
            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Escalates To</label>
            <Input value={escalatesTo} onChange={(e) => setEscalatesTo(e.target.value)} placeholder="agent-id or email" />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Capabilities (one per line)</label>
            <Textarea value={capabilities} onChange={(e) => setCapabilities(e.target.value)} rows={4} />
          </div>
          <div className="flex items-center gap-2 pt-2">
            <input type="checkbox" id="is-router" checked={isRouter} onChange={(e) => setIsRouter(e.target.checked)} className="h-4 w-4 rounded border-gray-300" />
            <label htmlFor="is-router" className="text-sm">This is a router/concierge agent</label>
          </div>
        </TabsContent>

        <TabsContent value="prompt" className="space-y-4 mt-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">System Prompt</label>
            <Textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} rows={15} className="font-mono text-sm" />
          </div>
        </TabsContent>

        <TabsContent value="guardrails" className="space-y-4 mt-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Guardrails (one per line)</label>
            <Textarea value={guardrails} onChange={(e) => setGuardrails(e.target.value)} rows={10} />
          </div>
        </TabsContent>
      </Tabs>

      <DialogFooter className="mt-6">
        <Button variant="outline" onClick={onCancel}>Cancel</Button>
        <Button onClick={() => onSave({
          id: id.trim(), name: name.trim(), title: title.trim(), domain, description: description.trim(),
          system_prompt: systemPrompt.trim(),
          capabilities: capabilities.split("\n").filter((c) => c.trim()),
          guardrails: guardrails.split("\n").filter((g) => g.trim()),
          escalates_to: escalatesTo.trim(), is_router: isRouter,
        })} disabled={!id.trim() || !name.trim()} className="bg-gradient-to-r from-green-500 to-emerald-500">
          Create Agent
        </Button>
      </DialogFooter>
    </>
  );
}
