"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Bot,
  History,
  Settings,
  ChevronLeft,
  ChevronRight,
  FileSearch,
  MessageCircle,
  Sparkles,
  ExternalLink,
  BarChart3,
  CheckCircle,
  Library,
  Building2,
  Wand2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { config } from "@/lib/config";

const navItems = [
  {
    title: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    title: "Onboarding",
    href: "/onboarding",
    icon: Wand2,
  },
  {
    title: "Tenants",
    href: "/tenants",
    icon: Building2,
  },
  {
    title: "Agents",
    href: "/agents",
    icon: Bot,
  },
  {
    title: "Analytics",
    href: "/analytics",
    icon: BarChart3,
  },
  {
    title: "Approvals",
    href: "/approvals",
    icon: CheckCircle,
  },
  {
    title: "Templates",
    href: "/templates",
    icon: Library,
  },
  {
    title: "Runs",
    href: "/runs",
    icon: History,
  },
  {
    title: "Audit Log",
    href: "/audit",
    icon: FileSearch,
  },
  {
    title: "Settings",
    href: "/settings",
    icon: Settings,
  },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          "flex flex-col border-r bg-card transition-all duration-300",
          collapsed ? "w-16" : "w-64"
        )}
      >
        {/* Logo */}
        <div className="flex h-16 items-center border-b px-4">
          <Link href="/" className="flex items-center gap-2">
            {config.logoUrl ? (
              <Image
                src={config.logoUrl}
                alt={config.logoAlt || config.appName}
                width={32}
                height={32}
                className="h-8 w-8 object-contain"
              />
            ) : (
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600">
                <Sparkles className="h-5 w-5 text-white" />
              </div>
            )}
            {!collapsed && (
              <div className="flex flex-col">
                <span className="text-lg font-semibold tracking-tight leading-tight">{config.appName}</span>
                <span className="text-xs text-muted-foreground">{config.tagline}</span>
              </div>
            )}
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            const linkContent = (
              <Link
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                  collapsed && "justify-center px-2"
                )}
              >
                <Icon className="h-5 w-5 shrink-0" />
                {!collapsed && <span>{item.title}</span>}
              </Link>
            );

            if (collapsed) {
              return (
                <Tooltip key={item.href}>
                  <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
                  <TooltipContent side="right">{item.title}</TooltipContent>
                </Tooltip>
              );
            }

            return <div key={item.href}>{linkContent}</div>;
          })}
        </nav>

        {/* Concierge Link - Premium styling */}
        <div className="border-t p-2">
          {collapsed ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Link
                  href="/chat"
                  target="_blank"
                  className="flex items-center justify-center gap-2 rounded-lg px-2 py-2.5 text-sm font-medium bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:from-amber-600 hover:to-orange-600 transition-all shadow-md hover:shadow-lg"
                >
                  <Sparkles className="h-5 w-5 shrink-0" />
                </Link>
              </TooltipTrigger>
              <TooltipContent side="right">Open Concierge Chat</TooltipContent>
            </Tooltip>
          ) : (
            <Link
              href="/chat"
              target="_blank"
              className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:from-amber-600 hover:to-orange-600 transition-all shadow-md hover:shadow-lg"
            >
              <Sparkles className="h-5 w-5 shrink-0" />
              <span className="flex-1">Concierge</span>
              <ExternalLink className="h-4 w-4 opacity-70" />
            </Link>
          )}
        </div>

        {/* Collapse Toggle */}
        <div className="border-t p-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggle}
            className={cn("w-full", collapsed && "px-2")}
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <>
                <ChevronLeft className="h-4 w-4 mr-2" />
                Collapse
              </>
            )}
          </Button>
        </div>
      </aside>
    </TooltipProvider>
  );
}
