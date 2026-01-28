"use client";

import { useEffect, useState } from "react";
import {
  Library,
  Search,
  Bot,
  Shield,
  Zap,
  Tag,
  Plus,
  Loader2,
  RefreshCw,
  Building2,
  Briefcase,
  Sparkles,
  ArrowRight,
  Star,
  Copy,
  CheckCircle,
  Layers,
  BookOpen,
  FolderOpen,
  Upload,
  Calendar,
  Trash2,
  AlertTriangle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { listTemplates, searchTemplates, createAgent, listSystemTemplates, importFromTemplate, deleteSystemTemplate, type AgentTemplate, type SystemTemplate } from "@/lib/api";
import { config } from "@/lib/config";
import { toast } from "sonner";

const categoryConfigs: Record<string, { icon: React.ElementType; gradient: string; bg: string; text: string }> = {
  municipal: {
    icon: Building2,
    gradient: "from-blue-500 to-indigo-600",
    bg: "bg-blue-50 dark:bg-blue-950/30",
    text: "text-blue-700 dark:text-blue-300",
  },
  enterprise: {
    icon: Briefcase,
    gradient: "from-purple-500 to-pink-600",
    bg: "bg-purple-50 dark:bg-purple-950/30",
    text: "text-purple-700 dark:text-purple-300",
  },
};

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<AgentTemplate[]>([]);
  const [savedTemplates, setSavedTemplates] = useState<SystemTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedTemplate, setSelectedTemplate] = useState<AgentTemplate | null>(null);
  const [selectedSavedTemplate, setSelectedSavedTemplate] = useState<SystemTemplate | null>(null);
  const [creating, setCreating] = useState(false);
  const [customId, setCustomId] = useState("");
  const [activeTab, setActiveTab] = useState<"gallery" | "saved">("gallery");
  const [loadingSaved, setLoadingSaved] = useState(false);
  const [importing, setImporting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [mergeMode, setMergeMode] = useState(false);

  async function loadTemplates() {
    try {
      setLoading(true);
      const category = selectedCategory === "all" ? undefined : selectedCategory;
      const data = await listTemplates(category);
      setTemplates(data.templates);
    } catch (error) {
      console.error("Failed to load templates:", error);
      toast.error("Failed to load templates");
    } finally {
      setLoading(false);
    }
  }

  async function loadSavedTemplates() {
    try {
      setLoadingSaved(true);
      const data = await listSystemTemplates();
      setSavedTemplates(data.templates || []);
    } catch (error) {
      console.error("Failed to load saved templates:", error);
      // Don't show error toast - might just be empty
    } finally {
      setLoadingSaved(false);
    }
  }

  async function handleImportTemplate() {
    if (!selectedSavedTemplate) return;

    setImporting(true);
    try {
      const result = await importFromTemplate(selectedSavedTemplate.id, mergeMode);
      toast.success(result.message, {
        description: `Created ${result.created} agents${result.skipped > 0 ? `, skipped ${result.skipped}` : ""}`,
      });
      setSelectedSavedTemplate(null);
      // Redirect to agents page to see the imported agents
      window.location.href = "/agents";
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to import template";
      toast.error(message);
    } finally {
      setImporting(false);
    }
  }

  async function handleDeleteTemplate() {
    if (!selectedSavedTemplate) return;

    setDeleting(true);
    try {
      await deleteSystemTemplate(selectedSavedTemplate.id);
      toast.success(`Template "${selectedSavedTemplate.name}" deleted`);
      setSavedTemplates(savedTemplates.filter(t => t.id !== selectedSavedTemplate.id));
      setSelectedSavedTemplate(null);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to delete template";
      toast.error(message);
    } finally {
      setDeleting(false);
    }
  }

  async function handleSearch() {
    if (!searchQuery.trim()) {
      loadTemplates();
      return;
    }
    try {
      setLoading(true);
      const data = await searchTemplates(searchQuery);
      setTemplates(data.templates);
    } catch (error) {
      console.error("Failed to search templates:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTemplates();
    loadSavedTemplates();
  }, [selectedCategory]);

  async function handleCreateFromTemplate() {
    if (!selectedTemplate || !customId.trim()) return;

    setCreating(true);
    try {
      await createAgent({
        id: customId.toLowerCase().replace(/\s+/g, "-"),
        name: selectedTemplate.name,
        title: selectedTemplate.title,
        domain: selectedTemplate.domain,
        description: selectedTemplate.description,
        capabilities: selectedTemplate.capabilities,
        guardrails: selectedTemplate.guardrails,
        system_prompt: selectedTemplate.system_prompt,
        escalates_to: selectedTemplate.escalates_to,
      });
      toast.success(`Agent "${customId}" created successfully from template`);
      setSelectedTemplate(null);
      setCustomId("");
    } catch (error) {
      console.error("Failed to create agent:", error);
      toast.error("Failed to create agent from template");
    } finally {
      setCreating(false);
    }
  }

  const municipalCount = templates.filter(t => t.category === "municipal").length;
  const enterpriseCount = templates.filter(t => t.category === "enterprise").length;

  if (loading && templates.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Gradient Header */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-pink-500 via-rose-500 to-orange-500 p-8 text-white shadow-2xl">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDM0aDR2MmgtNHYtMnptMC04aDR2Nmg0djJoLTh2LTh6bTAgMTZoOHYyaC04di0yem0tMTYgMGg0djJoLTR2LTJ6bTAtOGg0djZoNHYyaC04di04em0wIDE2aDh2MmgtOviz0yeiIvPjwvZz48L2c+PC9zdmc+')] opacity-30"></div>
        <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-white/10 blur-3xl"></div>
        <div className="absolute -bottom-20 -left-20 h-64 w-64 rounded-full bg-orange-300/20 blur-3xl"></div>
        <div className="relative">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/20 backdrop-blur-sm">
                  <Library className="h-7 w-7" />
                </div>
                <div>
                  <h1 className="text-3xl font-bold tracking-tight">Agent Templates</h1>
                  <p className="text-pink-100">Pre-built configurations for rapid deployment</p>
                </div>
              </div>
              <p className="mt-4 max-w-xl text-white/80">
                Jumpstart your AI agents with battle-tested templates designed for {config.organization}.
                Each template includes optimized prompts, guardrails, and capabilities.
              </p>
            </div>
            <div className="hidden lg:flex items-center gap-3">
              {/* Gallery/Saved Tab Switcher */}
              <div className="flex bg-white/20 rounded-lg p-1">
                <button
                  onClick={() => setActiveTab("gallery")}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                    activeTab === "gallery"
                      ? "bg-white text-pink-600 shadow"
                      : "text-white hover:bg-white/10"
                  }`}
                >
                  <Library className="h-4 w-4 inline mr-2" />
                  Gallery
                </button>
                <button
                  onClick={() => setActiveTab("saved")}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                    activeTab === "saved"
                      ? "bg-white text-pink-600 shadow"
                      : "text-white hover:bg-white/10"
                  }`}
                >
                  <FolderOpen className="h-4 w-4 inline mr-2" />
                  Saved ({savedTemplates.length})
                </button>
              </div>
              <Button
                variant="secondary"
                className="bg-white/20 hover:bg-white/30 border-0 text-white"
                onClick={() => { loadTemplates(); loadSavedTemplates(); }}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-pink-50 to-rose-100 dark:from-pink-950/50 dark:to-rose-900/30">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-pink-500/20"></div>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-pink-600/70 dark:text-pink-400">Total Templates</p>
                <p className="text-3xl font-bold text-pink-700 dark:text-pink-300">{templates.length}</p>
                <p className="text-xs text-pink-600/60 dark:text-pink-400/60 mt-1">Ready to deploy</p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-pink-500/20">
                <Layers className="h-6 w-6 text-pink-600 dark:text-pink-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-blue-950/50 dark:to-indigo-900/30">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-blue-500/20"></div>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-blue-600/70 dark:text-blue-400">Municipal</p>
                <p className="text-3xl font-bold text-blue-700 dark:text-blue-300">{municipalCount}</p>
                <p className="text-xs text-blue-600/60 dark:text-blue-400/60 mt-1">Government-focused</p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/20">
                <Building2 className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-purple-50 to-violet-100 dark:from-purple-950/50 dark:to-violet-900/30">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-purple-500/20"></div>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-purple-600/70 dark:text-purple-400">Enterprise</p>
                <p className="text-3xl font-bold text-purple-700 dark:text-purple-300">{enterpriseCount}</p>
                <p className="text-xs text-purple-600/60 dark:text-purple-400/60 mt-1">Business-focused</p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-purple-500/20">
                <Briefcase className="h-6 w-6 text-purple-600 dark:text-purple-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-amber-50 to-orange-100 dark:from-amber-950/50 dark:to-orange-900/30">
          <div className="absolute right-0 top-0 h-24 w-24 translate-x-8 -translate-y-8 rounded-full bg-amber-500/20"></div>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-amber-600/70 dark:text-amber-400">Featured</p>
                <p className="text-3xl font-bold text-amber-700 dark:text-amber-300">
                  {templates.filter(t => t.tags?.includes("featured")).length || 3}
                </p>
                <p className="text-xs text-amber-600/60 dark:text-amber-400/60 mt-1">Top rated</p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-500/20">
                <Star className="h-6 w-6 text-amber-600 dark:text-amber-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Conditional Content Based on Tab */}
      {activeTab === "gallery" ? (
        <>
          {/* Search and Filters */}
          <Card className="border-0 shadow-lg">
            <CardContent className="p-4">
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search templates by name, domain, or capability..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                    className="pl-10 bg-muted/50"
                  />
                </div>
                <Tabs value={selectedCategory} onValueChange={setSelectedCategory}>
                  <TabsList className="bg-muted/50">
                    <TabsTrigger value="all" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-pink-500 data-[state=active]:to-rose-500 data-[state=active]:text-white">
                      All
                    </TabsTrigger>
                    <TabsTrigger value="municipal" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-blue-500 data-[state=active]:to-indigo-500 data-[state=active]:text-white">
                      <Building2 className="h-4 w-4 mr-1" />
                      Municipal
                    </TabsTrigger>
                    <TabsTrigger value="enterprise" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-purple-500 data-[state=active]:to-pink-500 data-[state=active]:text-white">
                      <Briefcase className="h-4 w-4 mr-1" />
                      Enterprise
                    </TabsTrigger>
                  </TabsList>
                </Tabs>
              </div>
            </CardContent>
          </Card>

          {/* Templates Grid */}
      {templates.length === 0 ? (
        <Card className="border-0 shadow-lg">
          <CardContent className="text-center py-16">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-pink-500 to-rose-500 text-white mx-auto mb-4">
              <Library className="h-8 w-8" />
            </div>
            <h3 className="text-xl font-semibold mb-2">No templates found</h3>
            <p className="text-muted-foreground max-w-md mx-auto">
              {searchQuery ? "Try a different search term or browse all categories" : "No templates available in this category yet"}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {templates.map((template) => {
            const categoryConfig = categoryConfigs[template.category] || categoryConfigs.enterprise;
            const CategoryIcon = categoryConfig.icon;
            return (
              <Card
                key={template.id}
                className="group relative overflow-hidden border-0 shadow-lg hover:shadow-xl transition-all duration-300 cursor-pointer"
                onClick={() => {
                  setSelectedTemplate(template);
                  setCustomId(template.id);
                }}
              >
                {/* Gradient accent top */}
                <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${categoryConfig.gradient}`}></div>

                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${categoryConfig.gradient} text-white shadow-lg group-hover:scale-110 transition-transform`}>
                        <Bot className="h-6 w-6" />
                      </div>
                      <div>
                        <CardTitle className="text-base group-hover:text-primary transition-colors">{template.name}</CardTitle>
                        <p className="text-xs text-muted-foreground">{template.title}</p>
                      </div>
                    </div>
                    <Badge className={`${categoryConfig.bg} ${categoryConfig.text} border-0`}>
                      <CategoryIcon className="h-3 w-3 mr-1" />
                      {template.category}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                    {template.description}
                  </p>

                  {/* Capabilities */}
                  <div className="mb-3">
                    <p className="text-xs font-medium mb-2 flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                      <Zap className="h-3 w-3" />
                      Capabilities
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {template.capabilities.slice(0, 3).map((cap) => (
                        <Badge key={cap} variant="secondary" className="text-xs bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                          {cap}
                        </Badge>
                      ))}
                      {template.capabilities.length > 3 && (
                        <Badge variant="outline" className="text-xs">
                          +{template.capabilities.length - 3}
                        </Badge>
                      )}
                    </div>
                  </div>

                  {/* Guardrails */}
                  <div className="mb-3">
                    <p className="text-xs font-medium mb-2 flex items-center gap-1 text-amber-600 dark:text-amber-400">
                      <Shield className="h-3 w-3" />
                      Guardrails
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {template.guardrails.slice(0, 2).map((guard) => (
                        <Badge key={guard} variant="outline" className="text-xs text-amber-600 border-amber-200 dark:text-amber-400 dark:border-amber-800">
                          {guard}
                        </Badge>
                      ))}
                      {template.guardrails.length > 2 && (
                        <Badge variant="outline" className="text-xs">
                          +{template.guardrails.length - 2}
                        </Badge>
                      )}
                    </div>
                  </div>

                  {/* Tags */}
                  <div className="flex flex-wrap gap-1">
                    {template.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs bg-muted/50">
                        <Tag className="h-2 w-2 mr-1" />
                        {tag}
                      </Badge>
                    ))}
                  </div>

                  {/* Hover action */}
                  <div className="mt-4 pt-3 border-t flex items-center justify-between opacity-0 group-hover:opacity-100 transition-opacity">
                    <span className="text-xs text-muted-foreground">Click to deploy</span>
                    <ArrowRight className="h-4 w-4 text-primary" />
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
        </>
      ) : (
        /* Saved Templates Section */
        <Card className="border-0 shadow-lg">
          <CardHeader className="border-b bg-muted/30">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <FolderOpen className="h-5 w-5 text-blue-500" />
                  Saved Configurations
                </CardTitle>
                <CardDescription>
                  Your exported agent configurations that can be loaded to restore a complete setup
                </CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={loadSavedTemplates} disabled={loadingSaved}>
                <RefreshCw className={`h-4 w-4 mr-2 ${loadingSaved ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-6">
            {loadingSaved ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : savedTemplates.length === 0 ? (
              <div className="text-center py-12">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-500 text-white mx-auto mb-4">
                  <FolderOpen className="h-8 w-8" />
                </div>
                <h3 className="text-xl font-semibold mb-2">No saved templates</h3>
                <p className="text-muted-foreground max-w-md mx-auto">
                  Save your current agent configuration from the Agents page using "Save as Template"
                </p>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {savedTemplates.map((template) => (
                  <Card
                    key={template.id}
                    className="group relative overflow-hidden border hover:border-blue-500/50 hover:shadow-md transition-all cursor-pointer"
                    onClick={() => setSelectedSavedTemplate(template)}
                  >
                    <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 to-indigo-500"></div>
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-500 text-white shadow-lg">
                            <FolderOpen className="h-6 w-6" />
                          </div>
                          <div>
                            <CardTitle className="text-base">{template.name}</CardTitle>
                            <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                              <Calendar className="h-3 w-3" />
                              {new Date(template.created_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                        <Badge className="bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 border-0">
                          {template.agent_count} agents
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                        {template.description || "No description provided"}
                      </p>
                      <div className="flex items-center justify-between pt-3 border-t opacity-0 group-hover:opacity-100 transition-opacity">
                        <span className="text-xs text-muted-foreground">Click to view details</span>
                        <ArrowRight className="h-4 w-4 text-blue-500" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Saved Template Detail Dialog */}
      <Dialog open={!!selectedSavedTemplate} onOpenChange={() => setSelectedSavedTemplate(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          {selectedSavedTemplate && (
            <>
              <DialogHeader>
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-500 text-white shadow-lg">
                    <FolderOpen className="h-6 w-6" />
                  </div>
                  <div>
                    <DialogTitle className="text-xl">{selectedSavedTemplate.name}</DialogTitle>
                    <DialogDescription>
                      Saved on {new Date(selectedSavedTemplate.created_at).toLocaleDateString()} · {selectedSavedTemplate.agent_count} agents
                    </DialogDescription>
                  </div>
                </div>
              </DialogHeader>

              <div className="space-y-4 mt-4">
                {selectedSavedTemplate.description && (
                  <p className="text-sm text-muted-foreground">{selectedSavedTemplate.description}</p>
                )}

                <div>
                  <p className="text-sm font-medium mb-3 flex items-center gap-2">
                    <Bot className="h-4 w-4 text-blue-500" />
                    Agents in this Template
                  </p>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {selectedSavedTemplate.agents?.map((agent) => (
                      <div key={agent.id} className="flex items-center gap-3 p-3 rounded-lg border bg-muted/30">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-green-500 text-white">
                          <Bot className="h-4 w-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate">{agent.name}</p>
                          <p className="text-xs text-muted-foreground truncate">{agent.description}</p>
                        </div>
                        <Badge variant="outline">{agent.domain}</Badge>
                      </div>
                    )) || <p className="text-sm text-muted-foreground">No agent details available</p>}
                  </div>
                </div>

                {/* Import Options */}
                <div className="pt-4 border-t space-y-4">
                  <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                    <div>
                      <p className="text-sm font-medium">Merge with existing agents</p>
                      <p className="text-xs text-muted-foreground">
                        {mergeMode
                          ? "Add template agents alongside existing ones (skip duplicates)"
                          : "Replace all existing agents with template agents"}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs ${!mergeMode ? "text-primary font-medium" : "text-muted-foreground"}`}>Replace</span>
                      <button
                        onClick={() => setMergeMode(!mergeMode)}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          mergeMode ? "bg-blue-500" : "bg-muted"
                        }`}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                            mergeMode ? "translate-x-6" : "translate-x-1"
                          }`}
                        />
                      </button>
                      <span className={`text-xs ${mergeMode ? "text-primary font-medium" : "text-muted-foreground"}`}>Merge</span>
                    </div>
                  </div>

                  {!mergeMode && (
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30">
                      <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-amber-800 dark:text-amber-200">Replace Mode</p>
                        <p className="text-xs text-amber-700 dark:text-amber-300">
                          This will delete all existing agents (except the Concierge) before importing.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <DialogFooter className="mt-6 flex-col sm:flex-row gap-2">
                <Button
                  variant="destructive"
                  onClick={handleDeleteTemplate}
                  disabled={deleting || importing}
                  className="sm:mr-auto"
                >
                  {deleting ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Trash2 className="h-4 w-4 mr-2" />
                  )}
                  Delete Template
                </Button>
                <Button variant="outline" onClick={() => setSelectedSavedTemplate(null)}>
                  Cancel
                </Button>
                <Button
                  onClick={handleImportTemplate}
                  disabled={importing || deleting}
                  className="bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600"
                >
                  {importing ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Upload className="h-4 w-4 mr-2" />
                  )}
                  Load Template
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Create from Template Dialog */}
      <Dialog open={!!selectedTemplate} onOpenChange={() => setSelectedTemplate(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          {selectedTemplate && (
            <>
              <DialogHeader>
                <div className="flex items-center gap-3">
                  <div className={`flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${categoryConfigs[selectedTemplate.category]?.gradient || "from-purple-500 to-pink-500"} text-white shadow-lg`}>
                    <Bot className="h-6 w-6" />
                  </div>
                  <div>
                    <DialogTitle className="text-xl">Deploy from Template</DialogTitle>
                    <DialogDescription>
                      Create a new agent based on "{selectedTemplate.name}"
                    </DialogDescription>
                  </div>
                </div>
              </DialogHeader>

              <div className="space-y-4 mt-4">
                {/* Template Summary */}
                <Card className="bg-gradient-to-br from-muted/50 to-muted border-0">
                  <CardContent className="pt-4">
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Domain</p>
                        <p className="text-sm font-semibold">{selectedTemplate.domain}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Escalates To</p>
                        <p className="text-sm font-semibold">{selectedTemplate.escalates_to}</p>
                      </div>
                    </div>
                    <div className="mt-4">
                      <p className="text-sm font-medium text-muted-foreground">Description</p>
                      <p className="text-sm">{selectedTemplate.description}</p>
                    </div>
                  </CardContent>
                </Card>

                {/* Capabilities */}
                <div>
                  <p className="text-sm font-medium mb-2 flex items-center gap-2">
                    <div className="flex h-6 w-6 items-center justify-center rounded-md bg-emerald-100 dark:bg-emerald-900">
                      <Zap className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    </div>
                    Capabilities
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {selectedTemplate.capabilities.map((cap) => (
                      <Badge key={cap} className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300 hover:bg-emerald-200">
                        {cap}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Guardrails */}
                <div>
                  <p className="text-sm font-medium mb-2 flex items-center gap-2">
                    <div className="flex h-6 w-6 items-center justify-center rounded-md bg-amber-100 dark:bg-amber-900">
                      <Shield className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                    </div>
                    Guardrails
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {selectedTemplate.guardrails.map((guard) => (
                      <Badge key={guard} variant="outline" className="text-amber-600 border-amber-200 dark:text-amber-400 dark:border-amber-800">
                        {guard}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Custom Agent ID */}
                <div className="pt-4 border-t">
                  <label className="text-sm font-medium mb-2 block">Agent ID</label>
                  <Input
                    value={customId}
                    onChange={(e) => setCustomId(e.target.value)}
                    placeholder="my-custom-agent"
                    className="font-mono bg-muted/50"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Unique identifier for the agent (lowercase, no spaces)
                  </p>
                </div>
              </div>

              <DialogFooter className="mt-6">
                <Button variant="outline" onClick={() => setSelectedTemplate(null)}>
                  Cancel
                </Button>
                <Button
                  onClick={handleCreateFromTemplate}
                  disabled={creating || !customId.trim()}
                  className="bg-gradient-to-r from-pink-500 to-rose-500 hover:from-pink-600 hover:to-rose-600"
                >
                  {creating ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Copy className="h-4 w-4 mr-2" />
                  )}
                  Deploy Agent
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
