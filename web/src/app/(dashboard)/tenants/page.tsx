"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Building2,
  Plus,
  Search,
  Filter,
  MoreVertical,
  Crown,
  Zap,
  Rocket,
  Shield,
  Landmark,
  Users,
  Activity,
  TrendingUp,
  DollarSign,
  Server,
  AlertCircle,
  CheckCircle2,
  Clock,
  Archive,
  Settings2,
  Trash2,
  Eye,
  ChevronRight,
  Sparkles,
  Globe,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import {
  listTenants,
  createTenant,
  updateTenant,
  deleteTenant,
  getTenantQuota,
  getTenantUsage,
  type Tenant,
  type ResourceQuota,
  type TenantUsage,
} from "@/lib/api";

// Tier configurations with visual styling
const tierConfig = {
  free: {
    label: "Free",
    icon: Zap,
    color: "bg-slate-500/10 text-slate-600 border-slate-300",
    gradient: "from-slate-400 to-slate-600",
    description: "Basic features for small teams",
  },
  starter: {
    label: "Starter",
    icon: Rocket,
    color: "bg-blue-500/10 text-blue-600 border-blue-300",
    gradient: "from-blue-400 to-blue-600",
    description: "Growing organizations",
  },
  professional: {
    label: "Professional",
    icon: Crown,
    color: "bg-purple-500/10 text-purple-600 border-purple-300",
    gradient: "from-purple-400 to-purple-600",
    description: "Advanced features & support",
  },
  enterprise: {
    label: "Enterprise",
    icon: Shield,
    color: "bg-amber-500/10 text-amber-600 border-amber-300",
    gradient: "from-amber-400 to-amber-600",
    description: "Full platform access",
  },
  government: {
    label: "Government",
    icon: Landmark,
    color: "bg-emerald-500/10 text-emerald-600 border-emerald-300",
    gradient: "from-emerald-400 to-emerald-600",
    description: "Public sector solution",
  },
};

const statusConfig = {
  active: {
    label: "Active",
    icon: CheckCircle2,
    color: "bg-green-500/10 text-green-600 border-green-300",
  },
  suspended: {
    label: "Suspended",
    icon: AlertCircle,
    color: "bg-red-500/10 text-red-600 border-red-300",
  },
  pending: {
    label: "Pending",
    icon: Clock,
    color: "bg-yellow-500/10 text-yellow-600 border-yellow-300",
  },
  archived: {
    label: "Archived",
    icon: Archive,
    color: "bg-gray-500/10 text-gray-600 border-gray-300",
  },
};

interface TenantWithStats extends Tenant {
  usage?: TenantUsage;
  quota?: ResourceQuota & { is_custom: boolean };
}

