"use client";

import { useEffect, useState } from "react";
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
  Loader2,
  RefreshCw,
  Eye,
  FileSearch,
  Scale,
  Lock,
  AlertCircle,
  Activity,
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
import {
  getAuditSummary,
  listAuditEvents,
  type AuditEvent,
  type AuditSummary,
} from "@/lib/api";
import { config } from "@/lib/config";
import { toast } from "sonner";

const severityConfigs: Record<string, { bg: string; text: string; icon: React.ElementType }> = {
  INFO: {
    bg: "bg-blue-100 dark:bg-blue-900/50",
    text: "text-blue-700 dark:text-blue-300",
    icon: AlertCircle,
  },
  WARNING: {
    bg: "bg-amber-100 dark:bg-amber-900/50",
    text: "text-amber-700 dark:text-amber-300",
    icon: AlertTriangle,
  },
  ALERT: {
    bg: "bg-orange-100 dark:bg-orange-900/50",
    text: "text-orange-700 dark:text-orange-300",
    icon: AlertTriangle,
  },
  CRITICAL: {
    bg: "bg-red-100 dark:bg-red-900/50",
    text: "text-red-700 dark:text-red-300",
    icon: XCircle,
  },
};

const eventTypeIcons: Record<string, React.ElementType> = {
  query: Clock,
  policy_trigger: Shield,
  escalation: AlertTriangle,
  approval: CheckCircle,
  rejection: XCircle,
  error: XCircle,
};

