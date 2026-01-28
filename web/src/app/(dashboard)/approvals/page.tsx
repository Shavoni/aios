"use client";

import { useEffect, useState } from "react";
import {
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Shield,
  User,
  Bot,
  Loader2,
  RefreshCw,
  Inbox,
  Timer,
  TrendingUp,
  Eye,
  MessageSquare,
  Sparkles,
  ChevronRight,
  CheckSquare,
  Square,
  ListChecks,
  Filter,
  Download,
  Search,
  Calendar,
  ArrowUpDown,
  UserPlus,
  Globe,
  ExternalLink,
  CheckCheck,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  getApprovalQueue,
  listPendingApprovals,
  approveRequest,
  rejectRequest,
  listPendingAgents,
  approvePendingAgent,
  rejectPendingAgent,
  approveAllPendingAgents,
  type ApprovalQueue,
  type ApprovalRequest,
  type PendingAgent,
} from "@/lib/api";
import { config } from "@/lib/config";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const priorityConfig = {
  urgent: {
    label: "Urgent",
    color: "bg-red-500/10 text-red-600 border-red-300",
    gradient: "from-red-500 to-rose-500",
  },
  high: {
    label: "High",
    color: "bg-orange-500/10 text-orange-600 border-orange-300",
    gradient: "from-orange-500 to-amber-500",
  },
  normal: {
    label: "Normal",
    color: "bg-blue-500/10 text-blue-600 border-blue-300",
    gradient: "from-blue-500 to-indigo-500",
  },
  low: {
    label: "Low",
    color: "bg-gray-500/10 text-gray-600 border-gray-300",
    gradient: "from-gray-400 to-gray-500",
  },
};

const modeConfig = {
  DRAFT: {
    label: "Draft",
    color: "bg-yellow-500/10 text-yellow-700 border-yellow-300",
    icon: MessageSquare,
  },
  EXECUTE: {
    label: "Execute",
    color: "bg-purple-500/10 text-purple-700 border-purple-300",
    icon: Sparkles,
  },
  ESCALATE: {
    label: "Escalate",
    color: "bg-red-500/10 text-red-700 border-red-300",
    icon: AlertTriangle,
  },
  INFORM: {
    label: "Inform",
    color: "bg-green-500/10 text-green-700 border-green-300",
    icon: CheckCircle,
  },
};

// Calculate SLA status based on created time
function getSlaStatus(createdAt: string, priority: string): { status: "ok" | "warning" | "breach"; timeLeft: string } {
  const created = new Date(createdAt);
  const now = new Date();
  const hoursElapsed = (now.getTime() - created.getTime()) / (1000 * 60 * 60);

  // SLA thresholds by priority (hours)
  const slaThresholds: Record<string, number> = {
    urgent: 1,
    high: 4,
    normal: 24,
    low: 72,
  };

  const threshold = slaThresholds[priority] || 24;
  const percentUsed = (hoursElapsed / threshold) * 100;
  const hoursLeft = threshold - hoursElapsed;

  let timeLeft: string;
  if (hoursLeft < 0) {
    timeLeft = `${Math.abs(Math.round(hoursLeft))}h overdue`;
  } else if (hoursLeft < 1) {
    timeLeft = `${Math.round(hoursLeft * 60)}m left`;
  } else {
    timeLeft = `${Math.round(hoursLeft)}h left`;
  }

  if (percentUsed >= 100) return { status: "breach", timeLeft };
  if (percentUsed >= 75) return { status: "warning", timeLeft };
  return { status: "ok", timeLeft };
}

