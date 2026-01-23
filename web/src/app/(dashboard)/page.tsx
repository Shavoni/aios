"use client";

import { KpiCards } from "@/components/dashboard/kpi-cards";
import { RecentRunsTable } from "@/components/dashboard/recent-runs-table";
import { config } from "@/lib/config";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          {config.appName} - Monitor AI governance and activity for {config.organization}
        </p>
      </div>

      {/* KPI Cards */}
      <KpiCards />

      {/* Recent Activity */}
      <RecentRunsTable />
    </div>
  );
}
