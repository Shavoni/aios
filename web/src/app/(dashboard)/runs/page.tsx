"use client";

import { useState } from "react";
import {
  Search,
  Filter,
  Download,
  ChevronLeft,
  ChevronRight,
  Eye,
  Play,
  Zap,
  Clock,
  DollarSign,
  TrendingUp,
  MessageSquare,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Bot,
  Activity,
  BarChart3,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { config } from "@/lib/config";

type HITLMode = "INFORM" | "DRAFT" | "ESCALATE";
type Domain = "Comms" | "Legal" | "HR" | "Finance" | "General";

interface Run {
  id: string;
  timestamp: string;
  domain: Domain;
  intent: string;
  requestText: string;
  hitlMode: HITLMode;
  tokens: number;
  cost: string;
  confidence: number;
  provider: string;
  responsePreview: string;
}

const mockRuns: Run[] = [
  {
    id: "run_001",
    timestamp: "2025-01-22 14:32:15",
    domain: "Comms",
    intent: "Draft press release",
    requestText: "Write a press release announcing our Q4 earnings...",
    hitlMode: "DRAFT",
    tokens: 1247,
    cost: "$0.024",
    confidence: 0.94,
    provider: "OpenAI",
    responsePreview: "[DRAFT] FOR IMMEDIATE RELEASE: Company announces record Q4...",
  },
  {
    id: "run_002",
    timestamp: "2025-01-22 14:28:42",
    domain: "Legal",
    intent: "Review NDA terms",
    requestText: "Review the non-compete clause in the attached NDA...",
    hitlMode: "ESCALATE",
    tokens: 892,
    cost: "$0.018",
    confidence: 0.87,
    provider: "OpenAI",
    responsePreview: "[ESCALATED] This request requires human review due to...",
  },
  {
    id: "run_003",
    timestamp: "2025-01-22 14:21:33",
    domain: "HR",
    intent: "Lookup employee benefits",
    requestText: "What are the dental benefits for employees in California?",
    hitlMode: "INFORM",
    tokens: 456,
    cost: "$0.009",
    confidence: 0.96,
    provider: "OpenAI",
    responsePreview: "California employees are eligible for Delta Dental PPO...",
  },
  {
    id: "run_004",
    timestamp: "2025-01-22 14:15:07",
    domain: "Finance",
    intent: "Generate budget report",
    requestText: "Generate a Q1 2025 budget forecast for the engineering team...",
    hitlMode: "DRAFT",
    tokens: 2103,
    cost: "$0.042",
    confidence: 0.91,
    provider: "OpenAI",
    responsePreview: "[DRAFT] Q1 2025 Engineering Budget Forecast: Total...",
  },
  {
    id: "run_005",
    timestamp: "2025-01-22 14:08:51",
    domain: "General",
    intent: "Research market trends",
    requestText: "What are the current trends in enterprise AI adoption?",
    hitlMode: "INFORM",
    tokens: 1567,
    cost: "$0.031",
    confidence: 0.89,
    provider: "OpenAI",
    responsePreview: "Enterprise AI adoption has accelerated significantly...",
  },
  {
    id: "run_006",
    timestamp: "2025-01-22 14:01:22",
    domain: "Comms",
    intent: "Social media response",
    requestText: "Draft a response to customer complaint on Twitter...",
    hitlMode: "DRAFT",
    tokens: 387,
    cost: "$0.008",
    confidence: 0.93,
    provider: "OpenAI",
    responsePreview: "[DRAFT] Hi @customer, we're sorry to hear about your...",
  },
  {
    id: "run_007",
    timestamp: "2025-01-22 13:55:18",
    domain: "Legal",
    intent: "Contract clause analysis",
    requestText: "Analyze the liability clause in the vendor agreement...",
    hitlMode: "ESCALATE",
    tokens: 1834,
    cost: "$0.037",
    confidence: 0.82,
    provider: "OpenAI",
    responsePreview: "[ESCALATED] This contract contains non-standard liability...",
  },
  {
    id: "run_008",
    timestamp: "2025-01-22 13:48:44",
    domain: "HR",
    intent: "Policy clarification",
    requestText: "What is our remote work policy for international employees?",
    hitlMode: "INFORM",
    tokens: 623,
    cost: "$0.012",
    confidence: 0.95,
    provider: "OpenAI",
    responsePreview: "International remote work is permitted with manager approval...",
  },
];

const hitlModeConfigs: Record<HITLMode, { bg: string; text: string; icon: React.ElementType }> = {
  INFORM: {
    bg: "bg-blue-100 dark:bg-blue-900/50",
    text: "text-blue-700 dark:text-blue-300",
    icon: CheckCircle,
  },
  DRAFT: {
    bg: "bg-amber-100 dark:bg-amber-900/50",
    text: "text-amber-700 dark:text-amber-300",
    icon: AlertTriangle,
  },
  ESCALATE: {
    bg: "bg-red-100 dark:bg-red-900/50",
    text: "text-red-700 dark:text-red-300",
    icon: XCircle,
  },
};

const domainConfigs: Record<Domain, { bg: string; text: string; gradient: string }> = {
  Comms: {
    bg: "bg-purple-100 dark:bg-purple-900/50",
    text: "text-purple-700 dark:text-purple-300",
    gradient: "from-purple-500 to-pink-500",
  },
  Legal: {
    bg: "bg-slate-100 dark:bg-slate-800/50",
    text: "text-slate-700 dark:text-slate-300",
    gradient: "from-slate-500 to-zinc-500",
  },
  HR: {
    bg: "bg-green-100 dark:bg-green-900/50",
    text: "text-green-700 dark:text-green-300",
    gradient: "from-green-500 to-emerald-500",
  },
  Finance: {
    bg: "bg-cyan-100 dark:bg-cyan-900/50",
    text: "text-cyan-700 dark:text-cyan-300",
    gradient: "from-cyan-500 to-blue-500",
  },
  General: {
    bg: "bg-gray-100 dark:bg-gray-800/50",
    text: "text-gray-700 dark:text-gray-300",
    gradient: "from-gray-500 to-slate-500",
  },
};

export default function RunsPage() {
  const [selectedRun, setSelectedRun] = useState<Run | null>(null);
  const [domainFilter, setDomainFilter] = useState<Domain[]>([]);
  const [hitlFilter, setHitlFilter] = useState<HITLMode[]>([]);
  const [searchQuery, setSearchQuery] = useState("");

  const filteredRuns = mockRuns.filter((run) => {
    if (domainFilter.length > 0 && !domainFilter.includes(run.domain)) {
      return false;
    }
    if (hitlFilter.length > 0 && !hitlFilter.includes(run.hitlMode)) {
      return false;
    }
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        run.intent.toLowerCase().includes(query) ||
        run.requestText.toLowerCase().includes(query) ||
        run.domain.toLowerCase().includes(query)
      );
    }
    return true;
  });

  const totalTokens = mockRuns.reduce((acc, run) => acc + run.tokens, 0);
  const totalCost = mockRuns.reduce((acc, run) => acc + parseFloat(run.cost.replace("$", "")), 0);
  const avgConfidence = mockRuns.reduce((acc, run) => acc + run.confidence, 0) / mockRuns.length;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Gradient Header */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-cyan-500 via-blue-600 to-indigo-600 p-8 text-white shadow-2xl">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDM0aDR2MmgtNHYtMnptMC04aDR2Nmg0djJoLTh2LTh6bTAgMTZoOHYyaC04di0yem0tMTYgMGg0djJoLTR2LTJ6bTAtOGg0djZoNHYyaC04di04em0wIDE2aDh2MmgtOHYtMnoiLz48L2c+PC9nPjwvc3ZnPg==')] opacity-30"></div>
        <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-white/10 blur-3xl"></div>
        <div className="absolute -bottom-20 -left-20 h-64 w-64 rounded-full bg-blue-300/20 blur-3xl"></div>
        <div className="relative">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/20 backdrop-blur-sm">
                  <Play className="h-7 w-7" />
                </div>
                <div>
                  <h1 className="text-3xl font-bold tracking-tight">Request History</h1>
                  <p className="text-cyan-100">AI Processing Analytics</p>
                </div>
              </div>
              <p className="mt-4 max-w-xl text-white/80">
                Track and analyze all AI requests processed by {config.appName}. Monitor performance,
                costs, and governance decisions across your organization.
              </p>
            </div>
            <div className="hidden lg:flex items-center gap-3">
              <Button
                variant="secondary"
                className="bg-white/20 hover:bg-white/30 border-0 text-white"
              >
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-cyan-50 to-blue-100 dark:from-cyan-950/50 dark:to-blue-900/30">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-cyan-500/20"></div>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-cyan-600/70 dark:text-cyan-400">Total Requests</p>
                <p className="text-3xl font-bold text-cyan-700 dark:text-cyan-300">{mockRuns.length}</p>
                <p className="text-xs text-cyan-600/60 dark:text-cyan-400/60 mt-1">Today</p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-cyan-500/20">
                <MessageSquare className="h-6 w-6 text-cyan-600 dark:text-cyan-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-purple-50 to-violet-100 dark:from-purple-950/50 dark:to-violet-900/30">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-purple-500/20"></div>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-purple-600/70 dark:text-purple-400">Total Tokens</p>
                <p className="text-3xl font-bold text-purple-700 dark:text-purple-300">
                  {totalTokens.toLocaleString()}
                </p>
                <p className="text-xs text-purple-600/60 dark:text-purple-400/60 mt-1">Processed</p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-purple-500/20">
                <Zap className="h-6 w-6 text-purple-600 dark:text-purple-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-green-50 to-emerald-100 dark:from-green-950/50 dark:to-emerald-900/30">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-green-500/20"></div>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-green-600/70 dark:text-green-400">Total Cost</p>
                <p className="text-3xl font-bold text-green-700 dark:text-green-300">
                  ${totalCost.toFixed(2)}
                </p>
                <p className="text-xs text-green-600/60 dark:text-green-400/60 mt-1">Today</p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-green-500/20">
                <DollarSign className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-amber-50 to-orange-100 dark:from-amber-950/50 dark:to-orange-900/30">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-amber-500/20"></div>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-amber-600/70 dark:text-amber-400">Avg Confidence</p>
                <p className="text-3xl font-bold text-amber-700 dark:text-amber-300">
                  {(avgConfidence * 100).toFixed(0)}%
                </p>
                <p className="text-xs text-amber-600/60 dark:text-amber-400/60 mt-1">Model accuracy</p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-500/20">
                <TrendingUp className="h-6 w-6 text-amber-600 dark:text-amber-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="border-0 shadow-lg">
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by intent, request, or domain..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 bg-muted/50"
              />
            </div>
            <div className="flex gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" className="bg-muted/50">
                    <Filter className="mr-2 h-4 w-4" />
                    Domain
                    {domainFilter.length > 0 && (
                      <Badge variant="secondary" className="ml-2 bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300">
                        {domainFilter.length}
                      </Badge>
                    )}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  {(["Comms", "Legal", "HR", "Finance", "General"] as Domain[]).map(
                    (domain) => (
                      <DropdownMenuCheckboxItem
                        key={domain}
                        checked={domainFilter.includes(domain)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setDomainFilter([...domainFilter, domain]);
                          } else {
                            setDomainFilter(domainFilter.filter((d) => d !== domain));
                          }
                        }}
                      >
                        <Badge className={`${domainConfigs[domain].bg} ${domainConfigs[domain].text} border-0`}>
                          {domain}
                        </Badge>
                      </DropdownMenuCheckboxItem>
                    )
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" className="bg-muted/50">
                    <Filter className="mr-2 h-4 w-4" />
                    HITL Mode
                    {hitlFilter.length > 0 && (
                      <Badge variant="secondary" className="ml-2 bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                        {hitlFilter.length}
                      </Badge>
                    )}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  {(["INFORM", "DRAFT", "ESCALATE"] as HITLMode[]).map((mode) => {
                    const config = hitlModeConfigs[mode];
                    return (
                      <DropdownMenuCheckboxItem
                        key={mode}
                        checked={hitlFilter.includes(mode)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setHitlFilter([...hitlFilter, mode]);
                          } else {
                            setHitlFilter(hitlFilter.filter((m) => m !== mode));
                          }
                        }}
                      >
                        <Badge className={`${config.bg} ${config.text} border-0`}>
                          {mode}
                        </Badge>
                      </DropdownMenuCheckboxItem>
                    );
                  })}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card className="border-0 shadow-lg">
        <CardHeader className="border-b bg-muted/30">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              All Requests
            </CardTitle>
            <Badge variant="outline" className="bg-muted/50">
              {filteredRuns.length} of {mockRuns.length}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/30">
                <TableHead>Timestamp</TableHead>
                <TableHead>Domain</TableHead>
                <TableHead className="hidden lg:table-cell">Intent</TableHead>
                <TableHead>HITL Mode</TableHead>
                <TableHead className="hidden md:table-cell">Confidence</TableHead>
                <TableHead className="hidden sm:table-cell text-right">Tokens</TableHead>
                <TableHead className="text-right">Cost</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRuns.map((run) => {
                const domainConfig = domainConfigs[run.domain];
                const hitlConfig = hitlModeConfigs[run.hitlMode];
                const HitlIcon = hitlConfig.icon;
                return (
                  <TableRow key={run.id} className="hover:bg-muted/50">
                    <TableCell className="font-mono text-sm">
                      {run.timestamp}
                    </TableCell>
                    <TableCell>
                      <Badge className={`${domainConfig.bg} ${domainConfig.text} border-0`}>
                        {run.domain}
                      </Badge>
                    </TableCell>
                    <TableCell className="hidden lg:table-cell max-w-[200px] truncate">
                      <span className="font-medium">{run.intent}</span>
                    </TableCell>
                    <TableCell>
                      <Badge className={`${hitlConfig.bg} ${hitlConfig.text} border-0`}>
                        <HitlIcon className="h-3 w-3 mr-1" />
                        {run.hitlMode}
                      </Badge>
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-2 rounded-full bg-muted overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              run.confidence >= 0.9
                                ? "bg-green-500"
                                : run.confidence >= 0.8
                                ? "bg-amber-500"
                                : "bg-red-500"
                            }`}
                            style={{ width: `${run.confidence * 100}%` }}
                          />
                        </div>
                        <span className={`text-sm font-medium ${
                          run.confidence >= 0.9
                            ? "text-green-600 dark:text-green-400"
                            : run.confidence >= 0.8
                            ? "text-amber-600 dark:text-amber-400"
                            : "text-red-600 dark:text-red-400"
                        }`}>
                          {(run.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="hidden sm:table-cell text-right font-mono">
                      {run.tokens.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right font-mono font-medium text-green-600 dark:text-green-400">
                      {run.cost}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setSelectedRun(run)}
                        className="hover:bg-primary/10"
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          {/* Pagination */}
          <div className="flex items-center justify-between p-4 border-t">
            <p className="text-sm text-muted-foreground">
              Showing {filteredRuns.length} of {mockRuns.length} requests
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled className="bg-muted/50">
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" disabled className="bg-muted/50">
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Detail Dialog */}
      <Dialog open={!!selectedRun} onOpenChange={() => setSelectedRun(null)}>
        <DialogContent className="max-w-2xl">
          {selectedRun && (
            <>
              <DialogHeader>
                <div className="flex items-center gap-3">
                  <div className={`flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${domainConfigs[selectedRun.domain].gradient} text-white shadow-lg`}>
                    <Bot className="h-6 w-6" />
                  </div>
                  <div>
                    <DialogTitle className="text-xl">Request Details</DialogTitle>
                    <p className="text-sm text-muted-foreground">{selectedRun.timestamp}</p>
                  </div>
                </div>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                <div className="flex flex-wrap gap-2">
                  <Badge className={`${domainConfigs[selectedRun.domain].bg} ${domainConfigs[selectedRun.domain].text} border-0`}>
                    {selectedRun.domain}
                  </Badge>
                  <Badge className={`${hitlModeConfigs[selectedRun.hitlMode].bg} ${hitlModeConfigs[selectedRun.hitlMode].text} border-0`}>
                    {selectedRun.hitlMode}
                  </Badge>
                  <Badge variant="outline" className="bg-muted/50">{selectedRun.provider}</Badge>
                </div>
                <Separator />
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-2 flex items-center gap-2">
                    <MessageSquare className="h-4 w-4" />
                    Request
                  </h4>
                  <p className="text-sm bg-muted/50 p-4 rounded-lg">{selectedRun.requestText}</p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-2 flex items-center gap-2">
                    <Bot className="h-4 w-4" />
                    Response Preview
                  </h4>
                  <p className="text-sm bg-gradient-to-br from-muted/50 to-muted p-4 rounded-lg border">
                    {selectedRun.responsePreview}
                  </p>
                </div>
                <Separator />
                <div className="grid grid-cols-4 gap-4">
                  <div className="text-center p-3 rounded-lg bg-purple-50 dark:bg-purple-950/30">
                    <div className="text-2xl font-bold text-purple-700 dark:text-purple-300">
                      {selectedRun.tokens.toLocaleString()}
                    </div>
                    <div className="text-xs text-purple-600/70 dark:text-purple-400">Tokens</div>
                  </div>
                  <div className="text-center p-3 rounded-lg bg-green-50 dark:bg-green-950/30">
                    <div className="text-2xl font-bold text-green-700 dark:text-green-300">{selectedRun.cost}</div>
                    <div className="text-xs text-green-600/70 dark:text-green-400">Cost</div>
                  </div>
                  <div className="text-center p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30">
                    <div className="text-2xl font-bold text-amber-700 dark:text-amber-300">
                      {(selectedRun.confidence * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-amber-600/70 dark:text-amber-400">Confidence</div>
                  </div>
                  <div className="text-center p-3 rounded-lg bg-blue-50 dark:bg-blue-950/30">
                    <div className="text-2xl font-bold text-blue-700 dark:text-blue-300">{selectedRun.provider}</div>
                    <div className="text-xs text-blue-600/70 dark:text-blue-400">Provider</div>
                  </div>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