export default function ApprovalsPage() {
  const [queue, setQueue] = useState<ApprovalQueue | null>(null);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedApproval, setSelectedApproval] = useState<ApprovalRequest | null>(null);
  const [reviewNotes, setReviewNotes] = useState("");
  const [modifiedResponse, setModifiedResponse] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");
  const [processing, setProcessing] = useState(false);
  const [filterPriority, setFilterPriority] = useState<string>("all");

  // Pending Agents state
  const [activeTab, setActiveTab] = useState<"responses" | "agents">("responses");
  const [pendingAgentsList, setPendingAgentsList] = useState<PendingAgent[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(false);
  const [selectedAgentIds, setSelectedAgentIds] = useState<Set<string>>(new Set());
  const [processingAgents, setProcessingAgents] = useState(false);
  const [agentRejectReason, setAgentRejectReason] = useState("");
  const [showAgentRejectDialog, setShowAgentRejectDialog] = useState(false);
  const [agentToReject, setAgentToReject] = useState<PendingAgent | null>(null);

  // Batch selection state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchProcessing, setBatchProcessing] = useState(false);
  const [showBatchDialog, setShowBatchDialog] = useState(false);
  const [batchAction, setBatchAction] = useState<"approve" | "reject">("approve");
  const [batchReason, setBatchReason] = useState("");

  // Additional filters
  const [filterMode, setFilterMode] = useState<string>("all");
  const [filterAgent, setFilterAgent] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<"created_at" | "priority">("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  async function loadData() {
    try {
      setLoading(true);
      const [queueData, approvalsData] = await Promise.all([
        getApprovalQueue(),
        listPendingApprovals(100),
      ]);
      setQueue(queueData);
      setApprovals(approvalsData.approvals);
    } catch (error) {
      console.error("Failed to load approvals:", error);
      toast.error("Failed to load approval queue");
    } finally {
      setLoading(false);
    }
  }

  async function loadPendingAgents() {
    try {
      setLoadingAgents(true);
      const data = await listPendingAgents();
      setPendingAgentsList(data.pending.filter(a => a.status === "pending"));
    } catch (error) {
      console.error("Failed to load pending agents:", error);
      toast.error("Failed to load pending agents");
    } finally {
      setLoadingAgents(false);
    }
  }

  async function handleApproveAgent(pending: PendingAgent) {
    setProcessingAgents(true);
    try {
      await approvePendingAgent(pending.pending_id);
      toast.success(`Agent "${pending.agent.name}" approved and created`);
      loadPendingAgents();
    } catch (error) {
      console.error("Failed to approve agent:", error);
      toast.error("Failed to approve agent");
    } finally {
      setProcessingAgents(false);
    }
  }

  async function handleRejectAgent() {
    if (!agentToReject) return;
    setProcessingAgents(true);
    try {
      await rejectPendingAgent(agentToReject.pending_id, agentRejectReason);
      toast.success(`Agent "${agentToReject.agent.name}" rejected`);
      setShowAgentRejectDialog(false);
      setAgentToReject(null);
      setAgentRejectReason("");
      loadPendingAgents();
    } catch (error) {
      console.error("Failed to reject agent:", error);
      toast.error("Failed to reject agent");
    } finally {
      setProcessingAgents(false);
    }
  }

  async function handleApproveAllAgents() {
    if (pendingAgentsList.length === 0) return;
    setProcessingAgents(true);
    try {
      const result = await approveAllPendingAgents();
      toast.success(`Approved ${result.approved} agent(s)`);
      loadPendingAgents();
    } catch (error) {
      console.error("Failed to approve all agents:", error);
      toast.error("Failed to approve all agents");
    } finally {
      setProcessingAgents(false);
    }
  }

  function toggleAgentSelection(id: string) {
    const newSet = new Set(selectedAgentIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedAgentIds(newSet);
  }

  function toggleAllAgents() {
    if (selectedAgentIds.size === pendingAgentsList.length) {
      setSelectedAgentIds(new Set());
    } else {
      setSelectedAgentIds(new Set(pendingAgentsList.map(a => a.pending_id)));
    }
  }

  useEffect(() => {
    loadData();
    loadPendingAgents();
  }, []);

  async function handleApprove() {
    if (!selectedApproval) return;
    setProcessing(true);
    try {
      await approveRequest(
        selectedApproval.id,
        "admin",
        reviewNotes || undefined,
        modifiedResponse !== selectedApproval.proposed_response ? modifiedResponse : undefined
      );
      toast.success("Request approved successfully");
      setSelectedApproval(null);
      setReviewNotes("");
      setModifiedResponse("");
      loadData();
    } catch (error) {
      console.error("Failed to approve:", error);
      toast.error("Failed to approve request");
    } finally {
      setProcessing(false);
    }
  }

  async function handleReject() {
    if (!selectedApproval || !rejectionReason.trim()) {
      toast.error("Rejection reason is required");
      return;
    }
    setProcessing(true);
    try {
      await rejectRequest(selectedApproval.id, "admin", rejectionReason);
      toast.success("Request rejected");
      setSelectedApproval(null);
      setRejectionReason("");
      loadData();
    } catch (error) {
      console.error("Failed to reject:", error);
      toast.error("Failed to reject request");
    } finally {
      setProcessing(false);
    }
  }

  // Batch handlers
  function toggleSelectAll() {
    if (selectedIds.size === filteredApprovals.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredApprovals.map((a) => a.id)));
    }
  }

  function toggleSelectOne(id: string) {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedIds(newSet);
  }

  async function handleBatchAction() {
    if (selectedIds.size === 0) return;

    setBatchProcessing(true);
    let successCount = 0;
    let failCount = 0;

    for (const id of selectedIds) {
      try {
        if (batchAction === "approve") {
          await approveRequest(id, "admin", batchReason || undefined);
        } else {
          await rejectRequest(id, "admin", batchReason || "Batch rejection");
        }
        successCount++;
      } catch {
        failCount++;
      }
    }

    setBatchProcessing(false);
    setShowBatchDialog(false);
    setBatchReason("");
    setSelectedIds(new Set());

    if (successCount > 0) {
      toast.success(`${batchAction === "approve" ? "Approved" : "Rejected"} ${successCount} request(s)`);
    }
    if (failCount > 0) {
      toast.error(`Failed to process ${failCount} request(s)`);
    }
    loadData();
  }

  // Export handlers
  function exportToCsv() {
    const headers = ["ID", "Created", "Priority", "Mode", "Agent", "User", "Department", "Query", "Response"];
    const rows = filteredApprovals.map((a) => [
      a.id,
      new Date(a.created_at).toISOString(),
      a.priority,
      a.hitl_mode,
      a.agent_name,
      a.user_id,
      a.user_department,
      `"${a.original_query.replace(/"/g, '""')}"`,
      `"${a.proposed_response.replace(/"/g, '""')}"`,
    ]);

    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `approvals-${new Date().toISOString().split("T")[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
    toast.success("Exported to CSV");
  }

  // Get unique agents for filter
  const uniqueAgents = [...new Set(approvals.map((a) => a.agent_name))];

  // Enhanced filtering with search, mode, and agent
  const filteredApprovals = approvals
    .filter((a) => filterPriority === "all" || a.priority === filterPriority)
    .filter((a) => filterMode === "all" || a.hitl_mode === filterMode)
    .filter((a) => filterAgent === "all" || a.agent_name === filterAgent)
    .filter((a) =>
      searchQuery === "" ||
      a.original_query.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.user_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.user_department.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .sort((a, b) => {
      if (sortField === "priority") {
        const priorityOrder = { urgent: 0, high: 1, normal: 2, low: 3 };
        const diff = priorityOrder[a.priority] - priorityOrder[b.priority];
        return sortOrder === "asc" ? diff : -diff;
      }
      const diff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      return sortOrder === "asc" ? diff : -diff;
    });

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Loading approval queue...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header with Gradient */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-amber-500 via-orange-500 to-red-500 p-6 text-white shadow-xl">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDM0aDR2MmgtNHYtMnptMC04aDR2Nmg0djJoLTh2LTh6bTAgMTZoOHYyaC04di0yem0tMTYgMGg0djJoLTR2LTJ6bTAtOGg0djZoNHYyaC04di04em0wIDE2aDh2Mmgtxdi0yeiIvPjwvZz48L2c+PC9zdmc+')] opacity-30"></div>
        <div className="relative">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/20 backdrop-blur-sm">
                <CheckCircle className="h-8 w-8" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight">Approval Queue</h1>
                <p className="text-white/80">Human-in-the-loop review for {config.appName}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                onClick={exportToCsv}
                variant="secondary"
                className="bg-white/20 text-white hover:bg-white/30 border-0"
              >
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
              <Button
                onClick={() => { loadData(); loadPendingAgents(); }}
                variant="secondary"
                className="bg-white/20 text-white hover:bg-white/30 border-0"
              >
                <RefreshCw className={`mr-2 h-4 w-4 ${loading || loadingAgents ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="flex gap-2 border-b">
        <button
          onClick={() => setActiveTab("responses")}
          className={cn(
            "flex items-center gap-2 px-4 py-2 border-b-2 transition-colors",
            activeTab === "responses"
              ? "border-orange-500 text-orange-600 font-medium"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          <MessageSquare className="h-4 w-4" />
          Response Approvals
          {approvals.length > 0 && (
            <Badge variant="secondary" className="ml-1">{approvals.length}</Badge>
          )}
        </button>
        <button
          onClick={() => setActiveTab("agents")}
          className={cn(
            "flex items-center gap-2 px-4 py-2 border-b-2 transition-colors",
            activeTab === "agents"
              ? "border-orange-500 text-orange-600 font-medium"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          <UserPlus className="h-4 w-4" />
          Pending Agents
          {pendingAgentsList.length > 0 && (
            <Badge variant="destructive" className="ml-1 animate-pulse">{pendingAgentsList.length}</Badge>
          )}
        </button>
      </div>

      {/* Pending Agents Tab Content */}
      {activeTab === "agents" && (
        <div className="space-y-4">
          {/* Agents Summary */}
          <Card className="border-0 shadow-md bg-gradient-to-r from-violet-50 to-purple-50 dark:from-violet-950/30 dark:to-purple-950/30">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/20">
                    <UserPlus className="h-5 w-5 text-violet-600" />
                  </div>
                  <div>
                    <p className="font-medium">Agents Awaiting Approval</p>
                    <p className="text-sm text-muted-foreground">
                      {pendingAgentsList.length} agent(s) discovered from onboarding need your approval before they are created
                    </p>
                  </div>
                </div>
                {pendingAgentsList.length > 0 && (
                  <Button
                    onClick={handleApproveAllAgents}
                    disabled={processingAgents}
                    className="bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600"
                  >
                    {processingAgents ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <CheckCheck className="mr-2 h-4 w-4" />
                    )}
                    Approve All ({pendingAgentsList.length})
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Pending Agents List */}
          <Card className="border-0 shadow-lg">
            <CardHeader className="border-b bg-muted/30">
              <CardTitle className="flex items-center gap-2 text-lg">
                <Bot className="h-5 w-5 text-muted-foreground" />
                Discovered Agents
              </CardTitle>
              <CardDescription>
                Review agents discovered during onboarding and approve to add them to your system
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {loadingAgents ? (
                <div className="flex items-center justify-center py-16">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : pendingAgentsList.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16">
                  <div className="flex h-20 w-20 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
                    <CheckCircle className="h-10 w-10 text-green-600" />
                  </div>
                  <h3 className="mt-4 text-lg font-semibold">No Pending Agents</h3>
                  <p className="text-muted-foreground">All discovered agents have been reviewed.</p>
                </div>
              ) : (
                <div className="divide-y">
                  {pendingAgentsList.map((pending, index) => (
                    <div
                      key={pending.pending_id}
                      className="group flex items-start gap-4 p-4 hover:bg-muted/50 transition-colors animate-in fade-in"
                      style={{ animationDelay: `${index * 50}ms` }}
                    >
                      {/* Agent Icon */}
                      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 text-white shadow-md">
                        <Bot className="h-6 w-6" />
                      </div>

                      {/* Agent Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold">{pending.agent.name}</span>
                          {pending.agent.title && (
                            <Badge variant="secondary">{pending.agent.title}</Badge>
                          )}
                          <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                            {pending.agent.domain}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground line-clamp-2 mb-2">
                          {pending.agent.description || "No description provided"}
                        </p>
                        <div className="flex flex-wrap gap-1 mb-2">
                          {pending.agent.capabilities?.slice(0, 3).map((cap) => (
                            <Badge key={cap} variant="outline" className="text-xs">
                              {cap}
                            </Badge>
                          ))}
                          {pending.agent.capabilities && pending.agent.capabilities.length > 3 && (
                            <Badge variant="outline" className="text-xs">
                              +{pending.agent.capabilities.length - 3} more
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Globe className="h-3 w-3" />
                            {pending.source}
                          </span>
                          {pending.agent.gpt_url && (
                            <a
                              href={pending.agent.gpt_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1 hover:text-foreground"
                            >
                              <Sparkles className="h-3 w-3" />
                              Custom GPT
                            </a>
                          )}
                          <span>
                            {new Date(pending.submitted_at).toLocaleString()}
                          </span>
                        </div>
                        {pending.agent.guardrails && pending.agent.guardrails.length > 0 && (
                          <div className="flex items-center gap-1 mt-2">
                            <Shield className="h-3 w-3 text-amber-600" />
                            <span className="text-xs text-amber-600">
                              {pending.agent.guardrails.length} guardrail(s) configured
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2 shrink-0">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setAgentToReject(pending);
                            setShowAgentRejectDialog(true);
                          }}
                          className="border-red-200 text-red-600 hover:bg-red-50"
                        >
                          <XCircle className="h-4 w-4 mr-1" />
                          Reject
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleApproveAgent(pending)}
                          disabled={processingAgents}
                          className="bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600"
                        >
                          {processingAgents ? (
                            <Loader2 className="h-4 w-4 animate-spin mr-1" />
                          ) : (
                            <CheckCircle className="h-4 w-4 mr-1" />
                          )}
                          Approve
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Response Approvals Tab Content */}
      {activeTab === "responses" && (
        <>
          {/* Queue Summary */}
          {queue && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950/50 dark:to-blue-900/30">
            <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-blue-500/20"></div>
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/20">
                  <Inbox className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-blue-600/70">Pending</p>
                  <p className="text-3xl font-bold text-blue-700">{queue.pending_count}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-red-50 to-red-100 dark:from-red-950/50 dark:to-red-900/30">
            <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-red-500/20"></div>
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-500/20">
                  <AlertTriangle className="h-6 w-6 text-red-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-red-600/70">Urgent</p>
                  <p className="text-3xl font-bold text-red-700">{queue.pending_by_priority.urgent || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-950/50 dark:to-purple-900/30">
            <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-purple-500/20"></div>
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-purple-500/20">
                  <Shield className="h-6 w-6 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-purple-600/70">Escalated</p>
                  <p className="text-3xl font-bold text-purple-700">{queue.pending_by_mode.ESCALATE || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950/50 dark:to-green-900/30">
            <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-green-500/20"></div>
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-green-500/20">
                  <Timer className="h-6 w-6 text-green-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-green-600/70">Avg Resolution</p>
                  <p className="text-3xl font-bold text-green-700">
                    {queue.avg_resolution_time_hrs ? `${queue.avg_resolution_time_hrs.toFixed(1)}h` : "N/A"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Enhanced Filters Bar */}
      <Card className="border-0 shadow-md">
        <CardContent className="p-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            {/* Search and Filters */}
            <div className="flex flex-1 flex-wrap items-center gap-2">
              <div className="relative flex-1 min-w-[200px] max-w-xs">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search queries, users..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>

              <Select value={filterPriority} onValueChange={setFilterPriority}>
                <SelectTrigger className="w-[130px]">
                  <SelectValue placeholder="Priority" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Priority</SelectItem>
                  <SelectItem value="urgent">Urgent</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="normal">Normal</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>

              <Select value={filterMode} onValueChange={setFilterMode}>
                <SelectTrigger className="w-[130px]">
                  <SelectValue placeholder="Mode" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Modes</SelectItem>
                  <SelectItem value="INFORM">Inform</SelectItem>
                  <SelectItem value="DRAFT">Draft</SelectItem>
                  <SelectItem value="EXECUTE">Execute</SelectItem>
                  <SelectItem value="ESCALATE">Escalate</SelectItem>
                </SelectContent>
              </Select>

              <Select value={filterAgent} onValueChange={setFilterAgent}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Agent" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Agents</SelectItem>
                  {uniqueAgents.map((agent) => (
                    <SelectItem key={agent} value={agent}>{agent}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Button
                variant="outline"
                size="icon"
                onClick={() => setSortOrder(sortOrder === "asc" ? "desc" : "asc")}
                title={`Sort ${sortOrder === "asc" ? "descending" : "ascending"}`}
              >
                <ArrowUpDown className="h-4 w-4" />
              </Button>
            </div>

            {/* Stats Summary */}
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-2">
                <Badge variant="destructive" className="animate-pulse">
                  {approvals.filter((a) => a.priority === "urgent").length}
                </Badge>
                <span className="text-muted-foreground">urgent</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="secondary">
                  {filteredApprovals.length}
                </Badge>
                <span className="text-muted-foreground">filtered</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Batch Action Toolbar */}
      {selectedIds.size > 0 && (
        <Card className="border-0 shadow-md bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/50 dark:to-indigo-950/50 animate-in slide-in-from-top duration-300">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <ListChecks className="h-5 w-5 text-blue-600" />
                <span className="font-medium">{selectedIds.size} selected</span>
                <Button variant="link" size="sm" onClick={() => setSelectedIds(new Set())}>
                  Clear selection
                </Button>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setBatchAction("reject");
                    setShowBatchDialog(true);
                  }}
                  className="border-red-200 text-red-600 hover:bg-red-50"
                >
                  <XCircle className="mr-2 h-4 w-4" />
                  Reject All
                </Button>
                <Button
                  onClick={() => {
                    setBatchAction("approve");
                    setShowBatchDialog(true);
                  }}
                  className="bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600"
                >
                  <CheckCircle className="mr-2 h-4 w-4" />
                  Approve All
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Approval List */}
      <Card className="border-0 shadow-lg">
        <CardHeader className="border-b bg-muted/30">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Eye className="h-5 w-5 text-muted-foreground" />
                Pending Reviews
              </CardTitle>
              <CardDescription>
                Review and approve or reject AI-generated responses
              </CardDescription>
            </div>
            {filteredApprovals.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={toggleSelectAll}
                className="gap-2"
              >
                {selectedIds.size === filteredApprovals.length ? (
                  <>
                    <CheckSquare className="h-4 w-4" />
                    Deselect All
                  </>
                ) : (
                  <>
                    <Square className="h-4 w-4" />
                    Select All ({filteredApprovals.length})
                  </>
                )}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {filteredApprovals.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="flex h-20 w-20 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
                <CheckCircle className="h-10 w-10 text-green-600" />
              </div>
              <h3 className="mt-4 text-lg font-semibold">All caught up!</h3>
              <p className="text-muted-foreground">No pending approvals at this time.</p>
            </div>
          ) : (
            <div className="divide-y">
              {filteredApprovals.map((approval, index) => {
                const priority = priorityConfig[approval.priority];
                const mode = modeConfig[approval.hitl_mode];
                const ModeIcon = mode.icon;
                const sla = getSlaStatus(approval.created_at, approval.priority);
                const isSelected = selectedIds.has(approval.id);

                return (
                  <div
                    key={approval.id}
                    className={cn(
                      "group flex items-start gap-4 p-4 hover:bg-muted/50 transition-colors",
                      approval.priority === "urgent" && "bg-red-50/50 dark:bg-red-950/10",
                      isSelected && "bg-blue-50/50 dark:bg-blue-950/20 border-l-4 border-l-blue-500",
                      sla.status === "breach" && "border-l-4 border-l-red-500"
                    )}
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    {/* Checkbox */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleSelectOne(approval.id);
                      }}
                      className="shrink-0 mt-1"
                    >
                      {isSelected ? (
                        <CheckSquare className="h-5 w-5 text-blue-600" />
                      ) : (
                        <Square className="h-5 w-5 text-muted-foreground hover:text-foreground" />
                      )}
                    </button>

                    {/* Priority Indicator */}
                    <div
                      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br ${priority.gradient} text-white shadow-sm cursor-pointer`}
                      onClick={() => {
                        setSelectedApproval(approval);
                        setModifiedResponse(approval.proposed_response);
                      }}
                    >
                      <ModeIcon className="h-5 w-5" />
                    </div>

                    {/* Content */}
                    <div
                      className="flex-1 min-w-0 cursor-pointer"
                      onClick={() => {
                        setSelectedApproval(approval);
                        setModifiedResponse(approval.proposed_response);
                      }}
                    >
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <Badge variant="outline" className={mode.color}>
                          {mode.label}
                        </Badge>
                        <Badge variant="outline" className={priority.color}>
                          {priority.label}
                        </Badge>
                        <Badge variant="secondary">{approval.agent_name}</Badge>
                        {approval.risk_signals.length > 0 && (
                          <Badge variant="destructive" className="text-xs">
                            {approval.risk_signals.length} risk{approval.risk_signals.length > 1 ? "s" : ""}
                          </Badge>
                        )}
                        {/* SLA Indicator */}
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-xs font-mono",
                            sla.status === "ok" && "bg-green-50 text-green-700 border-green-200",
                            sla.status === "warning" && "bg-amber-50 text-amber-700 border-amber-200",
                            sla.status === "breach" && "bg-red-50 text-red-700 border-red-200 animate-pulse"
                          )}
                        >
                          <Clock className="h-3 w-3 mr-1" />
                          {sla.timeLeft}
                        </Badge>
                      </div>
                      <p className="font-medium text-sm mb-1 line-clamp-1">{approval.original_query}</p>
                      <p className="text-sm text-muted-foreground line-clamp-2">{approval.proposed_response}</p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <User className="h-3 w-3" />
                          {approval.user_id}
                        </span>
                        <span>{approval.user_department}</span>
                        <span>{new Date(approval.created_at).toLocaleString()}</span>
                      </div>
                    </div>

                    {/* Action Button */}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => {
                        setSelectedApproval(approval);
                        setModifiedResponse(approval.proposed_response);
                      }}
                    >
                      Review
                      <ChevronRight className="ml-1 h-4 w-4" />
                    </Button>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Review Dialog */}
      <Dialog open={!!selectedApproval} onOpenChange={() => setSelectedApproval(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
          {selectedApproval && (
            <>
              <DialogHeader>
                <div className="flex items-center gap-3">
                  <div className={`flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${priorityConfig[selectedApproval.priority].gradient} text-white shadow-lg`}>
                    {(() => {
                      const ModeIcon = modeConfig[selectedApproval.hitl_mode].icon;
                      return <ModeIcon className="h-6 w-6" />;
                    })()}
                  </div>
                  <div>
                    <DialogTitle>Review Request</DialogTitle>
                    <DialogDescription className="flex items-center gap-2 mt-1">
                      <Badge variant="outline" className={modeConfig[selectedApproval.hitl_mode].color}>
                        {modeConfig[selectedApproval.hitl_mode].label}
                      </Badge>
                      <Badge variant="outline" className={priorityConfig[selectedApproval.priority].color}>
                        {priorityConfig[selectedApproval.priority].label}
                      </Badge>
                    </DialogDescription>
                  </div>
                </div>
              </DialogHeader>

              <ScrollArea className="flex-1 pr-4 -mr-4">
                <div className="space-y-4 py-4">
                  {/* Risk Signals */}
                  {selectedApproval.risk_signals.length > 0 && (
                    <div className="p-4 bg-red-50 dark:bg-red-950/30 rounded-xl border border-red-200 dark:border-red-900">
                      <p className="font-medium text-red-800 dark:text-red-300 mb-2 flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4" />
                        Risk Signals Detected
                      </p>
                      <div className="flex gap-2 flex-wrap">
                        {selectedApproval.risk_signals.map((signal) => (
                          <Badge key={signal} variant="destructive">{signal}</Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Escalation Reason */}
                  {selectedApproval.escalation_reason && (
                    <div className="p-4 bg-amber-50 dark:bg-amber-950/30 rounded-xl border border-amber-200 dark:border-amber-900">
                      <p className="font-medium text-amber-800 dark:text-amber-300">Escalation Reason:</p>
                      <p className="text-amber-700 dark:text-amber-400">{selectedApproval.escalation_reason}</p>
                    </div>
                  )}

                  {/* User Query */}
                  <div>
                    <label className="text-sm font-medium flex items-center gap-2 mb-2">
                      <User className="h-4 w-4" />
                      User Query
                    </label>
                    <div className="p-4 bg-muted rounded-xl">
                      <p className="text-sm">{selectedApproval.original_query}</p>
                      <div className="flex items-center gap-3 mt-3 text-xs text-muted-foreground">
                        <span>{selectedApproval.user_id}</span>
                        <span>|</span>
                        <span>{selectedApproval.user_department}</span>
                        <span>|</span>
                        <span>{new Date(selectedApproval.created_at).toLocaleString()}</span>
                      </div>
                    </div>
                  </div>

                  {/* AI Response (Editable) */}
                  <div>
                    <label className="text-sm font-medium flex items-center gap-2 mb-2">
                      <Bot className="h-4 w-4" />
                      AI Response
                      <span className="text-muted-foreground font-normal">(editable)</span>
                    </label>
                    <Textarea
                      value={modifiedResponse}
                      onChange={(e) => setModifiedResponse(e.target.value)}
                      rows={6}
                      className="font-mono text-sm"
                    />
                    {modifiedResponse !== selectedApproval.proposed_response && (
                      <p className="text-xs text-amber-600 mt-1">Response has been modified</p>
                    )}
                  </div>

                  {/* Review Notes */}
                  <div>
                    <label className="text-sm font-medium mb-2 block">Review Notes (optional)</label>
                    <Textarea
                      value={reviewNotes}
                      onChange={(e) => setReviewNotes(e.target.value)}
                      placeholder="Add notes about your decision..."
                      rows={2}
                    />
                  </div>

                  {/* Rejection Reason */}
                  <div>
                    <label className="text-sm font-medium mb-2 block text-red-600">
                      Rejection Reason (required if rejecting)
                    </label>
                    <Textarea
                      value={rejectionReason}
                      onChange={(e) => setRejectionReason(e.target.value)}
                      placeholder="Why is this response being rejected?"
                      rows={2}
                      className="border-red-200 focus:border-red-400"
                    />
                  </div>
                </div>
              </ScrollArea>

              <DialogFooter className="flex gap-2 pt-4 border-t">
                <Button variant="outline" onClick={() => setSelectedApproval(null)}>
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleReject}
                  disabled={processing || !rejectionReason.trim()}
                >
                  {processing ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <XCircle className="h-4 w-4 mr-2" />
                  )}
                  Reject
                </Button>
                <Button
                  onClick={handleApprove}
                  disabled={processing}
                  className="bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600"
                >
                  {processing ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <CheckCircle className="h-4 w-4 mr-2" />
                  )}
                  {modifiedResponse !== selectedApproval.proposed_response ? "Approve (Modified)" : "Approve"}
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Batch Action Dialog */}
      <Dialog open={showBatchDialog} onOpenChange={setShowBatchDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {batchAction === "approve" ? (
                <>
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  Batch Approve
                </>
              ) : (
                <>
                  <XCircle className="h-5 w-5 text-red-500" />
                  Batch Reject
                </>
              )}
            </DialogTitle>
            <DialogDescription>
              {batchAction === "approve"
                ? `Approve ${selectedIds.size} selected request(s) at once.`
                : `Reject ${selectedIds.size} selected request(s). A reason is required.`}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium mb-2 block">
                {batchAction === "approve" ? "Notes (optional)" : "Rejection Reason (required)"}
              </label>
              <Textarea
                value={batchReason}
                onChange={(e) => setBatchReason(e.target.value)}
                placeholder={
                  batchAction === "approve"
                    ? "Add notes for these approvals..."
                    : "Why are these being rejected?"
                }
                rows={3}
              />
            </div>

            <div className="p-3 rounded-lg bg-muted">
              <p className="text-sm font-medium mb-2">Selected Items ({selectedIds.size}):</p>
              <div className="max-h-32 overflow-y-auto space-y-1">
                {Array.from(selectedIds).slice(0, 5).map((id) => {
                  const approval = approvals.find((a) => a.id === id);
                  return approval ? (
                    <div key={id} className="text-xs text-muted-foreground truncate">
                      {approval.original_query.slice(0, 50)}...
                    </div>
                  ) : null;
                })}
                {selectedIds.size > 5 && (
                  <p className="text-xs text-muted-foreground">
                    +{selectedIds.size - 5} more items
                  </p>
                )}
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBatchDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleBatchAction}
              disabled={batchProcessing || (batchAction === "reject" && !batchReason.trim())}
              className={
                batchAction === "approve"
                  ? "bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600"
                  : "bg-gradient-to-r from-red-500 to-rose-500 hover:from-red-600 hover:to-rose-600"
              }
            >
              {batchProcessing ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : batchAction === "approve" ? (
                <CheckCircle className="h-4 w-4 mr-2" />
              ) : (
                <XCircle className="h-4 w-4 mr-2" />
              )}
              {batchAction === "approve" ? "Approve All" : "Reject All"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
        </>
      )}

      {/* Reject Agent Dialog */}
      <Dialog open={showAgentRejectDialog} onOpenChange={setShowAgentRejectDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <XCircle className="h-5 w-5 text-red-500" />
              Reject Agent
            </DialogTitle>
            <DialogDescription>
              {agentToReject && (
                <>Reject &quot;{agentToReject.agent.name}&quot;? This agent will not be created.</>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium mb-2 block">
                Rejection Reason (optional)
              </label>
              <Textarea
                value={agentRejectReason}
                onChange={(e) => setAgentRejectReason(e.target.value)}
                placeholder="Why is this agent being rejected?"
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAgentRejectDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleRejectAgent}
              disabled={processingAgents}
              className="bg-gradient-to-r from-red-500 to-rose-500 hover:from-red-600 hover:to-rose-600"
            >
              {processingAgents ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <XCircle className="h-4 w-4 mr-2" />
              )}
              Reject Agent
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
