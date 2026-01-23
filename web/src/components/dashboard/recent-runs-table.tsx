"use client";

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

type HITLMode = "INFORM" | "DRAFT" | "ESCALATE";
type Domain = "Router" | "PublicHealth" | "HR" | "Finance" | "Building" | "311" | "Strategy" | "Regional";

interface Run {
  id: string;
  time: string;
  agent: string;
  domain: Domain;
  intent: string;
  hitlMode: HITLMode;
  tokens: number;
  cost: string;
}

const mockRuns: Run[] = [
  {
    id: "run_001",
    time: "2 min ago",
    agent: "Matthew J. Cole",
    domain: "HR",
    intent: "Benefits policy clarification",
    hitlMode: "INFORM",
    tokens: 847,
    cost: "$0.017",
  },
  {
    id: "run_002",
    time: "5 min ago",
    agent: "Ayesha Bell Hardaway",
    domain: "Finance",
    intent: "Vendor contract review",
    hitlMode: "ESCALATE",
    tokens: 1292,
    cost: "$0.026",
  },
  {
    id: "run_003",
    time: "8 min ago",
    agent: "Dr. David Margolius",
    domain: "PublicHealth",
    intent: "Public advisory draft",
    hitlMode: "DRAFT",
    tokens: 2156,
    cost: "$0.043",
  },
  {
    id: "run_004",
    time: "12 min ago",
    agent: "Kate Connor Warren",
    domain: "311",
    intent: "Service request routing",
    hitlMode: "INFORM",
    tokens: 456,
    cost: "$0.009",
  },
  {
    id: "run_005",
    time: "15 min ago",
    agent: "Sally Martin O'Toole",
    domain: "Building",
    intent: "Permit guidance",
    hitlMode: "INFORM",
    tokens: 678,
    cost: "$0.014",
  },
  {
    id: "run_006",
    time: "22 min ago",
    agent: "Dr. Elizabeth Crowe",
    domain: "Strategy",
    intent: "Pilot decision memo",
    hitlMode: "DRAFT",
    tokens: 1834,
    cost: "$0.037",
  },
  {
    id: "run_007",
    time: "28 min ago",
    agent: "Civic AI Concierge",
    domain: "Router",
    intent: "Department routing",
    hitlMode: "INFORM",
    tokens: 234,
    cost: "$0.005",
  },
];

const hitlModeStyles: Record<HITLMode, string> = {
  INFORM: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  DRAFT: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300",
  ESCALATE: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
};

const domainStyles: Record<Domain, string> = {
  Router: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300",
  Strategy: "bg-violet-100 text-violet-800 dark:bg-violet-900 dark:text-violet-300",
  PublicHealth: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
  HR: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  Finance: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-300",
  Building: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300",
  "311": "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  Regional: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300",
};

export function RecentRunsTable() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Requests</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead>Agent</TableHead>
              <TableHead className="hidden md:table-cell">Intent</TableHead>
              <TableHead>HITL Mode</TableHead>
              <TableHead className="hidden sm:table-cell text-right">Tokens</TableHead>
              <TableHead className="text-right">Cost</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {mockRuns.map((run) => (
              <TableRow key={run.id} className="cursor-pointer hover:bg-muted/50">
                <TableCell className="text-muted-foreground">
                  {run.time}
                </TableCell>
                <TableCell>
                  <div className="flex flex-col gap-1">
                    <span className="font-medium text-sm">{run.agent}</span>
                    <Badge variant="secondary" className={`${domainStyles[run.domain]} w-fit text-xs`}>
                      {run.domain}
                    </Badge>
                  </div>
                </TableCell>
                <TableCell className="hidden md:table-cell max-w-[200px] truncate">
                  {run.intent}
                </TableCell>
                <TableCell>
                  <Badge variant="secondary" className={hitlModeStyles[run.hitlMode]}>
                    {run.hitlMode}
                  </Badge>
                </TableCell>
                <TableCell className="hidden sm:table-cell text-right font-mono text-sm">
                  {run.tokens.toLocaleString()}
                </TableCell>
                <TableCell className="text-right font-mono text-sm">
                  {run.cost}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
