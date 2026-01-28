"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Shield,
  DollarSign,
  Users,
  Clock,
  TrendingUp,
  Loader2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getAnalyticsSummary, type AnalyticsSummary } from "@/lib/api";

export function KpiCards() {
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAnalytics() {
      try {
        const data = await getAnalyticsSummary(30);
        setAnalytics(data);
      } catch (error) {
        console.error("Failed to load analytics:", error);
      } finally {
        setLoading(false);
      }
    }
    loadAnalytics();
  }, []);

  if (loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <div className="h-4 w-24 bg-muted animate-pulse rounded" />
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="h-8 w-20 bg-muted animate-pulse rounded mb-2" />
              <div className="h-3 w-32 bg-muted animate-pulse rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const kpiData = analytics
    ? [
        {
          title: "Total Requests",
          value: analytics.total_queries_30d.toLocaleString(),
          change: `${analytics.total_queries_today} today`,
          changeType: "positive" as const,
          icon: Activity,
          description: "Last 30 days",
        },
        {
          title: "Escalation Rate",
          value: `${analytics.escalation_rate.toFixed(1)}%`,
          change: analytics.escalation_rate < 5 ? "Below target" : "Above target",
          changeType: analytics.escalation_rate < 5 ? "positive" : "negative" as const,
          icon: AlertTriangle,
          description: "Target: <5%",
        },
        {
          title: "Guardrails Enforced",
          value: analytics.guardrails_enforced.toLocaleString(),
          change: "100% compliant",
          changeType: "positive" as const,
          icon: Shield,
          description: "Policy triggers",
        },
        {
          title: "Cost Savings",
          value: `$${Math.round(analytics.estimated_savings).toLocaleString()}`,
          change: `$${analytics.avg_cost_per_query.toFixed(3)}/query`,
          changeType: "positive" as const,
          icon: DollarSign,
          description: "vs. manual processing",
        },
      ]
    : [
        {
          title: "Total Requests",
          value: "0",
          change: "No data",
          changeType: "positive" as const,
          icon: Activity,
          description: "Last 30 days",
        },
        {
          title: "Escalation Rate",
          value: "0%",
          change: "No data",
          changeType: "positive" as const,
          icon: AlertTriangle,
          description: "Target: <5%",
        },
        {
          title: "Guardrails Enforced",
          value: "0",
          change: "No data",
          changeType: "positive" as const,
          icon: Shield,
          description: "Policy triggers",
        },
        {
          title: "Cost Savings",
          value: "$0",
          change: "No data",
          changeType: "positive" as const,
          icon: DollarSign,
          description: "vs. manual processing",
        },
      ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {kpiData.map((kpi) => {
        const Icon = kpi.icon;
        return (
          <Card key={kpi.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {kpi.title}
              </CardTitle>
              <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{kpi.value}</div>
              <div className="flex items-center gap-1 text-xs">
                <span
                  className={
                    kpi.changeType === "positive"
                      ? "text-green-600 dark:text-green-400"
                      : "text-red-600 dark:text-red-400"
                  }
                >
                  {kpi.change}
                </span>
                <span className="text-muted-foreground">{kpi.description}</span>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

// Extended KPI cards with more metrics
export function ExtendedKpiCards() {
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAnalytics() {
      try {
        const data = await getAnalyticsSummary(30);
        setAnalytics(data);
      } catch (error) {
        console.error("Failed to load analytics:", error);
      } finally {
        setLoading(false);
      }
    }
    loadAnalytics();
  }, []);

  if (loading || !analytics) {
    return null;
  }

  const extendedKpis = [
    {
      title: "Unique Users",
      value: analytics.unique_users_30d.toLocaleString(),
      subtitle: `${analytics.unique_users_today} active today`,
      icon: Users,
    },
    {
      title: "Avg Response Time",
      value: `${Math.round(analytics.avg_latency_ms)}ms`,
      subtitle: `P95: ${Math.round(analytics.p95_latency_ms)}ms`,
      icon: Clock,
    },
    {
      title: "Success Rate",
      value: `${analytics.success_rate.toFixed(1)}%`,
      subtitle: "Query completion",
      icon: TrendingUp,
    },
    {
      title: "Total Tokens",
      value: (analytics.total_tokens_30d / 1000).toFixed(1) + "K",
      subtitle: `${Math.round(analytics.avg_tokens_per_query)} avg/query`,
      icon: Activity,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mt-4">
      {extendedKpis.map((kpi) => {
        const Icon = kpi.icon;
        return (
          <Card key={kpi.title} className="bg-muted/50">
            <CardContent className="pt-4">
              <div className="flex items-center gap-2">
                <Icon className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">{kpi.title}</span>
              </div>
              <div className="text-xl font-semibold mt-1">{kpi.value}</div>
              <div className="text-xs text-muted-foreground">{kpi.subtitle}</div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