export default function AuditPage() {
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  async function loadData() {
    try {
      setLoading(true);
      const [summaryData, eventsData] = await Promise.all([
        getAuditSummary(startDate || undefined, endDate || undefined),
        listAuditEvents({
          startDate: startDate || undefined,
          endDate: endDate || undefined,
          severity: severityFilter.length === 1 ? severityFilter[0] : undefined,
          limit: 100,
        }),
      ]);
      setSummary(summaryData);
      setEvents(eventsData.events);
    } catch (error) {
      console.error("Failed to load audit data:", error);
      toast.error("Failed to load audit data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [startDate, endDate]);

  const filteredEvents = events.filter((event) => {
    if (severityFilter.length > 0 && !severityFilter.includes(event.severity)) {
      return false;
    }
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        event.user_id.toLowerCase().includes(query) ||
        event.agent_name?.toLowerCase().includes(query) ||
        event.action.toLowerCase().includes(query) ||
        event.event_type.toLowerCase().includes(query)
      );
    }
    return true;
  });

  async function handleExport() {
    const headers = ["Timestamp", "Event Type", "Severity", "User", "Department", "Agent", "Action", "PII Detected", "Guardrails Triggered"];
    const rows = filteredEvents.map((e) => [
      e.timestamp,
      e.event_type,
      e.severity,
      e.user_id,
      e.user_department,
      e.agent_name || "",
      e.action,
      e.pii_detected.join("; "),
      e.guardrails_triggered.join("; "),
    ]);

    const csv = [headers.join(","), ...rows.map((r) => r.map((c) => `"${c}"`).join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-log-${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Audit log exported");
  }

  if (loading && events.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Gradient Header */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-red-500 via-rose-600 to-pink-600 p-8 text-white shadow-2xl">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDM0aDR2MmgtNHYtMnptMC04aDR2Nmg0djJoLTh2LTh6bTAgMTZoOHYyaC04di0yem0tMTYgMGg0djJoLTR2LTJ6bTAtOGg0djZoNHYyaC04di04em0wIDE2aDh2MmgtOHYtMnoiLz48L2c+PC9nPjwvc3ZnPg==')] opacity-30"></div>
        <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-white/10 blur-3xl"></div>
        <div className="absolute -bottom-20 -left-20 h-64 w-64 rounded-full bg-pink-300/20 blur-3xl"></div>
        <div className="relative">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/20 backdrop-blur-sm">
                  <FileSearch className="h-7 w-7" />
                </div>
                <div>
                  <h1 className="text-3xl font-bold tracking-tight">Audit Log</h1>
                  <p className="text-red-100">Governance & Compliance Trail</p>
                </div>
              </div>
              <p className="mt-4 max-w-xl text-white/80">
                Complete audit trail for {config.appName} governance decisions. Track policy triggers,
                PII detections, and human oversight actions.
              </p>
            </div>
            <div className="hidden lg:flex items-center gap-3">
              <Button
                variant="secondary"
                className="bg-white/20 hover:bg-white/30 border-0 text-white"
                onClick={loadData}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh
              </Button>
              <Button
                variant="secondary"
                className="bg-white/20 hover:bg-white/30 border-0 text-white"
                onClick={handleExport}
              >
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      {summary && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950/50 dark:to-slate-900/30">
            <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-slate-500/20"></div>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600/70 dark:text-slate-400">Total Events</p>
                  <p className="text-3xl font-bold text-slate-700 dark:text-slate-300">
                    {summary.total_events.toLocaleString()}
                  </p>
                  <p className="text-xs text-slate-600/60 dark:text-slate-400/60 mt-1">
                    {summary.period_start ? `Since ${new Date(summary.period_start).toLocaleDateString()}` : "All time"}
                  </p>
                </div>
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-500/20">
                  <Activity className="h-6 w-6 text-slate-600 dark:text-slate-400" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-amber-50 to-orange-100 dark:from-amber-950/50 dark:to-orange-900/30">
            <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-amber-500/20"></div>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-amber-600/70 dark:text-amber-400">PII Detections</p>
                  <p className="text-3xl font-bold text-amber-700 dark:text-amber-300">
                    {summary.pii_detections.toLocaleString()}
                  </p>
                  <p className="text-xs text-amber-600/60 dark:text-amber-400/60 mt-1">Protected data flagged</p>
                </div>
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-500/20">
                  <Lock className="h-6 w-6 text-amber-600 dark:text-amber-400" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-blue-950/50 dark:to-indigo-900/30">
            <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-blue-500/20"></div>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-blue-600/70 dark:text-blue-400">Guardrail Triggers</p>
                  <p className="text-3xl font-bold text-blue-700 dark:text-blue-300">
                    {summary.guardrail_triggers.toLocaleString()}
                  </p>
                  <p className="text-xs text-blue-600/60 dark:text-blue-400/60 mt-1">Policy enforcements</p>
                </div>
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/20">
                  <Shield className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-red-50 to-rose-100 dark:from-red-950/50 dark:to-rose-900/30">
            <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-red-500/20"></div>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-red-600/70 dark:text-red-400">Pending Review</p>
                  <p className="text-3xl font-bold text-red-700 dark:text-red-300">{summary.pending_review}</p>
                  <p className="text-xs text-red-600/60 dark:text-red-400/60 mt-1">Requires attention</p>
                </div>
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-500/20">
                  <Scale className="h-6 w-6 text-red-600 dark:text-red-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Event Type Distribution */}
      {summary && Object.keys(summary.events_by_type).length > 0 && (
        <Card className="border-0 shadow-lg">
          <CardHeader className="border-b bg-muted/30">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary" />
              Events by Type
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="flex flex-wrap gap-2">
              {Object.entries(summary.events_by_type).map(([type, count]) => {
                const Icon = eventTypeIcons[type] || Clock;
                return (
                  <Badge key={type} variant="outline" className="text-sm py-1.5 px-3 bg-muted/50">
                    <Icon className="h-3 w-3 mr-1.5" />
                    {type}: <span className="font-bold ml-1">{count}</span>
                  </Badge>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card className="border-0 shadow-lg">
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by user, agent, or action..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 bg-muted/50"
              />
            </div>
            <div className="flex gap-2 flex-wrap">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" className="bg-muted/50">
                    <Filter className="mr-2 h-4 w-4" />
                    Severity
                    {severityFilter.length > 0 && (
                      <Badge variant="secondary" className="ml-2 bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300">
                        {severityFilter.length}
                      </Badge>
                    )}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  {["INFO", "WARNING", "ALERT", "CRITICAL"].map((severity) => {
                    const config = severityConfigs[severity];
                    return (
                      <DropdownMenuCheckboxItem
                        key={severity}
                        checked={severityFilter.includes(severity)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setSeverityFilter([...severityFilter, severity]);
                          } else {
                            setSeverityFilter(severityFilter.filter((s) => s !== severity));
                          }
                        }}
                      >
                        <Badge className={`${config.bg} ${config.text} border-0`}>
                          {severity}
                        </Badge>
                      </DropdownMenuCheckboxItem>
                    );
                  })}
                </DropdownMenuContent>
              </DropdownMenu>
              <Input
                type="date"
                className="w-auto bg-muted/50"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                placeholder="Start date"
              />
              <Input
                type="date"
                className="w-auto bg-muted/50"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                placeholder="End date"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Audit Table */}
      <Card className="border-0 shadow-lg">
        <CardHeader className="border-b bg-muted/30">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" />
                Audit Events
              </CardTitle>
              <CardDescription>
                {filteredEvents.length} events shown
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {filteredEvents.length === 0 ? (
            <div className="text-center py-16">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-red-500 to-rose-500 text-white mx-auto mb-4">
                <FileText className="h-8 w-8" />
              </div>
              <h3 className="text-xl font-semibold mb-2">No audit events</h3>
              <p className="text-muted-foreground">
                No events match your current filters
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/30">
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead className="hidden md:table-cell">Agent</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredEvents.map((event) => {
                  const EventIcon = eventTypeIcons[event.event_type] || Clock;
                  const severityConfig = severityConfigs[event.severity] || severityConfigs.INFO;
                  return (
                    <TableRow key={event.id} className="hover:bg-muted/50">
                      <TableCell className="font-mono text-xs">
                        {new Date(event.timestamp).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-muted">
                            <EventIcon className="h-4 w-4 text-muted-foreground" />
                          </div>
                          <span className="text-sm font-medium">{event.event_type}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-slate-200 to-slate-300 dark:from-slate-700 dark:to-slate-800">
                            <User className="h-4 w-4 text-slate-600 dark:text-slate-400" />
                          </div>
                          <div>
                            <div className="font-medium text-sm">{event.user_id}</div>
                            <div className="text-xs text-muted-foreground">
                              {event.user_department}
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="hidden md:table-cell">
                        {event.agent_name && (
                          <div className="flex items-center gap-2">
                            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10">
                              <Bot className="h-4 w-4 text-primary" />
                            </div>
                            <span className="text-sm">{event.agent_name}</span>
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className="text-sm line-clamp-1 max-w-[200px]">{event.action}</span>
                      </TableCell>
                      <TableCell>
                        <Badge className={`${severityConfig.bg} ${severityConfig.text} border-0`}>
                          {event.severity}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setSelectedEvent(event)}
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
          )}
        </CardContent>
      </Card>

      {/* Event Detail Dialog */}
      <Dialog open={!!selectedEvent} onOpenChange={() => setSelectedEvent(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          {selectedEvent && (
            <>
              <DialogHeader>
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-red-500 to-rose-500 text-white shadow-lg">
                    <FileSearch className="h-6 w-6" />
                  </div>
                  <div>
                    <DialogTitle className="text-xl">Audit Event Details</DialogTitle>
                    <p className="text-sm text-muted-foreground">
                      {new Date(selectedEvent.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                {/* Header Info */}
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline" className="bg-muted/50">{selectedEvent.event_type}</Badge>
                  <Badge className={`${severityConfigs[selectedEvent.severity]?.bg} ${severityConfigs[selectedEvent.severity]?.text} border-0`}>
                    {selectedEvent.severity}
                  </Badge>
                  {selectedEvent.requires_review && (
                    <Badge className="bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300 border-0">
                      Requires Review
                    </Badge>
                  )}
                </div>

                <Separator />

                {/* Event Metadata */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="rounded-lg bg-muted/50 p-3">
                    <p className="text-muted-foreground text-xs">Event ID</p>
                    <p className="font-mono text-xs mt-1">{selectedEvent.id}</p>
                  </div>
                  <div className="rounded-lg bg-muted/50 p-3">
                    <p className="text-muted-foreground text-xs">Timestamp</p>
                    <p className="font-mono text-xs mt-1">{new Date(selectedEvent.timestamp).toLocaleString()}</p>
                  </div>
                  <div className="rounded-lg bg-muted/50 p-3">
                    <p className="text-muted-foreground text-xs">User</p>
                    <p className="font-medium mt-1">{selectedEvent.user_id}</p>
                  </div>
                  <div className="rounded-lg bg-muted/50 p-3">
                    <p className="text-muted-foreground text-xs">Department</p>
                    <p className="font-medium mt-1">{selectedEvent.user_department}</p>
                  </div>
                  {selectedEvent.agent_id && (
                    <div className="rounded-lg bg-muted/50 p-3">
                      <p className="text-muted-foreground text-xs">Agent ID</p>
                      <p className="font-mono text-xs mt-1">{selectedEvent.agent_id}</p>
                    </div>
                  )}
                  {selectedEvent.agent_name && (
                    <div className="rounded-lg bg-muted/50 p-3">
                      <p className="text-muted-foreground text-xs">Agent Name</p>
                      <p className="font-medium mt-1">{selectedEvent.agent_name}</p>
                    </div>
                  )}
                </div>

                <Separator />

                {/* Action */}
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-2 flex items-center gap-2">
                    <Activity className="h-4 w-4" />
                    Action
                  </p>
                  <p className="text-sm bg-muted/50 p-4 rounded-lg">
                    {selectedEvent.action}
                  </p>
                </div>

                {/* Details */}
                {Object.keys(selectedEvent.details).length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-2">
                      Details
                    </p>
                    <div className="bg-slate-900 dark:bg-slate-950 p-4 rounded-lg font-mono text-xs overflow-x-auto text-green-400">
                      <pre>{JSON.stringify(selectedEvent.details, null, 2)}</pre>
                    </div>
                  </div>
                )}

                {/* PII Detected */}
                {selectedEvent.pii_detected.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-2 flex items-center gap-2">
                      <div className="flex h-6 w-6 items-center justify-center rounded-md bg-amber-100 dark:bg-amber-900">
                        <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                      </div>
                      PII Detected
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {selectedEvent.pii_detected.map((pii) => (
                        <Badge key={pii} className="bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300 border-0">
                          {pii}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Guardrails Triggered */}
                {selectedEvent.guardrails_triggered.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-2 flex items-center gap-2">
                      <div className="flex h-6 w-6 items-center justify-center rounded-md bg-blue-100 dark:bg-blue-900">
                        <Shield className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                      </div>
                      Guardrails Triggered
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {selectedEvent.guardrails_triggered.map((guard) => (
                        <Badge key={guard} className="bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 border-0">
                          {guard}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Reviewed By */}
                {selectedEvent.reviewed_by && (
                  <div className="flex items-center gap-2 text-sm bg-green-50 dark:bg-green-950/30 p-3 rounded-lg">
                    <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
                    <span className="text-green-700 dark:text-green-300">
                      Reviewed by: <span className="font-medium">{selectedEvent.reviewed_by}</span>
                    </span>
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
