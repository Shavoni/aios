"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  Users,
  Clock,
  DollarSign,
  TrendingUp,
  AlertTriangle,
  Shield,
  BarChart3,
  Loader2,
  RefreshCw,
  Zap,
  Target,
  PieChart,
  ArrowUpRight,
  ArrowDownRight,
  Sparkles,
  Download,
  Calendar,
  FileSpreadsheet,
  FileText,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { getAnalyticsSummary, type AnalyticsSummary } from "@/lib/api";
import { config } from "@/lib/config";
import { toast } from "sonner";

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState("30");

  async function loadAnalytics() {
    try {
      setLoading(true);
      const data = await getAnalyticsSummary(Number(period));
      setAnalytics(data);
    } catch (error) {
      console.error("Failed to load analytics:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAnalytics();
  }, [period]);

  // Export functions
  function exportToCsv() {
    if (!analytics) return;

    const rows = [
      ["Metric", "Value"],
      ["Total Queries (30d)", analytics.total_queries_30d.toString()],
      ["Total Queries (7d)", analytics.total_queries_7d.toString()],
      ["Total Queries Today", analytics.total_queries_today.toString()],
      ["Unique Users (30d)", analytics.unique_users_30d.toString()],
      ["Unique Users Today", analytics.unique_users_today.toString()],
      ["Success Rate", `${analytics.success_rate.toFixed(1)}%`],
      ["Escalation Rate", `${analytics.escalation_rate.toFixed(1)}%`],
      ["Avg Latency (ms)", analytics.avg_latency_ms.toFixed(0)],
      ["P95 Latency (ms)", analytics.p95_latency_ms.toFixed(0)],
      ["Total Cost (30d)", `$${analytics.total_cost_30d.toFixed(2)}`],
      ["Estimated Savings", `$${analytics.estimated_savings.toFixed(2)}`],
      ["Guardrails Enforced", analytics.guardrails_enforced.toString()],
      ["Total Tokens (30d)", analytics.total_tokens_30d.toString()],
      [],
      ["Top Agents"],
      ["Agent ID", "Queries"],
      ...analytics.top_agents.map(a => [a.agent_id, a.queries.toString()]),
      [],
      ["Top Departments"],
      ["Department", "Queries"],
      ...analytics.top_departments.map(d => [d.department, d.queries.toString()]),
      [],
      ["Daily Queries"],
      ["Date", "Queries"],
      ...analytics.daily_queries.map(d => [d.date, d.queries.toString()]),
    ];

    const csv = rows.map(r => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `analytics-${period}d-${new Date().toISOString().split("T")[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
    toast.success("Analytics exported to CSV");
  }

  function exportToJson() {
    if (!analytics) return;

    const json = JSON.stringify(analytics, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `analytics-${period}d-${new Date().toISOString().split("T")[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
    toast.success("Analytics exported to JSON");
  }

  function printReport() {
    window.print();
    toast.success("Print dialog opened");
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Loading analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header with Gradient */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-cyan-600 via-blue-600 to-indigo-600 p-6 text-white shadow-xl">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDM0aDR2MmgtNHYtMnptMC04aDR2Nmg0djJoLTh2LTh6bTAgMTZoOHYyaC04di0yem0tMTYgMGg0djJoLTR2LTJ6bTAtOGg0djZoNHYyaC04di04em0wIDE2aDh2Mmgtxdi0yeiIvPjwvZz48L2c+PC9zdmc+')] opacity-30"></div>
        <div className="relative">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/20 backdrop-blur-sm">
                <BarChart3 className="h-8 w-8" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight">Analytics Dashboard</h1>
                <p className="text-white/80">Performance metrics and usage insights for {config.appName}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Select value={period} onValueChange={setPeriod}>
                <SelectTrigger className="w-40 bg-white/10 border-white/20 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="7">Last 7 days</SelectItem>
                  <SelectItem value="30">Last 30 days</SelectItem>
                  <SelectItem value="90">Last 90 days</SelectItem>
                </SelectContent>
              </Select>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="secondary"
                    className="bg-white/20 text-white hover:bg-white/30 border-0"
                    disabled={!analytics}
                  >
                    <Download className="mr-2 h-4 w-4" />
                    Export
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={exportToCsv}>
                    <FileSpreadsheet className="mr-2 h-4 w-4" />
                    Export as CSV
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={exportToJson}>
                    <FileText className="mr-2 h-4 w-4" />
                    Export as JSON
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={printReport}>
                    <FileText className="mr-2 h-4 w-4" />
                    Print Report
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              <Button
                onClick={loadAnalytics}
                variant="secondary"
                className="bg-white/20 text-white hover:bg-white/30 border-0"
              >
                <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </div>
          </div>
        </div>
      </div>

      {analytics && (
        <>
          {/* Primary KPI Cards */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-violet-50 to-violet-100 dark:from-violet-950/50 dark:to-violet-900/30">
              <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-violet-500/20"></div>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-violet-600/70">Total Queries</p>
                    <p className="text-3xl font-bold text-violet-700">{analytics.total_queries_30d.toLocaleString()}</p>
                    <div className="mt-1 flex items-center gap-1 text-xs">
                      <span className="flex items-center text-green-600">
                        <ArrowUpRight className="h-3 w-3" />
                        {analytics.total_queries_today}
                      </span>
                      <span className="text-muted-foreground">today</span>
                    </div>
                  </div>
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-violet-500/20">
                    <Activity className="h-6 w-6 text-violet-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-950/50 dark:to-emerald-900/30">
              <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-emerald-500/20"></div>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-emerald-600/70">Unique Users</p>
                    <p className="text-3xl font-bold text-emerald-700">{analytics.unique_users_30d.toLocaleString()}</p>
                    <div className="mt-1 flex items-center gap-1 text-xs">
                      <span className="flex items-center text-green-600">
                        <Users className="h-3 w-3 mr-1" />
                        {analytics.unique_users_today}
                      </span>
                      <span className="text-muted-foreground">active today</span>
                    </div>
                  </div>
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/20">
                    <Users className="h-6 w-6 text-emerald-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-amber-50 to-amber-100 dark:from-amber-950/50 dark:to-amber-900/30">
              <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-amber-500/20"></div>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-amber-600/70">Avg Response</p>
                    <p className="text-3xl font-bold text-amber-700">{Math.round(analytics.avg_latency_ms)}ms</p>
                    <div className="mt-1 flex items-center gap-1 text-xs">
                      <span className="text-muted-foreground">P95:</span>
                      <span className="font-mono">{Math.round(analytics.p95_latency_ms)}ms</span>
                    </div>
                  </div>
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-500/20">
                    <Zap className="h-6 w-6 text-amber-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950/50 dark:to-green-900/30">
              <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-green-500/20"></div>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-green-600/70">Cost Savings</p>
                    <p className="text-3xl font-bold text-green-700">${Math.round(analytics.estimated_savings).toLocaleString()}</p>
                    <div className="mt-1 flex items-center gap-1 text-xs">
                      <span className="text-muted-foreground">${analytics.avg_cost_per_query.toFixed(3)}/query</span>
                    </div>
                  </div>
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-green-500/20">
                    <DollarSign className="h-6 w-6 text-green-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Secondary Metrics */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card className="border-0 shadow-md">
              <CardContent className="flex items-center gap-4 p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900/30">
                  <Target className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Success Rate</p>
                  <p className="text-xl font-bold">{analytics.success_rate.toFixed(1)}%</p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-0 shadow-md">
              <CardContent className="flex items-center gap-4 p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100 dark:bg-amber-900/30">
                  <AlertTriangle className="h-5 w-5 text-amber-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Escalation Rate</p>
                  <p className="text-xl font-bold">{analytics.escalation_rate.toFixed(1)}%</p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-0 shadow-md">
              <CardContent className="flex items-center gap-4 p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/30">
                  <Shield className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Guardrails</p>
                  <p className="text-xl font-bold">{analytics.guardrails_enforced.toLocaleString()}</p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-0 shadow-md">
              <CardContent className="flex items-center gap-4 p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/30">
                  <Sparkles className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Tokens</p>
                  <p className="text-xl font-bold">{(analytics.total_tokens_30d / 1000).toFixed(1)}K</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Charts Row */}
          <div className="grid gap-6 md:grid-cols-2">
            {/* Daily Volume */}
            <Card className="border-0 shadow-lg">
              <CardHeader className="border-b bg-muted/30">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500">
                    <BarChart3 className="h-4 w-4 text-white" />
                  </div>
                  <div>
                    <CardTitle className="text-base">Query Volume</CardTitle>
                    <CardDescription>Daily queries over the last {period} days</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="h-64 flex items-end gap-1">
                  {analytics.daily_queries.slice(-30).map((day, i) => {
                    const maxQueries = Math.max(...analytics.daily_queries.map(d => d.queries));
                    const height = maxQueries > 0 ? (day.queries / maxQueries) * 100 : 0;
                    return (
                      <div
                        key={i}
                        className="flex-1 bg-gradient-to-t from-blue-500 to-cyan-400 hover:from-blue-600 hover:to-cyan-500 rounded-t transition-all cursor-pointer"
                        style={{ height: `${Math.max(height, 2)}%` }}
                        title={`${day.date}: ${day.queries} queries`}
                      />
                    );
                  })}
                </div>
                <div className="flex justify-between mt-3 text-xs text-muted-foreground">
                  <span>{analytics.daily_queries[0]?.date}</span>
                  <span>{analytics.daily_queries[analytics.daily_queries.length - 1]?.date}</span>
                </div>
              </CardContent>
            </Card>

            {/* Hourly Distribution */}
            <Card className="border-0 shadow-lg">
              <CardHeader className="border-b bg-muted/30">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500 to-pink-500">
                    <Clock className="h-4 w-4 text-white" />
                  </div>
                  <div>
                    <CardTitle className="text-base">Hourly Distribution</CardTitle>
                    <CardDescription>When users are most active</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="h-64 flex items-end gap-1">
                  {Array.from({ length: 24 }, (_, hour) => {
                    const queries = analytics.hourly_distribution[hour] || 0;
                    const maxQueries = Math.max(...Object.values(analytics.hourly_distribution));
                    const height = maxQueries > 0 ? (queries / maxQueries) * 100 : 0;
                    const isBusinessHours = hour >= 8 && hour <= 18;
                    return (
                      <div
                        key={hour}
                        className={`flex-1 rounded-t transition-all cursor-pointer ${
                          isBusinessHours
                            ? "bg-gradient-to-t from-purple-500 to-pink-400 hover:from-purple-600 hover:to-pink-500"
                            : "bg-gradient-to-t from-gray-400 to-gray-300 hover:from-gray-500 hover:to-gray-400"
                        }`}
                        style={{ height: `${Math.max(height, 2)}%` }}
                        title={`${hour}:00 - ${queries} queries`}
                      />
                    );
                  })}
                </div>
                <div className="flex justify-between mt-3 text-xs text-muted-foreground">
                  <span>12am</span>
                  <span>6am</span>
                  <span>12pm</span>
                  <span>6pm</span>
                  <span>12am</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Tables Row */}
          <div className="grid gap-6 md:grid-cols-2">
            {/* Top Agents */}
            <Card className="border-0 shadow-lg">
              <CardHeader className="border-b bg-muted/30">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-green-500 to-emerald-500">
                    <TrendingUp className="h-4 w-4 text-white" />
                  </div>
                  <div>
                    <CardTitle className="text-base">Top Agents</CardTitle>
                    <CardDescription>Most used agents by query volume</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/30 hover:bg-muted/30">
                      <TableHead className="font-semibold">Agent</TableHead>
                      <TableHead className="text-right font-semibold">Queries</TableHead>
                      <TableHead className="text-right font-semibold">Share</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {analytics.top_agents.slice(0, 5).map((agent, i) => (
                      <TableRow key={agent.agent_id} className="group">
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <div className={`flex h-8 w-8 items-center justify-center rounded-lg text-white text-xs font-bold ${
                              i === 0 ? "bg-gradient-to-br from-amber-400 to-amber-600" :
                              i === 1 ? "bg-gradient-to-br from-gray-300 to-gray-500" :
                              i === 2 ? "bg-gradient-to-br from-orange-400 to-orange-600" :
                              "bg-gradient-to-br from-slate-400 to-slate-600"
                            }`}>
                              #{i + 1}
                            </div>
                            <span className="font-medium">{agent.agent_id}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-mono">{agent.queries.toLocaleString()}</TableCell>
                        <TableCell className="text-right">
                          <Badge variant="secondary" className="font-mono">
                            {((agent.queries / analytics.total_queries_30d) * 100).toFixed(1)}%
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            {/* Top Departments */}
            <Card className="border-0 shadow-lg">
              <CardHeader className="border-b bg-muted/30">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-orange-500 to-red-500">
                    <PieChart className="h-4 w-4 text-white" />
                  </div>
                  <div>
                    <CardTitle className="text-base">Top Departments</CardTitle>
                    <CardDescription>Most active departments</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/30 hover:bg-muted/30">
                      <TableHead className="font-semibold">Department</TableHead>
                      <TableHead className="text-right font-semibold">Queries</TableHead>
                      <TableHead className="text-right font-semibold">Share</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {analytics.top_departments.slice(0, 5).map((dept, i) => (
                      <TableRow key={dept.department}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <div className={`h-3 w-3 rounded-full ${
                              i === 0 ? "bg-blue-500" :
                              i === 1 ? "bg-green-500" :
                              i === 2 ? "bg-purple-500" :
                              i === 3 ? "bg-amber-500" :
                              "bg-gray-500"
                            }`} />
                            <span className="font-medium">{dept.department}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-mono">{dept.queries.toLocaleString()}</TableCell>
                        <TableCell className="text-right">
                          <Badge variant="secondary" className="font-mono">
                            {((dept.queries / analytics.total_queries_30d) * 100).toFixed(1)}%
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>

          {/* Recent Errors */}
          {analytics.recent_errors.length > 0 && (
            <Card className="border-0 shadow-lg border-l-4 border-l-red-500">
              <CardHeader className="border-b bg-red-50/50 dark:bg-red-950/20">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-red-500 to-rose-500">
                    <AlertTriangle className="h-4 w-4 text-white" />
                  </div>
                  <div>
                    <CardTitle className="text-base">Recent Errors</CardTitle>
                    <CardDescription>Last {analytics.recent_errors.length} errors requiring attention</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/30 hover:bg-muted/30">
                      <TableHead className="font-semibold">Time</TableHead>
                      <TableHead className="font-semibold">Agent</TableHead>
                      <TableHead className="font-semibold">Error</TableHead>
                      <TableHead className="font-semibold">Query</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {analytics.recent_errors.slice(0, 5).map((error, i) => (
                      <TableRow key={i}>
                        <TableCell className="text-sm text-muted-foreground">
                          {new Date(error.timestamp).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{error.agent_id}</Badge>
                        </TableCell>
                        <TableCell className="text-sm text-red-600 font-medium">{error.error}</TableCell>
                        <TableCell className="text-sm text-muted-foreground truncate max-w-[200px]">
                          {error.query}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
