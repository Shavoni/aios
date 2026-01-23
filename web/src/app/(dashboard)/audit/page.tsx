"use client";

import { useState } from "react";
import {
  Search,
  Download,
  Filter,
  ChevronRight,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Clock,
  User,
  Bot,
  Shield,
  FileText,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface AuditEvent {
  id: string;
  timestamp: string;
  eventType: "request" | "policy_match" | "escalation" | "approval" | "rejection";
  userId: string;
  userRole: string;
  agent: string;
  action: string;
  details: {
    requestText?: string;
    intentClassified?: string;
    risksDetected?: string[];
    policyTriggered?: string;
    hitlMode?: string;
    approvedBy?: string;
    rejectionReason?: string;
  };
  outcome: "success" | "blocked" | "pending" | "escalated";
  ipAddress: string;
}

const mockAuditEvents: AuditEvent[] = [
  {
    id: "audit_001",
    timestamp: "2025-01-22 14:32:15.234",
    eventType: "request",
    userId: "jsmith@cleveland.gov",
    userRole: "HR Analyst",
    agent: "Matthew J. Cole",
    action: "Policy Guidance Request",
    details: {
      requestText: "What is the remote work policy for part-time employees?",
      intentClassified: "HR Policy Inquiry",
      risksDetected: [],
      policyTriggered: "HR-INFORM-001",
      hitlMode: "INFORM",
    },
    outcome: "success",
    ipAddress: "10.0.1.45",
  },
  {
    id: "audit_002",
    timestamp: "2025-01-22 14:28:42.891",
    eventType: "escalation",
    userId: "mwilliams@cleveland.gov",
    userRole: "Finance Manager",
    agent: "Ayesha Bell Hardaway",
    action: "Contract Review Escalated",
    details: {
      requestText: "Review vendor contract for IT services exceeding $500k",
      intentClassified: "Contract Review",
      risksDetected: ["high_value_contract", "legal_review_required"],
      policyTriggered: "FIN-ESCALATE-003",
      hitlMode: "ESCALATE",
    },
    outcome: "escalated",
    ipAddress: "10.0.2.112",
  },
  {
    id: "audit_003",
    timestamp: "2025-01-22 14:21:33.456",
    eventType: "policy_match",
    userId: "kjohnson@cleveland.gov",
    userRole: "Public Health Coordinator",
    agent: "Dr. David Margolius",
    action: "PHI Protection Triggered",
    details: {
      requestText: "Generate report on clinic patient outcomes",
      intentClassified: "Health Data Request",
      risksDetected: ["phi_detected", "hipaa_applicable"],
      policyTriggered: "HEALTH-LOCAL-001",
      hitlMode: "ESCALATE",
    },
    outcome: "blocked",
    ipAddress: "10.0.3.78",
  },
  {
    id: "audit_004",
    timestamp: "2025-01-22 14:15:07.123",
    eventType: "approval",
    userId: "dcole@cleveland.gov",
    userRole: "HR Director",
    agent: "Matthew J. Cole",
    action: "Draft Approved",
    details: {
      requestText: "Employee termination communication draft",
      intentClassified: "HR Communication",
      policyTriggered: "HR-DRAFT-002",
      hitlMode: "DRAFT",
      approvedBy: "dcole@cleveland.gov",
    },
    outcome: "success",
    ipAddress: "10.0.1.22",
  },
  {
    id: "audit_005",
    timestamp: "2025-01-22 14:08:51.789",
    eventType: "rejection",
    userId: "asmith@cleveland.gov",
    userRole: "311 Operator",
    agent: "Kate Connor Warren",
    action: "Response Rejected",
    details: {
      requestText: "Promise expedited service for council member request",
      intentClassified: "Service Request",
      risksDetected: ["preferential_treatment"],
      policyTriggered: "311-BLOCK-001",
      hitlMode: "ESCALATE",
      rejectionReason: "Cannot provide preferential treatment based on political status",
    },
    outcome: "blocked",
    ipAddress: "10.0.4.33",
  },
  {
    id: "audit_006",
    timestamp: "2025-01-22 14:01:22.567",
    eventType: "request",
    userId: "bthompson@cleveland.gov",
    userRole: "Building Inspector",
    agent: "Sally Martin O'Toole",
    action: "Code Reference Lookup",
    details: {
      requestText: "What are the setback requirements for residential construction?",
      intentClassified: "Code Inquiry",
      risksDetected: [],
      policyTriggered: "BLDG-INFORM-001",
      hitlMode: "INFORM",
    },
    outcome: "success",
    ipAddress: "10.0.5.91",
  },
];

const eventTypeIcons = {
  request: Clock,
  policy_match: Shield,
  escalation: AlertTriangle,
  approval: CheckCircle,
  rejection: XCircle,
};

const outcomeStyles = {
  success: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  blocked: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
  pending: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300",
  escalated: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300",
};

export default function AuditPage() {
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [eventTypeFilter, setEventTypeFilter] = useState<string[]>([]);

  const filteredEvents = mockAuditEvents.filter((event) => {
    if (eventTypeFilter.length > 0 && !eventTypeFilter.includes(event.eventType)) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Audit Log</h1>
          <p className="text-muted-foreground">
            CGI-compliant audit trail for all AI governance decisions
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <FileText className="mr-2 h-4 w-4" />
            Generate Report
          </Button>
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export CSV
          </Button>
        </div>
      </div>

      {/* Compliance Summary */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Events
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12,847</div>
            <p className="text-xs text-muted-foreground">Last 30 days</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Policy Enforcements
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2,341</div>
            <p className="text-xs text-muted-foreground">100% logged</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Escalations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">487</div>
            <p className="text-xs text-muted-foreground">All reviewed</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Retention Period
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">7 Years</div>
            <p className="text-xs text-muted-foreground">CGI compliant</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input placeholder="Search by user, agent, or action..." className="pl-9" />
            </div>
            <div className="flex gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Filter className="mr-2 h-4 w-4" />
                    Event Type
                    {eventTypeFilter.length > 0 && (
                      <Badge variant="secondary" className="ml-2">
                        {eventTypeFilter.length}
                      </Badge>
                    )}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  {["request", "policy_match", "escalation", "approval", "rejection"].map(
                    (type) => (
                      <DropdownMenuCheckboxItem
                        key={type}
                        checked={eventTypeFilter.includes(type)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setEventTypeFilter([...eventTypeFilter, type]);
                          } else {
                            setEventTypeFilter(eventTypeFilter.filter((t) => t !== type));
                          }
                        }}
                      >
                        {type.replace("_", " ")}
                      </DropdownMenuCheckboxItem>
                    )
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
              <Input type="date" className="w-auto" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Audit Table */}
      <Card>
        <CardHeader>
          <CardTitle>Audit Events</CardTitle>
          <CardDescription>
            Complete record of all AI interactions and governance decisions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Agent</TableHead>
                <TableHead className="hidden md:table-cell">Action</TableHead>
                <TableHead>Policy</TableHead>
                <TableHead>Outcome</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredEvents.map((event) => {
                const EventIcon = eventTypeIcons[event.eventType];
                return (
                  <TableRow key={event.id}>
                    <TableCell className="font-mono text-xs">
                      {event.timestamp}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <User className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <div className="font-medium text-sm">{event.userId}</div>
                          <div className="text-xs text-muted-foreground">
                            {event.userRole}
                          </div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Bot className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">{event.agent}</span>
                      </div>
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      <div className="flex items-center gap-2">
                        <EventIcon className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">{event.action}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="font-mono text-xs">
                        {event.details.policyTriggered}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className={outcomeStyles[event.outcome]}>
                        {event.outcome}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setSelectedEvent(event)}
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Event Detail Dialog */}
      <Dialog open={!!selectedEvent} onOpenChange={() => setSelectedEvent(null)}>
        <DialogContent className="max-w-2xl">
          {selectedEvent && (
            <>
              <DialogHeader>
                <DialogTitle>Audit Event Details</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                {/* Header Info */}
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">{selectedEvent.eventType.replace("_", " ")}</Badge>
                  <Badge variant="secondary" className={outcomeStyles[selectedEvent.outcome]}>
                    {selectedEvent.outcome}
                  </Badge>
                  {selectedEvent.details.hitlMode && (
                    <Badge variant="outline">{selectedEvent.details.hitlMode}</Badge>
                  )}
                </div>

                <Separator />

                {/* Event Metadata */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Event ID</p>
                    <p className="font-mono">{selectedEvent.id}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Timestamp</p>
                    <p className="font-mono">{selectedEvent.timestamp}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">User</p>
                    <p>{selectedEvent.userId}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Role</p>
                    <p>{selectedEvent.userRole}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">IP Address</p>
                    <p className="font-mono">{selectedEvent.ipAddress}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Agent</p>
                    <p>{selectedEvent.agent}</p>
                  </div>
                </div>

                <Separator />

                {/* Request Details */}
                {selectedEvent.details.requestText && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-1">
                      Original Request
                    </p>
                    <p className="text-sm bg-muted p-3 rounded-lg">
                      {selectedEvent.details.requestText}
                    </p>
                  </div>
                )}

                {/* Decision Chain */}
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-2">
                    Decision Chain
                  </p>
                  <div className="space-y-2">
                    {selectedEvent.details.intentClassified && (
                      <div className="flex items-center gap-2 text-sm">
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span>Intent: {selectedEvent.details.intentClassified}</span>
                      </div>
                    )}
                    {selectedEvent.details.risksDetected && selectedEvent.details.risksDetected.length > 0 && (
                      <div className="flex items-center gap-2 text-sm">
                        <AlertTriangle className="h-4 w-4 text-amber-500" />
                        <span>Risks: {selectedEvent.details.risksDetected.join(", ")}</span>
                      </div>
                    )}
                    {selectedEvent.details.policyTriggered && (
                      <div className="flex items-center gap-2 text-sm">
                        <Shield className="h-4 w-4 text-blue-500" />
                        <span>Policy: {selectedEvent.details.policyTriggered}</span>
                      </div>
                    )}
                    {selectedEvent.details.approvedBy && (
                      <div className="flex items-center gap-2 text-sm">
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span>Approved by: {selectedEvent.details.approvedBy}</span>
                      </div>
                    )}
                    {selectedEvent.details.rejectionReason && (
                      <div className="flex items-center gap-2 text-sm">
                        <XCircle className="h-4 w-4 text-red-500" />
                        <span>Rejection: {selectedEvent.details.rejectionReason}</span>
                      </div>
                    )}
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
