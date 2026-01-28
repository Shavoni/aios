"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { KpiCards, ExtendedKpiCards } from "@/components/dashboard/kpi-cards";
import { RecentRunsTable } from "@/components/dashboard/recent-runs-table";
import { config } from "@/lib/config";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  BarChart3,
  Bot,
  CheckCircle,
  Library,
  FileSearch,
  MessageSquare,
  ArrowRight,
  Building2,
  Sparkles,
  TrendingUp,
  Users,
  Shield,
  Zap,
  Activity,
  Clock,
  RefreshCw,
} from "lucide-react";
import { getHealth, getAnalyticsSummary, getApprovalQueue, listAgents, type HealthResponse, type AnalyticsSummary, type ApprovalQueue } from "@/lib/api";

const quickLinks = [
  {
    title: "Tenants",
    description: "Manage organizations and quotas",
    href: "/tenants",
    icon: Building2,
    gradient: "from-indigo-500 to-purple-500",
  },
  {
    title: "Analytics",
    description: "View detailed metrics and performance data",
    href: "/analytics",
    icon: BarChart3,
    gradient: "from-cyan-500 to-blue-500",
  },
  {
    title: "Agents",
    description: "Manage AI agents and knowledge bases",
    href: "/agents",
    icon: Bot,
    gradient: "from-green-500 to-emerald-500",
  },
  {
    title: "Approvals",
    description: "Review pending HITL requests",
    href: "/approvals",
    icon: CheckCircle,
    gradient: "from-amber-500 to-orange-500",
  },
  {
    title: "Templates",
    description: "Browse pre-built agent templates",
    href: "/templates",
    icon: Library,
    gradient: "from-pink-500 to-rose-500",
  },
  {
    title: "Audit Log",
    description: "View governance audit trail",
    href: "/audit",
    icon: FileSearch,
    gradient: "from-red-500 to-pink-500",
  },
];

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [queue, setQueue] = useState<ApprovalQueue | null>(null);
  const [agentCount, setAgentCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [healthData, analyticsData, queueData, agentsData] = await Promise.all([
          getHealth().catch(() => null),
          getAnalyticsSummary(7).catch(() => null),
          getApprovalQueue().catch(() => null),
          listAgents().catch(() => ({ agents: [], total: 0 })),
        ]);
        setHealth(healthData);
        setAnalytics(analyticsData);
        setQueue(queueData);
        setAgentCount(agentsData.total);
      } catch (error) {
        console.error("Failed to load dashboard data:", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Hero Header */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-8 text-white shadow-2xl">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wMyI+PHBhdGggZD0iTTM2IDM0aDR2MmgtNHYtMnptMC04aDR2Nmg0djJoLTh2LTh6bTAgMTZoOHYyaC04di0yem0tMTYgMGg0djJoLTR2LTJ6bTAtOGg0djZoNHYyaC04di04em0wIDE2aDh2Mmgtxdi0yeiIvPjwvZz48L2c+PC9zdmc+')] opacity-50"></div>
        <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-purple-500/20 blur-3xl"></div>
        <div className="absolute -bottom-20 -left-20 h-64 w-64 rounded-full bg-blue-500/20 blur-3xl"></div>
        <div className="relative">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/10 backdrop-blur-sm">
                  <Sparkles className="h-7 w-7 text-purple-300" />
                </div>
                <div>
                  <h1 className="text-3xl font-bold tracking-tight">{config.appName}</h1>
                  <p className="text-purple-200">{config.tagline}</p>
                </div>
              </div>
              <p className="mt-4 max-w-xl text-white/70">
                AI governance and automation platform for {config.organization}. Monitor agents,
                review approvals, and track performance across your organization.
              </p>
            </div>
            <div className="hidden lg:flex items-center gap-3">
              {health && (
                <Badge
                  variant="outline"
                  className={`border-0 px-3 py-1.5 ${
                    health.llm_available
                      ? "bg-green-500/20 text-green-300"
                      : "bg-red-500/20 text-red-300"
                  }`}
                >
                  <div className={`mr-2 h-2 w-2 rounded-full ${health.llm_available ? "bg-green-400 animate-pulse" : "bg-red-400"}`} />
                  {health.llm_available ? `${health.llm_provider} Connected` : "LLM Offline"}
                </Badge>
              )}
              <Link href="/chat" target="_blank">
                <Button className="bg-white/10 hover:bg-white/20 border-0 text-white">
                  <MessageSquare className="mr-2 h-4 w-4" />
                  Open Chat
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950/50 dark:to-blue-900/30">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-blue-500/20"></div>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-blue-600/70 dark:text-blue-400">Queries Today</p>
                <p className="text-3xl font-bold text-blue-700 dark:text-blue-300">
                  {analytics?.total_queries_today.toLocaleString() || "—"}
                </p>
                <p className="text-xs text-blue-600/60 dark:text-blue-400/60 mt-1">
                  {analytics?.total_queries_7d.toLocaleString() || 0} this week
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/20">
                <Activity className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950/50 dark:to-green-900/30">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-green-500/20"></div>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-green-600/70 dark:text-green-400">Active Agents</p>
                <p className="text-3xl font-bold text-green-700 dark:text-green-300">{agentCount}</p>
                <p className="text-xs text-green-600/60 dark:text-green-400/60 mt-1">
                  Across all domains
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-green-500/20">
                <Bot className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-amber-50 to-amber-100 dark:from-amber-950/50 dark:to-amber-900/30">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-amber-500/20"></div>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-amber-600/70 dark:text-amber-400">Pending Approvals</p>
                <p className="text-3xl font-bold text-amber-700 dark:text-amber-300">{queue?.pending_count || 0}</p>
                <p className="text-xs text-amber-600/60 dark:text-amber-400/60 mt-1">
                  {queue?.pending_by_priority?.urgent || 0} urgent
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-500/20">
                <Clock className="h-6 w-6 text-amber-600 dark:text-amber-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-950/50 dark:to-purple-900/30">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-purple-500/20"></div>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-purple-600/70 dark:text-purple-400">Success Rate</p>
                <p className="text-3xl font-bold text-purple-700 dark:text-purple-300">
                  {analytics?.success_rate?.toFixed(1) || "—"}%
                </p>
                <p className="text-xs text-purple-600/60 dark:text-purple-400/60 mt-1">
                  Last 7 days
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-purple-500/20">
                <TrendingUp className="h-6 w-6 text-purple-600 dark:text-purple-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Links */}
      <Card className="border-0 shadow-lg">
        <CardHeader className="border-b bg-muted/30">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Zap className="h-5 w-5 text-amber-500" />
            Quick Access
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {quickLinks.map((link) => {
              const Icon = link.icon;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className="group flex items-center gap-4 p-4 rounded-xl border bg-card hover:bg-muted/50 hover:border-primary/20 transition-all duration-200"
                >
                  <div className={`flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${link.gradient} text-white shadow-lg group-hover:scale-110 transition-transform`}>
                    <Icon className="h-6 w-6" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm">{link.title}</p>
                    <p className="text-xs text-muted-foreground truncate">
                      {link.description}
                    </p>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
                </Link>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card className="border-0 shadow-lg">
        <CardHeader className="border-b bg-muted/30">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Activity className="h-5 w-5 text-blue-500" />
              Recent Activity
            </CardTitle>
            <Link href="/runs">
              <Button variant="ghost" size="sm">
                View All
                <ArrowRight className="ml-1 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <RecentRunsTable />
        </CardContent>
      </Card>
    </div>
  );
}
