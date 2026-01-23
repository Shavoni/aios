"use client";

import { useState, useEffect } from "react";
import {
  Key,
  Shield,
  Bell,
  Save,
  Eye,
  EyeOff,
  Plus,
  Trash2,
  Building2,
  AlertTriangle,
  RefreshCw,
  Sparkles,
  Loader2,
  CheckCircle2,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { resetForNewClient, regenerateConcierge, listAgents } from "@/lib/api";
import { config } from "@/lib/config";

interface Policy {
  id: string;
  name: string;
  type: "constitutional" | "departmental";
  domain: string;
  trigger: string;
  action: string;
  enabled: boolean;
}

const mockPolicies: Policy[] = [
  {
    id: "pol_001",
    name: "Public Statement Draft",
    type: "constitutional",
    domain: "All",
    trigger: "audience = public",
    action: "DRAFT mode",
    enabled: true,
  },
  {
    id: "pol_002",
    name: "Legal Contract Escalation",
    type: "constitutional",
    domain: "Legal",
    trigger: "risk.contains(legal_contract)",
    action: "ESCALATE",
    enabled: true,
  },
  {
    id: "pol_003",
    name: "PII Data Protection",
    type: "constitutional",
    domain: "All",
    trigger: "risk.contains(pii)",
    action: "local_only = true",
    enabled: true,
  },
  {
    id: "pol_004",
    name: "HR Employment Actions",
    type: "departmental",
    domain: "HR",
    trigger: "task = employment_action",
    action: "DRAFT mode",
    enabled: true,
  },
  {
    id: "pol_005",
    name: "Finance High Value",
    type: "departmental",
    domain: "Finance",
    trigger: "impact = high",
    action: "ESCALATE",
    enabled: false,
  },
];

export default function SettingsPage() {
  const [showApiKey, setShowApiKey] = useState(false);
  const [provider, setProvider] = useState("openai");

  // Client setup state
  const [clientName, setClientName] = useState("");
  const [organization, setOrganization] = useState("");
  const [description, setDescription] = useState("");
  const [isResetting, setIsResetting] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [agentCount, setAgentCount] = useState(0);

  // Load current agent count
  useEffect(() => {
    loadAgentCount();
  }, []);

  async function loadAgentCount() {
    try {
      const data = await listAgents();
      setAgentCount(data.total);
    } catch (error) {
      console.error("Failed to load agents:", error);
    }
  }

  async function handleReset() {
    if (!clientName.trim() || !organization.trim()) {
      toast.error("Client name and organization are required");
      return;
    }

    setIsResetting(true);
    try {
      const result = await resetForNewClient({
        client_name: clientName.trim(),
        organization: organization.trim(),
        description: description.trim(),
      });

      toast.success(result.message);
      setClientName("");
      setOrganization("");
      setDescription("");
      loadAgentCount();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Reset failed";
      toast.error(message);
    } finally {
      setIsResetting(false);
    }
  }

  async function handleRegenerateConcierge() {
    setIsRegenerating(true);
    try {
      await regenerateConcierge();
      toast.success("Concierge updated with current agent knowledge");
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Regeneration failed";
      toast.error(message);
    } finally {
      setIsRegenerating(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Configure {config.appName} instance and governance policies
        </p>
      </div>

      <Tabs defaultValue="client" className="space-y-6">
        <TabsList>
          <TabsTrigger value="client">
            <Building2 className="mr-2 h-4 w-4" />
            Client Setup
          </TabsTrigger>
          <TabsTrigger value="api">
            <Key className="mr-2 h-4 w-4" />
            API Keys
          </TabsTrigger>
          <TabsTrigger value="governance">
            <Shield className="mr-2 h-4 w-4" />
            Governance
          </TabsTrigger>
          <TabsTrigger value="notifications">
            <Bell className="mr-2 h-4 w-4" />
            Notifications
          </TabsTrigger>
        </TabsList>

        {/* Client Setup Tab */}
        <TabsContent value="client" className="space-y-6">
          {/* Current Status */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-blue-500" />
                Current Deployment
              </CardTitle>
              <CardDescription>
                System status and Concierge management
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-lg border p-4">
                  <div className="text-2xl font-bold">{agentCount}</div>
                  <div className="text-sm text-muted-foreground">
                    Total Agents
                  </div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-2xl font-bold text-green-600">Active</div>
                  <div className="text-sm text-muted-foreground">
                    Concierge Status
                  </div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-2xl font-bold">{config.organization}</div>
                  <div className="text-sm text-muted-foreground">
                    Organization
                  </div>
                </div>
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">Update Concierge</div>
                  <div className="text-sm text-muted-foreground">
                    Regenerate the Concierge with awareness of all current agents.
                    Do this after adding or removing agents.
                  </div>
                </div>
                <Button
                  variant="outline"
                  onClick={handleRegenerateConcierge}
                  disabled={isRegenerating}
                >
                  {isRegenerating ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="mr-2 h-4 w-4" />
                  )}
                  Update Concierge
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* New Client Setup */}
          <Card className="border-amber-200 bg-amber-50/50 dark:border-amber-900 dark:bg-amber-950/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
                <AlertTriangle className="h-5 w-5" />
                New Client Setup
              </CardTitle>
              <CardDescription className="text-amber-600 dark:text-amber-500">
                Reset the system for a new client deployment. This will DELETE all existing agents and knowledge bases.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Client Name *</label>
                  <Input
                    value={clientName}
                    onChange={(e) => setClientName(e.target.value)}
                    placeholder="e.g., Cleveland Production"
                  />
                  <p className="text-xs text-muted-foreground">
                    Internal name for this deployment
                  </p>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Organization *</label>
                  <Input
                    value={organization}
                    onChange={(e) => setOrganization(e.target.value)}
                    placeholder="e.g., City of Cleveland"
                  />
                  <p className="text-xs text-muted-foreground">
                    Displayed to end users
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Description</label>
                <Textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional description of this deployment..."
                  rows={2}
                />
              </div>

              <Separator />

              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button
                    variant="destructive"
                    disabled={!clientName.trim() || !organization.trim() || isResetting}
                    className="w-full"
                  >
                    {isResetting ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="mr-2 h-4 w-4" />
                    )}
                    Reset System for New Client
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle className="flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5 text-destructive" />
                      Confirm System Reset
                    </AlertDialogTitle>
                    <AlertDialogDescription className="space-y-2">
                      <p>This action will permanently delete:</p>
                      <ul className="list-disc list-inside space-y-1 text-sm">
                        <li><strong>{agentCount} agents</strong> and their configurations</li>
                        <li><strong>All knowledge base documents</strong></li>
                        <li><strong>All vector embeddings</strong></li>
                      </ul>
                      <p className="pt-2">
                        A fresh Concierge will be created for <strong>{organization || "the new client"}</strong>.
                      </p>
                      <p className="font-medium text-destructive pt-2">
                        This cannot be undone.
                      </p>
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={handleReset}
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                      Yes, Reset Everything
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>

              <div className="flex items-start gap-2 text-sm text-amber-700 dark:text-amber-400">
                <CheckCircle2 className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <span>
                  After reset, a new AI Concierge will be automatically created.
                  Add your agents and the Concierge will learn about them.
                </span>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* API Keys Tab */}
        <TabsContent value="api" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>LLM Provider</CardTitle>
              <CardDescription>
                Select and configure your AI provider
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4">
                <Button
                  variant={provider === "openai" ? "default" : "outline"}
                  onClick={() => setProvider("openai")}
                  className="flex-1"
                >
                  OpenAI
                </Button>
                <Button
                  variant={provider === "anthropic" ? "default" : "outline"}
                  onClick={() => setProvider("anthropic")}
                  className="flex-1"
                >
                  Anthropic
                </Button>
                <Button
                  variant={provider === "local" ? "default" : "outline"}
                  onClick={() => setProvider("local")}
                  className="flex-1"
                >
                  Local LLM
                </Button>
              </div>
              <Separator />
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  {provider === "openai"
                    ? "OpenAI API Key"
                    : provider === "anthropic"
                    ? "Anthropic API Key"
                    : "Ollama Endpoint"}
                </label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Input
                      type={showApiKey ? "text" : "password"}
                      placeholder={
                        provider === "local"
                          ? "http://localhost:11434"
                          : "sk-..."
                      }
                      defaultValue={
                        provider === "local" ? "http://localhost:11434" : ""
                      }
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
                      onClick={() => setShowApiKey(!showApiKey)}
                    >
                      {showApiKey ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                  <Button>
                    <Save className="mr-2 h-4 w-4" />
                    Save
                  </Button>
                </div>
              </div>
              {provider !== "local" && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">Default Model</label>
                  <Input
                    placeholder={
                      provider === "openai" ? "gpt-4o" : "claude-sonnet-4-20250514"
                    }
                    defaultValue={
                      provider === "openai" ? "gpt-4o" : "claude-sonnet-4-20250514"
                    }
                  />
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>API Usage</CardTitle>
              <CardDescription>Current billing period usage</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-lg border p-4">
                  <div className="text-2xl font-bold">$47.82</div>
                  <div className="text-sm text-muted-foreground">
                    Total spend this month
                  </div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-2xl font-bold">1.2M</div>
                  <div className="text-sm text-muted-foreground">
                    Tokens used
                  </div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-2xl font-bold">2,847</div>
                  <div className="text-sm text-muted-foreground">
                    API calls
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Governance Tab */}
        <TabsContent value="governance" className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Governance Policies</CardTitle>
                <CardDescription>
                  Rules that control AI behavior and human oversight
                </CardDescription>
              </div>
              <Dialog>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Add Policy
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create New Policy</DialogTitle>
                    <DialogDescription>
                      Define a governance rule for AI requests
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Policy Name</label>
                      <Input placeholder="e.g., External Communications Review" />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Trigger Condition</label>
                      <Input placeholder="e.g., domain = Comms AND audience = public" />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Action</label>
                      <Input placeholder="e.g., DRAFT" />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline">Cancel</Button>
                    <Button>Create Policy</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Policy</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead className="hidden md:table-cell">Domain</TableHead>
                    <TableHead className="hidden lg:table-cell">Trigger</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead className="w-[100px]">Status</TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mockPolicies.map((policy) => (
                    <TableRow key={policy.id}>
                      <TableCell className="font-medium">{policy.name}</TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={
                            policy.type === "constitutional"
                              ? "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300"
                              : "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300"
                          }
                        >
                          {policy.type}
                        </Badge>
                      </TableCell>
                      <TableCell className="hidden md:table-cell">
                        {policy.domain}
                      </TableCell>
                      <TableCell className="hidden lg:table-cell font-mono text-xs">
                        {policy.trigger}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{policy.action}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={policy.enabled ? "default" : "secondary"}
                        >
                          {policy.enabled ? "Active" : "Disabled"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <Trash2 className="h-4 w-4 text-muted-foreground" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
              <CardDescription>
                Configure how you receive alerts and updates
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">Escalation Alerts</div>
                  <div className="text-sm text-muted-foreground">
                    Get notified when requests are escalated for review
                  </div>
                </div>
                <Badge>Email + Push</Badge>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">Draft Pending</div>
                  <div className="text-sm text-muted-foreground">
                    Notifications for drafts awaiting approval
                  </div>
                </div>
                <Badge>Push only</Badge>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">Policy Changes</div>
                  <div className="text-sm text-muted-foreground">
                    Alerts when governance policies are modified
                  </div>
                </div>
                <Badge>Email only</Badge>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">Weekly Summary</div>
                  <div className="text-sm text-muted-foreground">
                    Weekly digest of AI activity and metrics
                  </div>
                </div>
                <Badge variant="secondary">Disabled</Badge>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
