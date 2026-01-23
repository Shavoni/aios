"use client";

import {
  Activity,
  AlertTriangle,
  Shield,
  DollarSign,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const kpiData = [
  {
    title: "Total Requests",
    value: "8,247",
    change: "+12.5%",
    changeType: "positive" as const,
    icon: Activity,
    description: "Last 30 days",
  },
  {
    title: "Escalation Rate",
    value: "3.8%",
    change: "-1.2%",
    changeType: "positive" as const,
    icon: AlertTriangle,
    description: "Below 5% target",
  },
  {
    title: "Guardrails Enforced",
    value: "412",
    change: "100%",
    changeType: "positive" as const,
    icon: Shield,
    description: "CGI compliant",
  },
  {
    title: "Cost Savings",
    value: "$47,890",
    change: "+42%",
    changeType: "positive" as const,
    icon: DollarSign,
    description: "vs. manual processing",
  },
];

export function KpiCards() {
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
