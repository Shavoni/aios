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
  queryAgent,
  createAgent,
  type AgentConfig,
  type KnowledgeDocument,
  type CreateAgentRequest,
} from "@/lib/api";
import { toast } from "sonner";
import { config } from "@/lib/config";
import { Plus, AlertTriangle } from "lucide-react";
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

type AgentDomain = "Router" | "Strategy" | "PublicHealth" | "HR" | "Finance" | "Building" | "311" | "Regional" | string;

const domainIcons: Record<string, React.ElementType> = {
  Router: Route,
  Strategy: Lightbulb,
  PublicHealth: HeartPulse,
  HR: Users,
  Finance: DollarSign,
  Building: Building2,
  "311": Phone,
  Regional: Globe,
};

const domainColors: Record<string, string> = {
  Router: "bg-indigo-500",
  Strategy: "bg-violet-500",
  PublicHealth: "bg-red-500",
  HR: "bg-green-500",
  Finance: "bg-cyan-500",
  Building: "bg-amber-500",
  "311": "bg-blue-500",
  Regional: "bg-purple-500",
};

const statusStyles = {
  active: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  inactive: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300",
  degraded: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300",
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

  // Test console state
  const [testQuery, setTestQuery] = useState("");
  const [testResponse, setTestResponse] = useState<string | null>(null);
  const [testSources, setTestSources] = useState<Array<{ text: string; metadata: Record<string, unknown> }>>([]);
  const [testLoading, setTestLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

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
      toast.success(`Agent "${created.name}" created - Concierge updated`);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to create agent";
      toast.error(message);
    }
  }

  async function handleDeleteAgent(agentId: string) {
    try {
      await deleteAgent(agentId);
      setAgents(agents.filter((a) => a.id !== agentId));
      toast.success("Agent deleted - Concierge updated");
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to delete agent";
      toast.error(message);
    }
  }

  async function handleUploadKnowledge(file: File) {
    if (!selectedAgent) return;
    try {
      const doc = await uploadKnowledge(selectedAgent.id, file);
      setKnowledge([...knowledge, doc]);
      toast.success(`Uploaded ${file.name}`);
    } catch (error) {
      toast.error("Failed to upload document");
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

  // Voice recording
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
          // Here you would send to a speech-to-text API
          // For now, we'll show a placeholder
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">AI Agents</h1>
          <p className="text-muted-foreground">
            {config.appName} agents - Create, edit, test, and manage knowledge bases
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={loadAgents} variant="outline">
            Refresh
          </Button>
          <Button onClick={() => setCreatingAgent(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Agent
          </Button>
        </div>
      </div>

      {/* Router Agent */}
      {router && (
        <div>
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Route className="h-5 w-5 text-indigo-500" />
            Concierge Router
          </h2>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <AgentCard
              agent={router}
              onEdit={() => setEditingAgent(router)}
              onToggleStatus={() => handleToggleStatus(router)}
              onManageKnowledge={() => {
                setSelectedAgent(router);
                loadKnowledge(router.id);
              }}
              onTest={() => {
                setTestingAgent(router);
                setTestQuery("");
                setTestResponse(null);
              }}
              onDelete={() => {}} // Concierge cannot be deleted
            />
          </div>
        </div>
      )}

      {/* Department Agents */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Department Leadership Assets</h2>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {departmentAgents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onEdit={() => setEditingAgent(agent)}
              onToggleStatus={() => handleToggleStatus(agent)}
              onManageKnowledge={() => {
                setSelectedAgent(agent);
                loadKnowledge(agent.id);
              }}
              onTest={() => {
                setTestingAgent(agent);
                setTestQuery("");
                setTestResponse(null);
              }}
              onDelete={() => handleDeleteAgent(agent.id)}
            />
          ))}
        </div>
      </div>

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
        <SheetContent className="w-full sm:max-w-lg">
          {selectedAgent && (
            <>
              <SheetHeader>
                <SheetTitle>Knowledge Base: {selectedAgent.name}</SheetTitle>
                <SheetDescription>
                  Upload documents for this agent to reference when responding
                </SheetDescription>
              </SheetHeader>
              <div className="mt-6 space-y-4">
                {/* Upload */}
                <div>
                  <Input
                    type="file"
                    accept=".txt,.pdf,.docx,.doc,.md"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleUploadKnowledge(file);
                      e.target.value = "";
                    }}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Supported: PDF, DOCX, TXT, MD
                  </p>
                </div>

                <Separator />

                {/* Documents */}
                {knowledgeLoading ? (
                  <div className="flex justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                  </div>
                ) : knowledge.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No documents yet. Upload files to build the knowledge base.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {knowledge.map((doc) => (
                      <div
                        key={doc.id}
                        className="flex items-center justify-between p-3 rounded-lg border"
                      >
                        <div className="flex items-center gap-3">
                          <FileText className="h-5 w-5 text-muted-foreground" />
                          <div>
                            <p className="font-medium text-sm">{doc.filename}</p>
                            <p className="text-xs text-muted-foreground">
                              {doc.chunk_count} chunks · {(doc.file_size / 1024).toFixed(1)}KB
                            </p>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeleteKnowledge(doc.id)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
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
                <DialogTitle>Test: {testingAgent.name}</DialogTitle>
                <DialogDescription>
                  Query this agent and see how it responds with its knowledge base
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4">
                {/* Input */}
                <div className="flex gap-2">
                  <Textarea
                    placeholder="Type your question or use the microphone..."
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
                    <Button onClick={handleTestQuery} disabled={testLoading || !testQuery.trim()}>
                      {testLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Send className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>

                {/* Response */}
                {testResponse && (
                  <div className="space-y-4">
                    <div className="p-4 rounded-lg bg-muted">
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
                              <p className="font-medium">
                                {(source.metadata?.filename as string) || "Unknown source"}
                              </p>
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
          <CreateAgentForm
            onSave={handleCreateAgent}
            onCancel={() => setCreatingAgent(false)}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}

// =============================================================================
// Agent Card Component
// =============================================================================

function AgentCard({
  agent,
  onEdit,
  onToggleStatus,
  onManageKnowledge,
  onTest,
  onDelete,
}: {
  agent: AgentConfig;
  onEdit: () => void;
  onToggleStatus: () => void;
  onManageKnowledge: () => void;
  onTest: () => void;
  onDelete: () => void;
}) {
  const Icon = domainIcons[agent.domain] || Shield;
  const color = domainColors[agent.domain] || "bg-gray-500";

  return (
    <Card className="relative overflow-hidden">
      <div className={`absolute left-0 top-0 h-full w-1 ${color}`} />
      <CardHeader className="flex flex-row items-start justify-between pb-2">
        <div className="flex items-center gap-3">
          <div className={`rounded-lg p-2 ${color} bg-opacity-10`}>
            <Icon className={`h-5 w-5 ${color.replace("bg-", "text-")}`} />
          </div>
          <div className="space-y-1">
            <CardTitle className="text-base leading-tight">{agent.name}</CardTitle>
            <p className="text-xs text-muted-foreground">{agent.title}</p>
          </div>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={onEdit}>
              <Settings className="mr-2 h-4 w-4" />
              Edit Agent
            </DropdownMenuItem>
            <DropdownMenuItem onClick={onManageKnowledge}>
              <Upload className="mr-2 h-4 w-4" />
              Manage Knowledge
            </DropdownMenuItem>
            <DropdownMenuItem onClick={onTest}>
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
            <DropdownMenuItem onClick={onToggleStatus}>
              <Power className="mr-2 h-4 w-4" />
              {agent.status === "active" ? "Disable" : "Enable"}
            </DropdownMenuItem>
            {!agent.is_router && (
              <>
                <DropdownMenuSeparator />
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <DropdownMenuItem
                      onSelect={(e) => e.preventDefault()}
                      className="text-destructive focus:text-destructive"
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete Agent
                    </DropdownMenuItem>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle className="flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5 text-destructive" />
                        Delete Agent
                      </AlertDialogTitle>
                      <AlertDialogDescription>
                        Are you sure you want to delete <strong>{agent.name}</strong>?
                        This will also delete all knowledge base documents for this agent.
                        This action cannot be undone.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={onDelete}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      >
                        Delete
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge variant="secondary">{agent.domain}</Badge>
          {agent.is_router && (
            <Badge variant="outline" className="border-indigo-500 text-indigo-600">
              Router
            </Badge>
          )}
          <Badge variant="secondary" className={statusStyles[agent.status]}>
            {agent.status}
          </Badge>
        </div>

        <p className="text-sm text-muted-foreground line-clamp-2">{agent.description}</p>

        <Separator />

        {/* Quick Actions */}
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="flex-1" onClick={onTest}>
            <Play className="mr-1 h-3 w-3" />
            Test
          </Button>
          <Button variant="outline" size="sm" className="flex-1" onClick={onManageKnowledge}>
            <Upload className="mr-1 h-3 w-3" />
            Knowledge
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Edit Agent Form
// =============================================================================

function EditAgentForm({
  agent,
  onSave,
  onCancel,
}: {
  agent: AgentConfig;
  onSave: (updates: Partial<AgentConfig>) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(agent.name);
  const [title, setTitle] = useState(agent.title);
  const [description, setDescription] = useState(agent.description);
  const [systemPrompt, setSystemPrompt] = useState(agent.system_prompt);
  const [capabilities, setCapabilities] = useState(agent.capabilities.join("\n"));
  const [guardrails, setGuardrails] = useState(agent.guardrails.join("\n"));
  const [escalatesTo, setEscalatesTo] = useState(agent.escalates_to);

  function handleSave() {
    onSave({
      name,
      title,
      description,
      system_prompt: systemPrompt,
      capabilities: capabilities.split("\n").filter((c) => c.trim()),
      guardrails: guardrails.split("\n").filter((g) => g.trim()),
      escalates_to: escalatesTo,
    });
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>Edit Agent: {agent.name}</DialogTitle>
        <DialogDescription>
          Update the agent configuration, system prompt, and guardrails
        </DialogDescription>
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
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Escalates To</label>
            <Input value={escalatesTo} onChange={(e) => setEscalatesTo(e.target.value)} />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Capabilities (one per line)</label>
            <Textarea
              value={capabilities}
              onChange={(e) => setCapabilities(e.target.value)}
              rows={4}
              placeholder="Intent classification&#10;Department routing&#10;Risk triage"
            />
          </div>
        </TabsContent>

        <TabsContent value="prompt" className="space-y-4 mt-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">System Prompt</label>
            <p className="text-xs text-muted-foreground">
              This is the core instruction that defines how the agent behaves
            </p>
            <Textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={15}
              className="font-mono text-sm"
            />
          </div>
        </TabsContent>

        <TabsContent value="guardrails" className="space-y-4 mt-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Guardrails (one per line)</label>
            <p className="text-xs text-muted-foreground">
              Rules the agent MUST follow - these are enforced in every response
            </p>
            <Textarea
              value={guardrails}
              onChange={(e) => setGuardrails(e.target.value)}
              rows={10}
              placeholder="No speculation on policy&#10;Escalate high-risk to human&#10;Protect PHI (HIPAA)"
            />
          </div>
        </TabsContent>
      </Tabs>

      <DialogFooter className="mt-6">
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button onClick={handleSave}>Save Changes</Button>
      </DialogFooter>
    </>
  );
}

// =============================================================================
// Create Agent Form
// =============================================================================

const domainOptions = [
  "General",
  "Router",
  "Strategy",
  "PublicHealth",
  "HR",
  "Finance",
  "Building",
  "311",
  "Regional",
  "Legal",
  "IT",
  "Custom",
];

function CreateAgentForm({
  onSave,
  onCancel,
}: {
  onSave: (agent: CreateAgentRequest) => void;
  onCancel: () => void;
}) {
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

  // Auto-generate ID from name
  useEffect(() => {
    if (name && !id) {
      setId(name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/-+$/, ""));
    }
  }, [name, id]);

  function handleSave() {
    if (!id.trim() || !name.trim()) {
      toast.error("ID and Name are required");
      return;
    }

    onSave({
      id: id.trim(),
      name: name.trim(),
      title: title.trim(),
      domain,
      description: description.trim(),
      system_prompt: systemPrompt.trim(),
      capabilities: capabilities.split("\n").filter((c) => c.trim()),
      guardrails: guardrails.split("\n").filter((g) => g.trim()),
      escalates_to: escalatesTo.trim(),
      is_router: isRouter,
    });
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>Create New Agent</DialogTitle>
        <DialogDescription>
          Configure a new AI agent with its system prompt, capabilities, and guardrails.
          You can add knowledge base documents after creation.
        </DialogDescription>
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
              <Input
                value={id}
                onChange={(e) => setId(e.target.value)}
                placeholder="hr-assistant"
              />
              <p className="text-xs text-muted-foreground">
                Unique identifier (auto-generated from name)
              </p>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Name *</label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="HR Assistant"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Title</label>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Human Resources Specialist"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Domain</label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
              >
                {domainOptions.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Description</label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="Describe what this agent does and its primary responsibilities..."
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Escalates To</label>
            <Input
              value={escalatesTo}
              onChange={(e) => setEscalatesTo(e.target.value)}
              placeholder="agent-id or email"
            />
            <p className="text-xs text-muted-foreground">
              Where to route queries this agent cannot handle
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Capabilities (one per line)</label>
            <Textarea
              value={capabilities}
              onChange={(e) => setCapabilities(e.target.value)}
              rows={4}
              placeholder="Answer HR policy questions&#10;Process time-off requests&#10;Explain benefits options"
            />
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="is-router"
              checked={isRouter}
              onChange={(e) => setIsRouter(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
            />
            <label htmlFor="is-router" className="text-sm">
              This is a router/concierge agent (routes to other agents)
            </label>
          </div>
        </TabsContent>

        <TabsContent value="prompt" className="space-y-4 mt-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">System Prompt</label>
            <p className="text-xs text-muted-foreground">
              The core instruction that defines how this agent behaves. Be specific about
              its role, tone, and how it should respond.
            </p>
            <Textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={15}
              className="font-mono text-sm"
              placeholder={`You are an AI assistant specializing in Human Resources for the City of Cleveland.

Your role is to:
- Answer employee questions about HR policies
- Help with benefits enrollment and questions
- Explain time-off procedures
- Guide employees through HR processes

Guidelines:
- Be professional and helpful
- Cite specific policies when relevant
- Escalate sensitive matters to HR leadership
- Protect employee privacy at all times`}
            />
          </div>
        </TabsContent>

        <TabsContent value="guardrails" className="space-y-4 mt-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Guardrails (one per line)</label>
            <p className="text-xs text-muted-foreground">
              Rules the agent MUST follow - these are enforced in every response and
              help prevent inappropriate or risky responses.
            </p>
            <Textarea
              value={guardrails}
              onChange={(e) => setGuardrails(e.target.value)}
              rows={10}
              placeholder="Never provide specific salary information for named individuals&#10;Escalate harassment complaints to HR leadership&#10;Do not make promises about employment decisions&#10;Protect employee PII at all times"
            />
          </div>
        </TabsContent>
      </Tabs>

      <DialogFooter className="mt-6">
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={!id.trim() || !name.trim()}>
          Create Agent
        </Button>
      </DialogFooter>
    </>
  );
}
