"use client";

import { useState, useMemo, useCallback } from "react";
import {
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  Check,
  ExternalLink,
  ArrowUpDown,
  Layers,
  List,
  Loader2,
  AlertCircle,
  Sparkles,
  Building2,
  User,
  Database,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

// =============================================================================
// Types
// =============================================================================

// All candidate types supported by the system
export type CandidateTypeValue =
  // Leadership hierarchy
  | "executive"    // Mayor, Governor, CEO
  | "cabinet"      // Chief Officers (CFO, COO)
  | "director"     // Department Directors
  | "deputy"       // Deputy/Assistant Directors
  | "leadership"   // Generic leadership (fallback)
  // Department categories
  | "public-safety"  // Police, Fire, Emergency
  | "public-works"   // Streets, Water, Utilities
  | "finance"        // Budget, Accounting
  | "legal"          // Law, Attorney, Clerk
  | "planning"       // Development, Zoning
  | "health"         // Health, Human Services
  | "parks-rec"      // Parks, Recreation, Libraries
  | "admin"          // HR, IT, Communications
  | "department"     // Generic department (fallback)
  // Other
  | "data-portal"    // Open data platforms
  | "service"        // Citizen-facing services
  | "board";         // Boards, Commissions

// Type categories for grouping
export type TypeCategory = "leadership" | "departments" | "other";

export interface CandidateAgent {
  id: string;
  name: string;
  type: CandidateTypeValue | string;
  department?: string;
  description?: string;
  confidence: "high" | "medium" | "low";
  confidenceScore?: number; // 0-100
  sourceUrls: string[];
  suggestedAgentName?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
  selected: boolean;
}

interface CandidateAgentsPanelProps {
  candidates: CandidateAgent[];
  onSelectionChange: (candidates: CandidateAgent[]) => void;
  onCreateAgents: (selected: CandidateAgent[]) => void;
  isLoading?: boolean;
  isCreating?: boolean;
  orgName?: string;
}

type SortField = "confidence" | "name" | "department" | "type" | "category";
type SortDirection = "asc" | "desc";
type ViewMode = "flat" | "grouped";

// =============================================================================
// Type Configuration
// =============================================================================

// Human-readable labels for types
const TYPE_LABELS: Record<string, string> = {
  // Leadership
  executive: "Executive",
  cabinet: "Cabinet",
  director: "Director",
  deputy: "Deputy",
  leadership: "Leadership",
  // Departments
  "public-safety": "Public Safety",
  "public-works": "Public Works",
  finance: "Finance",
  legal: "Legal",
  planning: "Planning",
  health: "Health",
  "parks-rec": "Parks & Rec",
  admin: "Admin",
  department: "Department",
  // Other
  "data-portal": "Data Portal",
  "data_portal": "Data Portal", // Legacy support
  service: "Service",
  board: "Board",
};

// Map types to categories
const TYPE_CATEGORIES: Record<string, TypeCategory> = {
  executive: "leadership",
  cabinet: "leadership",
  director: "leadership",
  deputy: "leadership",
  leadership: "leadership",
  "public-safety": "departments",
  "public-works": "departments",
  finance: "departments",
  legal: "departments",
  planning: "departments",
  health: "departments",
  "parks-rec": "departments",
  admin: "departments",
  department: "departments",
  "data-portal": "other",
  "data_portal": "other",
  service: "other",
  board: "other",
};

const CATEGORY_LABELS: Record<TypeCategory, string> = {
  leadership: "Leadership",
  departments: "Departments",
  other: "Other",
};

const CATEGORY_ORDER: TypeCategory[] = ["leadership", "departments", "other"];

// =============================================================================
// Helper Functions
// =============================================================================

const getTypeLabel = (type: string): string => {
  return TYPE_LABELS[type] || type.replace(/[-_]/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
};

const getTypeCategory = (type: string): TypeCategory => {
  return TYPE_CATEGORIES[type] || "other";
};

const getConfidenceScore = (confidence: string): number => {
  switch (confidence) {
    case "high": return 90;
    case "medium": return 60;
    case "low": return 30;
    default: return 50;
  }
};

const getTypeIcon = (type: string) => {
  switch (type) {
    // Leadership
    case "executive":
    case "cabinet":
    case "leadership":
      return User;
    case "director":
    case "deputy":
      return User;
    // Departments
    case "public-safety":
      return Sparkles; // Could use Shield
    case "public-works":
    case "planning":
      return Building2;
    case "finance":
    case "legal":
    case "admin":
      return Building2;
    case "health":
    case "parks-rec":
      return Building2;
    case "department":
      return Building2;
    // Other
    case "data-portal":
    case "data_portal":
      return Database;
    case "service":
      return Sparkles;
    case "board":
      return Building2;
    default:
      return Sparkles;
  }
};

const getTypeColor = (type: string) => {
  const category = getTypeCategory(type);
  switch (category) {
    case "leadership":
      // Different shades for leadership hierarchy
      if (type === "executive") return "border-blue-500/50 bg-blue-600/10 text-blue-400";
      if (type === "cabinet") return "border-blue-400/50 bg-blue-500/10 text-blue-400";
      if (type === "director") return "border-indigo-400/50 bg-indigo-500/10 text-indigo-400";
      return "border-blue-400/50 bg-blue-500/10 text-blue-400";
    case "departments":
      // Different colors by department type
      if (type === "public-safety") return "border-red-400/50 bg-red-500/10 text-red-400";
      if (type === "public-works") return "border-orange-400/50 bg-orange-500/10 text-orange-400";
      if (type === "finance") return "border-emerald-400/50 bg-emerald-500/10 text-emerald-400";
      if (type === "legal") return "border-slate-400/50 bg-slate-500/10 text-slate-400";
      if (type === "planning") return "border-cyan-400/50 bg-cyan-500/10 text-cyan-400";
      if (type === "health") return "border-pink-400/50 bg-pink-500/10 text-pink-400";
      if (type === "parks-rec") return "border-lime-400/50 bg-lime-500/10 text-lime-400";
      if (type === "admin") return "border-violet-400/50 bg-violet-500/10 text-violet-400";
      return "border-purple-400/50 bg-purple-500/10 text-purple-400";
    case "other":
      if (type === "data-portal" || type === "data_portal") return "border-amber-400/50 bg-amber-500/10 text-amber-400";
      if (type === "service") return "border-green-400/50 bg-green-500/10 text-green-400";
      if (type === "board") return "border-teal-400/50 bg-teal-500/10 text-teal-400";
      return "border-gray-400/50 bg-gray-500/10 text-gray-400";
    default:
      return "border-gray-400/50 bg-gray-500/10 text-gray-400";
  }
};

const getConfidenceColor = (confidence: string) => {
  switch (confidence) {
    case "high": return "bg-green-500/20 text-green-400 border-green-500/30";
    case "medium": return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
    case "low": return "bg-red-500/20 text-red-400 border-red-500/30";
    default: return "bg-gray-500/20 text-gray-400 border-gray-500/30";
  }
};

// =============================================================================
// Sub-Components
// =============================================================================

function CandidateRow({
  candidate,
  onToggle,
  expanded,
  onToggleExpand,
}: {
  candidate: CandidateAgent;
  onToggle: () => void;
  expanded: boolean;
  onToggleExpand: () => void;
}) {
  const TypeIcon = getTypeIcon(candidate.type);
  const hasDescription = candidate.description && candidate.description.length > 0;
  const hasSources = candidate.sourceUrls && candidate.sourceUrls.length > 0;

  return (
    <div
      className={`group relative rounded-lg border transition-all duration-200 ${
        candidate.selected
          ? "border-purple-500/50 bg-purple-500/5"
          : "border-border/50 bg-card/50 hover:border-border hover:bg-card"
      }`}
    >
      <div className="p-4">
        <div className="flex items-start gap-4">
          {/* Checkbox */}
          <button
            onClick={onToggle}
            className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 transition-all ${
              candidate.selected
                ? "border-purple-500 bg-purple-500"
                : "border-muted-foreground/30 hover:border-purple-400"
            }`}
            aria-label={candidate.selected ? "Deselect" : "Select"}
          >
            {candidate.selected && <Check className="h-3 w-3 text-white" />}
          </button>

          {/* Main Content */}
          <div className="min-w-0 flex-1">
            {/* Header Row */}
            <div className="flex flex-wrap items-center gap-2">
              {/* Type Icon + Name */}
              <div className="flex items-center gap-2">
                <div className={`rounded-md p-1 ${getTypeColor(candidate.type)}`}>
                  <TypeIcon className="h-3.5 w-3.5" />
                </div>
                <span className="font-medium text-foreground">
                  {candidate.name}
                </span>
              </div>

              {/* Type Badge */}
              <Badge
                variant="outline"
                className={`text-xs ${getTypeColor(candidate.type)}`}
              >
                {getTypeLabel(candidate.type)}
              </Badge>

              {/* Confidence Badge */}
              <Badge
                variant="outline"
                className={`text-xs capitalize ${getConfidenceColor(candidate.confidence)}`}
              >
                {candidate.confidence}
                {candidate.confidenceScore && ` (${candidate.confidenceScore}%)`}
              </Badge>

              {/* Tags */}
              {candidate.tags?.slice(0, 3).map((tag) => (
                <Badge
                  key={tag}
                  variant="secondary"
                  className="text-xs bg-muted/50"
                >
                  {tag}
                </Badge>
              ))}
              {(candidate.tags?.length || 0) > 3 && (
                <Badge variant="secondary" className="text-xs bg-muted/50">
                  +{(candidate.tags?.length || 0) - 3}
                </Badge>
              )}
            </div>

            {/* Suggested Agent Name */}
            {candidate.suggestedAgentName && (
              <div className="mt-1.5 text-sm text-muted-foreground">
                <span className="text-purple-400">Agent:</span>{" "}
                {candidate.suggestedAgentName}
              </div>
            )}

            {/* Description Preview */}
            {hasDescription && !expanded && (
              <p className="mt-2 text-sm text-muted-foreground line-clamp-2">
                {candidate.description}
              </p>
            )}

            {/* Expanded Content */}
            {expanded && (
              <div className="mt-3 space-y-3">
                {hasDescription && (
                  <p className="text-sm text-muted-foreground">
                    {candidate.description}
                  </p>
                )}

                {hasSources && (
                  <div className="flex flex-wrap gap-2">
                    <span className="text-xs text-muted-foreground">Sources:</span>
                    {candidate.sourceUrls.map((url, i) => (
                      <a
                        key={i}
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="inline-flex items-center gap-1 rounded-md bg-muted/50 px-2 py-0.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                      >
                        <ExternalLink className="h-3 w-3" />
                        {new URL(url).hostname}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Expand Button */}
          {(hasDescription || hasSources) && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggleExpand();
              }}
              className="shrink-0 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              aria-label={expanded ? "Collapse" : "Expand"}
            >
              {expanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function GroupedView({
  groups,
  onToggle,
  expandedIds,
  onToggleExpand,
}: {
  groups: Map<string, CandidateAgent[]>;
  onToggle: (id: string) => void;
  expandedIds: Set<string>;
  onToggleExpand: (id: string) => void;
}) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(groups.keys())
  );

  const toggleGroup = (groupName: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupName)) {
        next.delete(groupName);
      } else {
        next.add(groupName);
      }
      return next;
    });
  };

  return (
    <div className="space-y-4">
      {Array.from(groups.entries()).map(([groupName, items]) => {
        const isExpanded = expandedGroups.has(groupName);
        const selectedCount = items.filter((c) => c.selected).length;

        return (
          <div key={groupName} className="rounded-lg border border-border/50 overflow-hidden">
            <button
              onClick={() => toggleGroup(groupName)}
              className="w-full flex items-center justify-between p-3 bg-muted/30 hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                {isExpanded ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronUp className="h-4 w-4 text-muted-foreground" />
                )}
                <span className="font-medium">
                  {getTypeLabel(groupName)}
                </span>
                <Badge variant="secondary" className="text-xs">
                  {items.length} candidates
                </Badge>
                {selectedCount > 0 && (
                  <Badge className="text-xs bg-purple-500/20 text-purple-400 border-purple-500/30">
                    {selectedCount} selected
                  </Badge>
                )}
              </div>
            </button>

            {isExpanded && (
              <div className="p-3 space-y-2">
                {items.map((candidate) => (
                  <CandidateRow
                    key={candidate.id}
                    candidate={candidate}
                    onToggle={() => onToggle(candidate.id)}
                    expanded={expandedIds.has(candidate.id)}
                    onToggleExpand={() => onToggleExpand(candidate.id)}
                  />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function EmptyState({ searchQuery }: { searchQuery: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="rounded-full bg-muted p-4 mb-4">
        <Search className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="font-semibold text-lg mb-1">No candidates found</h3>
      <p className="text-muted-foreground text-sm max-w-sm">
        {searchQuery
          ? `No candidates match "${searchQuery}". Try adjusting your search or filters.`
          : "No candidate agents were discovered. Try scanning a different URL."}
      </p>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="space-y-3">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="rounded-lg border border-border/50 p-4">
          <div className="flex items-start gap-4">
            <Skeleton className="h-5 w-5 rounded" />
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-2">
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-5 w-20" />
                <Skeleton className="h-5 w-16" />
              </div>
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-4 w-full" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function CandidateAgentsPanel({
  candidates,
  onSelectionChange,
  onCreateAgents,
  isLoading = false,
  isCreating = false,
  orgName,
}: CandidateAgentsPanelProps) {
  // State
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilters, setTypeFilters] = useState<Set<string>>(new Set());
  const [confidenceFilters, setConfidenceFilters] = useState<Set<string>>(new Set());
  const [hasSourcesOnly, setHasSourcesOnly] = useState(false);
  const [sortField, setSortField] = useState<SortField>("confidence");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [viewMode, setViewMode] = useState<ViewMode>("flat");
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(0);
  const pageSize = 50;

  // Derived: unique types and departments
  const uniqueTypes = useMemo(
    () => [...new Set(candidates.map((c) => c.type))],
    [candidates]
  );
  const uniqueDepartments = useMemo(
    () => [...new Set(candidates.map((c) => c.department).filter(Boolean))],
    [candidates]
  );

  // Filter and sort candidates
  const filteredCandidates = useMemo(() => {
    let result = [...candidates];

    // Search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (c) =>
          c.name.toLowerCase().includes(query) ||
          c.department?.toLowerCase().includes(query) ||
          c.description?.toLowerCase().includes(query) ||
          c.suggestedAgentName?.toLowerCase().includes(query) ||
          c.sourceUrls.some((url) => url.toLowerCase().includes(query))
      );
    }

    // Type filter
    if (typeFilters.size > 0) {
      result = result.filter((c) => typeFilters.has(c.type));
    }

    // Confidence filter
    if (confidenceFilters.size > 0) {
      result = result.filter((c) => confidenceFilters.has(c.confidence));
    }

    // Has sources filter
    if (hasSourcesOnly) {
      result = result.filter((c) => c.sourceUrls.length > 0);
    }

    // Sort
    result.sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case "confidence":
          comparison = getConfidenceScore(a.confidence) - getConfidenceScore(b.confidence);
          break;
        case "name":
          comparison = a.name.localeCompare(b.name);
          break;
        case "category":
          // Sort by category order (Leadership, Departments, Other)
          const catA = CATEGORY_ORDER.indexOf(getTypeCategory(a.type));
          const catB = CATEGORY_ORDER.indexOf(getTypeCategory(b.type));
          comparison = catA - catB;
          // If same category, sort by type within category
          if (comparison === 0) {
            comparison = a.type.localeCompare(b.type);
          }
          break;
        case "department":
          comparison = (a.department || "").localeCompare(b.department || "");
          break;
        case "type":
          comparison = a.type.localeCompare(b.type);
          break;
      }
      return sortDirection === "desc" ? -comparison : comparison;
    });

    return result;
  }, [candidates, searchQuery, typeFilters, confidenceFilters, hasSourcesOnly, sortField, sortDirection]);

  // Paginated candidates
  const paginatedCandidates = useMemo(() => {
    const start = page * pageSize;
    return filteredCandidates.slice(start, start + pageSize);
  }, [filteredCandidates, page, pageSize]);

  // Grouped candidates
  const groupedCandidates = useMemo(() => {
    const groups = new Map<string, CandidateAgent[]>();
    for (const candidate of paginatedCandidates) {
      const key = candidate.type;
      if (!groups.has(key)) {
        groups.set(key, []);
      }
      groups.get(key)!.push(candidate);
    }
    return groups;
  }, [paginatedCandidates]);

  // Selection counts
  const selectedCount = candidates.filter((c) => c.selected).length;
  const filteredSelectedCount = filteredCandidates.filter((c) => c.selected).length;
  const totalPages = Math.ceil(filteredCandidates.length / pageSize);

  // Handlers
  const toggleCandidate = useCallback(
    (id: string) => {
      const updated = candidates.map((c) =>
        c.id === id ? { ...c, selected: !c.selected } : c
      );
      onSelectionChange(updated);
    },
    [candidates, onSelectionChange]
  );

  const toggleExpand = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const selectAllFiltered = useCallback(() => {
    const filteredIds = new Set(filteredCandidates.map((c) => c.id));
    const updated = candidates.map((c) =>
      filteredIds.has(c.id) ? { ...c, selected: true } : c
    );
    onSelectionChange(updated);
  }, [candidates, filteredCandidates, onSelectionChange]);

  const clearAllFiltered = useCallback(() => {
    const filteredIds = new Set(filteredCandidates.map((c) => c.id));
    const updated = candidates.map((c) =>
      filteredIds.has(c.id) ? { ...c, selected: false } : c
    );
    onSelectionChange(updated);
  }, [candidates, filteredCandidates, onSelectionChange]);

  const toggleTypeFilter = (type: string) => {
    setTypeFilters((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
    setPage(0);
  };

  const toggleConfidenceFilter = (confidence: string) => {
    setConfidenceFilters((prev) => {
      const next = new Set(prev);
      if (next.has(confidence)) {
        next.delete(confidence);
      } else {
        next.add(confidence);
      }
      return next;
    });
    setPage(0);
  };

  const clearAllFilters = () => {
    setSearchQuery("");
    setTypeFilters(new Set());
    setConfidenceFilters(new Set());
    setHasSourcesOnly(false);
    setPage(0);
  };

  const hasActiveFilters = searchQuery || typeFilters.size > 0 || confidenceFilters.size > 0 || hasSourcesOnly;

  const handleCreate = () => {
    const selected = candidates.filter((c) => c.selected);
    onCreateAgents(selected);
  };

  return (
    <Card className="border-0 shadow-lg overflow-hidden">
      {/* Header */}
      <CardHeader className="border-b bg-muted/30 pb-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2 text-xl">
              <Sparkles className="h-5 w-5 text-purple-500" />
              Candidate Agents
            </CardTitle>
            <CardDescription className="mt-1">
              {isLoading
                ? "Discovering agents..."
                : `Found ${candidates.length} potential agents${orgName ? ` for ${orgName}` : ""}`}
            </CardDescription>
          </div>

          {/* Selection Summary */}
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-2xl font-bold text-purple-400">{selectedCount}</div>
              <div className="text-xs text-muted-foreground">selected</div>
            </div>
            <Separator orientation="vertical" className="h-10" />
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={selectAllFiltered}
                disabled={isLoading}
              >
                Select All
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={clearAllFiltered}
                disabled={isLoading}
              >
                Clear
              </Button>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3 p-4 border-b bg-background/50">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search agents, departments, URLs..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(0);
              }}
              className="pl-9 bg-muted/50"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Type Filter - Grouped by Category */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2">
                <Filter className="h-4 w-4" />
                Type
                {typeFilters.size > 0 && (
                  <Badge variant="secondary" className="ml-1 h-5 px-1.5">
                    {typeFilters.size}
                  </Badge>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-56">
              <DropdownMenuLabel>Filter by Type</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {/* Group types by category */}
              {CATEGORY_ORDER.map((category) => {
                const typesInCategory = uniqueTypes.filter(
                  (type) => getTypeCategory(type) === category
                );
                if (typesInCategory.length === 0) return null;
                return (
                  <div key={category}>
                    <DropdownMenuLabel className="text-xs text-muted-foreground font-normal py-1">
                      {CATEGORY_LABELS[category]}
                    </DropdownMenuLabel>
                    {typesInCategory.map((type) => (
                      <DropdownMenuCheckboxItem
                        key={type}
                        checked={typeFilters.has(type)}
                        onCheckedChange={() => toggleTypeFilter(type)}
                      >
                        <span className={`inline-flex items-center gap-2 ${getTypeColor(type).split(' ')[2]}`}>
                          {getTypeLabel(type)}
                        </span>
                      </DropdownMenuCheckboxItem>
                    ))}
                  </div>
                );
              })}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Confidence Filter */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2">
                <Filter className="h-4 w-4" />
                Confidence
                {confidenceFilters.size > 0 && (
                  <Badge variant="secondary" className="ml-1 h-5 px-1.5">
                    {confidenceFilters.size}
                  </Badge>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuLabel>Filter by Confidence</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {["high", "medium", "low"].map((conf) => (
                <DropdownMenuCheckboxItem
                  key={conf}
                  checked={confidenceFilters.has(conf)}
                  onCheckedChange={() => toggleConfidenceFilter(conf)}
                >
                  <span className="capitalize">{conf}</span>
                </DropdownMenuCheckboxItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Category Quick Filters */}
          <div className="flex gap-1 border-l pl-3 ml-1">
            {CATEGORY_ORDER.map((category) => {
              const typesInCategory = uniqueTypes.filter(
                (t) => getTypeCategory(t) === category
              );
              if (typesInCategory.length === 0) return null;
              const isActive = typesInCategory.some((t) => typeFilters.has(t));
              const allActive = typesInCategory.every((t) => typeFilters.has(t));
              return (
                <Button
                  key={category}
                  variant={allActive ? "default" : isActive ? "secondary" : "outline"}
                  size="sm"
                  onClick={() => {
                    // Toggle all types in this category
                    const newFilters = new Set(typeFilters);
                    if (allActive) {
                      typesInCategory.forEach((t) => newFilters.delete(t));
                    } else {
                      typesInCategory.forEach((t) => newFilters.add(t));
                    }
                    setTypeFilters(newFilters);
                    setPage(0);
                  }}
                  className={allActive ? "bg-purple-600 hover:bg-purple-700" : ""}
                >
                  {CATEGORY_LABELS[category]}
                </Button>
              );
            })}
          </div>

          {/* Has Sources Toggle */}
          <Button
            variant={hasSourcesOnly ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setHasSourcesOnly(!hasSourcesOnly);
              setPage(0);
            }}
            className={hasSourcesOnly ? "bg-purple-600 hover:bg-purple-700" : ""}
          >
            Has Sources
          </Button>

          {/* Clear Filters */}
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllFilters}
              className="text-muted-foreground"
            >
              <X className="h-4 w-4 mr-1" />
              Clear filters
            </Button>
          )}

          <div className="flex-1" />

          {/* Sort */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2">
                <ArrowUpDown className="h-4 w-4" />
                Sort
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Sort by</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuRadioGroup
                value={sortField}
                onValueChange={(v) => setSortField(v as SortField)}
              >
                <DropdownMenuRadioItem value="confidence">Confidence</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="name">Name</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="category">Category</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="type">Type</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="department">Department</DropdownMenuRadioItem>
              </DropdownMenuRadioGroup>
              <DropdownMenuSeparator />
              <DropdownMenuRadioGroup
                value={sortDirection}
                onValueChange={(v) => setSortDirection(v as SortDirection)}
              >
                <DropdownMenuRadioItem value="desc">Descending</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="asc">Ascending</DropdownMenuRadioItem>
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* View Mode */}
          <div className="flex rounded-lg border bg-muted/50 p-0.5">
            <button
              onClick={() => setViewMode("flat")}
              className={`rounded-md p-1.5 transition-colors ${
                viewMode === "flat"
                  ? "bg-background shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              title="Flat list"
            >
              <List className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode("grouped")}
              className={`rounded-md p-1.5 transition-colors ${
                viewMode === "grouped"
                  ? "bg-background shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              title="Group by type"
            >
              <Layers className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Results Count */}
        {!isLoading && (
          <div className="px-4 py-2 text-sm text-muted-foreground border-b bg-muted/20">
            Showing {paginatedCandidates.length} of {filteredCandidates.length} candidates
            {hasActiveFilters && ` (filtered from ${candidates.length})`}
            {filteredSelectedCount > 0 && (
              <span className="text-purple-400 ml-2">
                • {filteredSelectedCount} selected in view
              </span>
            )}
          </div>
        )}

        {/* Content */}
        <ScrollArea className="h-[450px]">
          <div className="p-4">
            {isLoading ? (
              <LoadingState />
            ) : filteredCandidates.length === 0 ? (
              <EmptyState searchQuery={searchQuery} />
            ) : viewMode === "grouped" ? (
              <GroupedView
                groups={groupedCandidates}
                onToggle={toggleCandidate}
                expandedIds={expandedIds}
                onToggleExpand={toggleExpand}
              />
            ) : (
              <div className="space-y-2">
                {paginatedCandidates.map((candidate) => (
                  <CandidateRow
                    key={candidate.id}
                    candidate={candidate}
                    onToggle={() => toggleCandidate(candidate.id)}
                    expanded={expandedIds.has(candidate.id)}
                    onToggleExpand={() => toggleExpand(candidate.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t bg-muted/20">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
            >
              Previous
            </Button>
            <span className="text-sm text-muted-foreground">
              Page {page + 1} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
            >
              Next
            </Button>
          </div>
        )}

        {/* Footer Action */}
        <div className="flex items-center justify-between p-4 border-t bg-gradient-to-r from-purple-500/5 to-violet-500/5">
          <div className="text-sm">
            <span className="text-muted-foreground">Ready to create </span>
            <span className="font-semibold text-purple-400">{selectedCount} agents</span>
          </div>
          <Button
            onClick={handleCreate}
            disabled={selectedCount === 0 || isCreating}
            className="bg-gradient-to-r from-purple-500 to-violet-600 hover:from-purple-600 hover:to-violet-700"
          >
            {isCreating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-4 w-4" />
                Create {selectedCount} Agents
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default CandidateAgentsPanel;
