"use client";

import { useState } from "react";
import {
  Search,
  Filter,
  Download,
  ChevronLeft,
  ChevronRight,
  Eye,
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

const hitlModeStyles: Record<HITLMode, string> = {
  INFORM: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  DRAFT: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300",
  ESCALATE: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
};

const domainStyles: Record<Domain, string> = {
  Comms: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300",
  Legal: "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300",
  HR: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  Finance: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-300",
  General: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300",
};

export default function RunsPage() {
  const [selectedRun, setSelectedRun] = useState<Run | null>(null);
  const [domainFilter, setDomainFilter] = useState<Domain[]>([]);
  const [hitlFilter, setHitlFilter] = useState<HITLMode[]>([]);

  const filteredRuns = mockRuns.filter((run) => {
    if (domainFilter.length > 0 && !domainFilter.includes(run.domain)) {
      return false;
    }
    if (hitlFilter.length > 0 && !hitlFilter.includes(run.hitlMode)) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Request History</h1>
          <p className="text-muted-foreground">
            View and analyze all processed requests
          </p>
        </div>
        <Button variant="outline">
          <Download className="mr-2 h-4 w-4" />
          Export
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input placeholder="Search requests..." className="pl-9" />
            </div>
            <div className="flex gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Filter className="mr-2 h-4 w-4" />
                    Domain
                    {domainFilter.length > 0 && (
                      <Badge variant="secondary" className="ml-2">
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
                        {domain}
                      </DropdownMenuCheckboxItem>
                    )
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Filter className="mr-2 h-4 w-4" />
                    HITL Mode
                    {hitlFilter.length > 0 && (
                      <Badge variant="secondary" className="ml-2">
                        {hitlFilter.length}
                      </Badge>
                    )}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  {(["INFORM", "DRAFT", "ESCALATE"] as HITLMode[]).map((mode) => (
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
                      {mode}
                    </DropdownMenuCheckboxItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle>All Requests</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
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
              {filteredRuns.map((run) => (
                <TableRow key={run.id}>
                  <TableCell className="font-mono text-sm">
                    {run.timestamp}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className={domainStyles[run.domain]}>
                      {run.domain}
                    </Badge>
                  </TableCell>
                  <TableCell className="hidden lg:table-cell max-w-[200px] truncate">
                    {run.intent}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className={hitlModeStyles[run.hitlMode]}>
                      {run.hitlMode}
                    </Badge>
                  </TableCell>
                  <TableCell className="hidden md:table-cell">
                    <span className={run.confidence >= 0.9 ? "text-green-600" : run.confidence >= 0.8 ? "text-amber-600" : "text-red-600"}>
                      {(run.confidence * 100).toFixed(0)}%
                    </span>
                  </TableCell>
                  <TableCell className="hidden sm:table-cell text-right font-mono">
                    {run.tokens.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {run.cost}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setSelectedRun(run)}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {/* Pagination */}
          <div className="flex items-center justify-between pt-4">
            <p className="text-sm text-muted-foreground">
              Showing {filteredRuns.length} of {mockRuns.length} requests
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" disabled>
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
                <DialogTitle>Request Details</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  <Badge variant="secondary" className={domainStyles[selectedRun.domain]}>
                    {selectedRun.domain}
                  </Badge>
                  <Badge variant="secondary" className={hitlModeStyles[selectedRun.hitlMode]}>
                    {selectedRun.hitlMode}
                  </Badge>
                  <Badge variant="outline">{selectedRun.provider}</Badge>
                </div>
                <Separator />
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-1">
                    Request
                  </h4>
                  <p className="text-sm">{selectedRun.requestText}</p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-1">
                    Response Preview
                  </h4>
                  <p className="text-sm bg-muted p-3 rounded-lg">
                    {selectedRun.responsePreview}
                  </p>
                </div>
                <Separator />
                <div className="grid grid-cols-4 gap-4 text-center">
                  <div>
                    <div className="text-lg font-semibold">{selectedRun.tokens}</div>
                    <div className="text-xs text-muted-foreground">Tokens</div>
                  </div>
                  <div>
                    <div className="text-lg font-semibold">{selectedRun.cost}</div>
                    <div className="text-xs text-muted-foreground">Cost</div>
                  </div>
                  <div>
                    <div className="text-lg font-semibold">
                      {(selectedRun.confidence * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-muted-foreground">Confidence</div>
                  </div>
                  <div>
                    <div className="text-lg font-semibold">{selectedRun.provider}</div>
                    <div className="text-xs text-muted-foreground">Provider</div>
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