export default function TenantsPage() {
  const [tenants, setTenants] = useState<TenantWithStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [tierFilter, setTierFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedTenant, setSelectedTenant] = useState<TenantWithStats | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: "",
    tier: "professional",
    admin_email: "",
    admin_name: "",
  });

  const loadTenants = useCallback(async () => {
    try {
      setLoading(true);
      const status = statusFilter !== "all" ? statusFilter : undefined;
      const tier = tierFilter !== "all" ? tierFilter : undefined;
      const result = await listTenants(status, tier);

      // Enrich with usage/quota data
      const enriched = await Promise.all(
        result.tenants.map(async (tenant) => {
          try {
            const [quota, usage] = await Promise.all([
              getTenantQuota(tenant.id).catch(() => null),
              getTenantUsage(tenant.id).catch(() => null),
            ]);
            return { ...tenant, quota, usage } as TenantWithStats;
          } catch {
            return tenant as TenantWithStats;
          }
        })
      );

      setTenants(enriched);
    } catch (err) {
      toast.error("Failed to load tenants");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, tierFilter]);

  useEffect(() => {
    loadTenants();
  }, [loadTenants]);

  const handleCreateTenant = async () => {
    try {
      await createTenant({
        name: createForm.name,
        tier: createForm.tier,
        admin_email: createForm.admin_email,
        admin_name: createForm.admin_name,
      });
      toast.success(`Tenant "${createForm.name}" created successfully`);
      setIsCreateOpen(false);
      setCreateForm({ name: "", tier: "professional", admin_email: "", admin_name: "" });
      loadTenants();
    } catch (err) {
      toast.error("Failed to create tenant");
      console.error(err);
    }
  };

  const handleStatusChange = async (tenant: Tenant, newStatus: string) => {
    try {
      await updateTenant(tenant.id, { status: newStatus });
      toast.success(`Tenant status updated to ${newStatus}`);
      loadTenants();
    } catch (err) {
      toast.error("Failed to update tenant status");
      console.error(err);
    }
  };

  const handleDeleteTenant = async (tenant: Tenant) => {
    try {
      await deleteTenant(tenant.id);
      toast.success(`Tenant "${tenant.name}" archived`);
      loadTenants();
    } catch (err) {
      toast.error("Failed to archive tenant");
      console.error(err);
    }
  };

  const viewTenantDetails = async (tenant: TenantWithStats) => {
    setSelectedTenant(tenant);
    setIsDetailsOpen(true);
  };

  const filteredTenants = tenants.filter((tenant) =>
    tenant.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    tenant.admin_email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Calculate summary stats
  const stats = {
    total: tenants.length,
    active: tenants.filter((t) => t.status === "active").length,
    totalApiCalls: tenants.reduce((sum, t) => sum + (t.usage?.api_calls_this_month || 0), 0),
    totalCost: tenants.reduce((sum, t) => sum + (t.usage?.llm_cost_this_month_usd || 0), 0),
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header Section with Gradient Background */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500 p-6 text-white shadow-xl">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDM0aDR2MmgtNHYtMnptMC04aDR2Nmg0djJoLTh2LTh6bTAgMTZoOHYyaC04di0yem0tMTYgMGg0djJoLTR2LTJ6bTAtOGg0djZoNHYyaC04di04em0wIDE2aDh2Mmgtxdi0yeiIvPjwvZz48L2c+PC9zdmc+')] opacity-30"></div>
        <div className="relative">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/20 backdrop-blur-sm">
                <Building2 className="h-8 w-8" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight">Tenant Management</h1>
                <p className="text-white/80">Manage organizations, quotas, and usage across your platform</p>
              </div>
            </div>
            <Button
              onClick={() => setIsCreateOpen(true)}
              className="bg-white text-purple-600 hover:bg-white/90 shadow-lg"
            >
              <Plus className="mr-2 h-4 w-4" />
              New Tenant
            </Button>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950/50 dark:to-blue-900/30">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-blue-500/20"></div>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/20">
                <Users className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-blue-600/70">Total Tenants</p>
                <p className="text-3xl font-bold text-blue-700">{stats.total}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950/50 dark:to-green-900/30">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-green-500/20"></div>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-green-500/20">
                <Activity className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-green-600/70">Active</p>
                <p className="text-3xl font-bold text-green-700">{stats.active}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-950/50 dark:to-purple-900/30">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-purple-500/20"></div>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-purple-500/20">
                <TrendingUp className="h-6 w-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-purple-600/70">API Calls (MTD)</p>
                <p className="text-3xl font-bold text-purple-700">
                  {stats.totalApiCalls.toLocaleString()}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-amber-50 to-amber-100 dark:from-amber-950/50 dark:to-amber-900/30">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-amber-500/20"></div>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-500/20">
                <DollarSign className="h-6 w-6 text-amber-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-amber-600/70">LLM Cost (MTD)</p>
                <p className="text-3xl font-bold text-amber-700">
                  ${stats.totalCost.toFixed(2)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tenants Table */}
      <Card className="border-0 shadow-lg">
        <CardHeader className="border-b bg-muted/30">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Globe className="h-5 w-5 text-muted-foreground" />
              Organizations
            </CardTitle>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search tenants..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 sm:w-64"
                />
              </div>
              <Select value={tierFilter} onValueChange={setTierFilter}>
                <SelectTrigger className="w-full sm:w-40">
                  <Filter className="mr-2 h-4 w-4" />
                  <SelectValue placeholder="Tier" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Tiers</SelectItem>
                  <SelectItem value="free">Free</SelectItem>
                  <SelectItem value="starter">Starter</SelectItem>
                  <SelectItem value="professional">Professional</SelectItem>
                  <SelectItem value="enterprise">Enterprise</SelectItem>
                  <SelectItem value="government">Government</SelectItem>
                </SelectContent>
              </Select>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-full sm:w-40">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="suspended">Suspended</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="archived">Archived</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" size="icon" onClick={loadTenants}>
                <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex h-64 items-center justify-center">
              <div className="flex flex-col items-center gap-3">
                <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Loading tenants...</p>
              </div>
            </div>
          ) : filteredTenants.length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center gap-3">
              <Building2 className="h-12 w-12 text-muted-foreground/50" />
              <p className="text-lg font-medium text-muted-foreground">No tenants found</p>
              <p className="text-sm text-muted-foreground">
                {searchQuery ? "Try adjusting your search" : "Create your first tenant to get started"}
              </p>
              {!searchQuery && (
                <Button onClick={() => setIsCreateOpen(true)} className="mt-2">
                  <Plus className="mr-2 h-4 w-4" />
                  Create Tenant
                </Button>
              )}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/30 hover:bg-muted/30">
                  <TableHead className="font-semibold">Organization</TableHead>
                  <TableHead className="font-semibold">Tier</TableHead>
                  <TableHead className="font-semibold">Status</TableHead>
                  <TableHead className="font-semibold text-right">API Calls (MTD)</TableHead>
                  <TableHead className="font-semibold text-right">Cost (MTD)</TableHead>
                  <TableHead className="font-semibold">Created</TableHead>
                  <TableHead className="w-12"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTenants.map((tenant, index) => {
                  const tier = tierConfig[tenant.tier];
                  const status = statusConfig[tenant.status];
                  const TierIcon = tier.icon;
                  const StatusIcon = status.icon;

                  return (
                    <TableRow
                      key={tenant.id}
                      className="group cursor-pointer transition-colors hover:bg-muted/50"
                      style={{ animationDelay: `${index * 50}ms` }}
                      onClick={() => viewTenantDetails(tenant)}
                    >
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className={`flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br ${tier.gradient} text-white shadow-sm`}>
                            <TierIcon className="h-5 w-5" />
                          </div>
                          <div>
                            <p className="font-medium">{tenant.name}</p>
                            <p className="text-xs text-muted-foreground">{tenant.admin_email || "No admin email"}</p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={`${tier.color} font-medium`}>
                          {tier.label}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={`${status.color} font-medium`}>
                          <StatusIcon className="mr-1 h-3 w-3" />
                          {status.label}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {(tenant.usage?.api_calls_this_month || 0).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        ${(tenant.usage?.llm_cost_this_month_usd || 0).toFixed(2)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(tenant.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                            <Button variant="ghost" size="icon" className="opacity-0 group-hover:opacity-100">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); viewTenantDetails(tenant); }}>
                              <Eye className="mr-2 h-4 w-4" />
                              View Details
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={(e) => e.stopPropagation()}>
                              <Settings2 className="mr-2 h-4 w-4" />
                              Settings
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            {tenant.status === "active" ? (
                              <DropdownMenuItem
                                onClick={(e) => { e.stopPropagation(); handleStatusChange(tenant, "suspended"); }}
                                className="text-amber-600"
                              >
                                <AlertCircle className="mr-2 h-4 w-4" />
                                Suspend
                              </DropdownMenuItem>
                            ) : tenant.status === "suspended" ? (
                              <DropdownMenuItem
                                onClick={(e) => { e.stopPropagation(); handleStatusChange(tenant, "active"); }}
                                className="text-green-600"
                              >
                                <CheckCircle2 className="mr-2 h-4 w-4" />
                                Activate
                              </DropdownMenuItem>
                            ) : null}
                            <DropdownMenuItem
                              onClick={(e) => { e.stopPropagation(); handleDeleteTenant(tenant); }}
                              className="text-destructive"
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Archive
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Tenant Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-purple-500" />
              Create New Tenant
            </DialogTitle>
            <DialogDescription>
              Set up a new organization with customized quotas and settings.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Organization Name</label>
              <Input
                placeholder="e.g., City of Cleveland"
                value={createForm.name}
                onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Tier</label>
              <Select
                value={createForm.tier}
                onValueChange={(value) => setCreateForm({ ...createForm, tier: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(tierConfig).map(([key, config]) => {
                    const Icon = config.icon;
                    return (
                      <SelectItem key={key} value={key}>
                        <div className="flex items-center gap-2">
                          <Icon className="h-4 w-4" />
                          <span>{config.label}</span>
                          <span className="text-xs text-muted-foreground">- {config.description}</span>
                        </div>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium">Admin Name</label>
                <Input
                  placeholder="John Smith"
                  value={createForm.admin_name}
                  onChange={(e) => setCreateForm({ ...createForm, admin_name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Admin Email</label>
                <Input
                  type="email"
                  placeholder="admin@example.gov"
                  value={createForm.admin_email}
                  onChange={(e) => setCreateForm({ ...createForm, admin_email: e.target.value })}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateTenant}
              disabled={!createForm.name}
              className="bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600"
            >
              <Plus className="mr-2 h-4 w-4" />
              Create Tenant
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Tenant Details Dialog */}
      <Dialog open={isDetailsOpen} onOpenChange={setIsDetailsOpen}>
        <DialogContent className="sm:max-w-2xl">
          {selectedTenant && (
            <>
              <DialogHeader>
                <div className="flex items-center gap-4">
                  <div className={`flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br ${tierConfig[selectedTenant.tier].gradient} text-white shadow-lg`}>
                    {(() => {
                      const Icon = tierConfig[selectedTenant.tier].icon;
                      return <Icon className="h-7 w-7" />;
                    })()}
                  </div>
                  <div>
                    <DialogTitle className="text-xl">{selectedTenant.name}</DialogTitle>
                    <DialogDescription className="flex items-center gap-2 mt-1">
                      <Badge variant="outline" className={tierConfig[selectedTenant.tier].color}>
                        {tierConfig[selectedTenant.tier].label}
                      </Badge>
                      <Badge variant="outline" className={statusConfig[selectedTenant.status].color}>
                        {statusConfig[selectedTenant.status].label}
                      </Badge>
                    </DialogDescription>
                  </div>
                </div>
              </DialogHeader>
              <Tabs defaultValue="overview" className="mt-4">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="overview">Overview</TabsTrigger>
                  <TabsTrigger value="usage">Usage</TabsTrigger>
                  <TabsTrigger value="quota">Quotas</TabsTrigger>
                </TabsList>
                <TabsContent value="overview" className="space-y-4 pt-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Admin</p>
                      <p className="font-medium">{selectedTenant.admin_name || "Not set"}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Email</p>
                      <p className="font-medium">{selectedTenant.admin_email || "Not set"}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Created</p>
                      <p className="font-medium">{new Date(selectedTenant.created_at).toLocaleString()}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Updated</p>
                      <p className="font-medium">{new Date(selectedTenant.updated_at).toLocaleString()}</p>
                    </div>
                  </div>
                </TabsContent>
                <TabsContent value="usage" className="space-y-4 pt-4">
                  {selectedTenant.usage ? (
                    <div className="grid gap-4 sm:grid-cols-2">
                      <Card className="border-0 bg-blue-50 dark:bg-blue-950/30">
                        <CardContent className="p-4">
                          <p className="text-sm text-blue-600/70">API Calls Today</p>
                          <p className="text-2xl font-bold text-blue-700">{selectedTenant.usage.api_calls_today.toLocaleString()}</p>
                        </CardContent>
                      </Card>
                      <Card className="border-0 bg-purple-50 dark:bg-purple-950/30">
                        <CardContent className="p-4">
                          <p className="text-sm text-purple-600/70">API Calls This Month</p>
                          <p className="text-2xl font-bold text-purple-700">{selectedTenant.usage.api_calls_this_month.toLocaleString()}</p>
                        </CardContent>
                      </Card>
                      <Card className="border-0 bg-green-50 dark:bg-green-950/30">
                        <CardContent className="p-4">
                          <p className="text-sm text-green-600/70">Tokens Today</p>
                          <p className="text-2xl font-bold text-green-700">{selectedTenant.usage.tokens_used_today.toLocaleString()}</p>
                        </CardContent>
                      </Card>
                      <Card className="border-0 bg-amber-50 dark:bg-amber-950/30">
                        <CardContent className="p-4">
                          <p className="text-sm text-amber-600/70">LLM Cost This Month</p>
                          <p className="text-2xl font-bold text-amber-700">${selectedTenant.usage.llm_cost_this_month_usd.toFixed(2)}</p>
                        </CardContent>
                      </Card>
                    </div>
                  ) : (
                    <div className="flex h-32 items-center justify-center text-muted-foreground">
                      No usage data available
                    </div>
                  )}
                </TabsContent>
                <TabsContent value="quota" className="space-y-4 pt-4">
                  {selectedTenant.quota ? (
                    <div className="space-y-3">
                      {selectedTenant.quota.is_custom && (
                        <Badge variant="outline" className="mb-2 bg-amber-50 text-amber-600 border-amber-200">
                          Custom Quota
                        </Badge>
                      )}
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div className="flex items-center justify-between rounded-lg bg-muted/50 p-3">
                          <span className="text-sm">Daily API Calls</span>
                          <span className="font-mono font-medium">{selectedTenant.quota.daily_api_calls.toLocaleString()}</span>
                        </div>
                        <div className="flex items-center justify-between rounded-lg bg-muted/50 p-3">
                          <span className="text-sm">Monthly API Calls</span>
                          <span className="font-mono font-medium">{selectedTenant.quota.monthly_api_calls.toLocaleString()}</span>
                        </div>
                        <div className="flex items-center justify-between rounded-lg bg-muted/50 p-3">
                          <span className="text-sm">Max Agents</span>
                          <span className="font-mono font-medium">{selectedTenant.quota.max_agents}</span>
                        </div>
                        <div className="flex items-center justify-between rounded-lg bg-muted/50 p-3">
                          <span className="text-sm">Max Active Agents</span>
                          <span className="font-mono font-medium">{selectedTenant.quota.max_active_agents}</span>
                        </div>
                        <div className="flex items-center justify-between rounded-lg bg-muted/50 p-3">
                          <span className="text-sm">Daily LLM Budget</span>
                          <span className="font-mono font-medium">${selectedTenant.quota.daily_llm_budget_usd}</span>
                        </div>
                        <div className="flex items-center justify-between rounded-lg bg-muted/50 p-3">
                          <span className="text-sm">Monthly LLM Budget</span>
                          <span className="font-mono font-medium">${selectedTenant.quota.monthly_llm_budget_usd}</span>
                        </div>
                        <div className="flex items-center justify-between rounded-lg bg-muted/50 p-3">
                          <span className="text-sm">Max KB Documents</span>
                          <span className="font-mono font-medium">{selectedTenant.quota.max_kb_documents.toLocaleString()}</span>
                        </div>
                        <div className="flex items-center justify-between rounded-lg bg-muted/50 p-3">
                          <span className="text-sm">Max KB Size</span>
                          <span className="font-mono font-medium">{selectedTenant.quota.max_kb_size_mb} MB</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex h-32 items-center justify-center text-muted-foreground">
                      No quota data available
                    </div>
                  )}
                </TabsContent>
              </Tabs>
              <DialogFooter className="mt-6">
                <Button variant="outline" onClick={() => setIsDetailsOpen(false)}>
                  Close
                </Button>
                <Button className="bg-gradient-to-r from-indigo-500 to-purple-500 text-white">
                  <Settings2 className="mr-2 h-4 w-4" />
                  Manage Settings
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
