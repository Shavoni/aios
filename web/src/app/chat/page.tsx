"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import {
  Send,
  Mic,
  MicOff,
  User,
  Loader2,
  Sparkles,
  MessageCircle,
  ArrowRight,
  ArrowLeft,
  Clock,
  Shield,
  Star,
  Building2,
  Phone,
  Mail,
  ChevronRight,
  Briefcase,
  Heart,
  Scale,
  Landmark,
  Users,
  FileText,
  HelpCircle,
  Zap,
  Home,
  Bot,
  ExternalLink,
  X,
  Grid3X3,
} from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  listAgents,
  queryAgent,
  routeQuery,
  createConversation,
  addMessage,
  type AgentConfig,
  type RoutingResponse,
} from "@/lib/api";
import { config } from "@/lib/config";
import { cn } from "@/lib/utils";
import Link from "next/link";

// Domain icon mapping for visual distinction
const domainIcons: Record<string, React.ElementType> = {
  HR: Users,
  Finance: Briefcase,
  Building: Building2,
  PublicHealth: Heart,
  PublicSafety: Shield,
  Legal: Scale,
  "311": Phone,
  Strategy: Landmark,
  Router: Sparkles,
  General: HelpCircle,
};

// Warm, sophisticated color palette for domains - theme-aware
const domainColors: Record<string, { bg: string; text: string; accent: string; gradient: string }> = {
  HR: { bg: "bg-violet-50 dark:bg-violet-950/30", text: "text-violet-700 dark:text-violet-300", accent: "border-violet-200 dark:border-violet-800", gradient: "from-violet-500 to-purple-600" },
  Finance: { bg: "bg-emerald-50 dark:bg-emerald-950/30", text: "text-emerald-700 dark:text-emerald-300", accent: "border-emerald-200 dark:border-emerald-800", gradient: "from-emerald-500 to-teal-600" },
  Building: { bg: "bg-amber-50 dark:bg-amber-950/30", text: "text-amber-700 dark:text-amber-300", accent: "border-amber-200 dark:border-amber-800", gradient: "from-amber-500 to-orange-600" },
  PublicHealth: { bg: "bg-rose-50 dark:bg-rose-950/30", text: "text-rose-700 dark:text-rose-300", accent: "border-rose-200 dark:border-rose-800", gradient: "from-rose-500 to-pink-600" },
  PublicSafety: { bg: "bg-red-50 dark:bg-red-950/30", text: "text-red-700 dark:text-red-300", accent: "border-red-200 dark:border-red-800", gradient: "from-red-500 to-rose-600" },
  Legal: { bg: "bg-slate-50 dark:bg-slate-900/30", text: "text-slate-700 dark:text-slate-300", accent: "border-slate-200 dark:border-slate-700", gradient: "from-slate-500 to-zinc-600" },
  "311": { bg: "bg-sky-50 dark:bg-sky-950/30", text: "text-sky-700 dark:text-sky-300", accent: "border-sky-200 dark:border-sky-800", gradient: "from-sky-500 to-blue-600" },
  Strategy: { bg: "bg-indigo-50 dark:bg-indigo-950/30", text: "text-indigo-700 dark:text-indigo-300", accent: "border-indigo-200 dark:border-indigo-800", gradient: "from-indigo-500 to-blue-600" },
  Router: { bg: "bg-amber-50 dark:bg-amber-950/30", text: "text-amber-700 dark:text-amber-300", accent: "border-amber-200 dark:border-amber-800", gradient: "from-amber-400 to-orange-500" },
  General: { bg: "bg-gray-50 dark:bg-gray-900/30", text: "text-gray-700 dark:text-gray-300", accent: "border-gray-200 dark:border-gray-700", gradient: "from-gray-500 to-slate-600" },
};

interface Message {
  id: string;
  role: "user" | "assistant" | "routing";
  content: string;
  agentId?: string;
  agentName?: string;
  agentDomain?: string;
  routing?: RoutingResponse;
  timestamp: Date;
}

// Component to render message content with clickable links
function FormattedMessage({ content, className }: { content: string; className?: string }) {
  // Parse markdown links [text](url) and bare URLs
  const parseContent = (text: string) => {
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;

    // Combined regex for markdown links and bare URLs
    const linkRegex = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|(https?:\/\/[^\s<>\])"]+)/g;
    let match;

    while ((match = linkRegex.exec(text)) !== null) {
      // Add text before the match
      if (match.index > lastIndex) {
        parts.push(text.slice(lastIndex, match.index));
      }

      if (match[1] && match[2]) {
        // Markdown link [text](url)
        parts.push(
          <a
            key={match.index}
            href={match[2]}
            target="_blank"
            rel="noopener noreferrer"
            className="text-purple-600 dark:text-purple-400 hover:text-purple-800 dark:hover:text-purple-300 underline decoration-purple-300 dark:decoration-purple-600 underline-offset-2 font-medium transition-colors"
          >
            {match[1]}
          </a>
        );
      } else if (match[3]) {
        // Bare URL
        parts.push(
          <a
            key={match.index}
            href={match[3]}
            target="_blank"
            rel="noopener noreferrer"
            className="text-purple-600 dark:text-purple-400 hover:text-purple-800 dark:hover:text-purple-300 underline decoration-purple-300 dark:decoration-purple-600 underline-offset-2 font-medium transition-colors break-all"
          >
            {match[3]}
          </a>
        );
      }

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push(text.slice(lastIndex));
    }

    return parts.length > 0 ? parts : text;
  };

  // Split by newlines and process each line
  const lines = content.split('\n');

  return (
    <div className={cn("whitespace-pre-wrap leading-relaxed", className)}>
      {lines.map((line, i) => (
        <span key={i}>
          {parseContent(line)}
          {i < lines.length - 1 && '\n'}
        </span>
      ))}
    </div>
  );
}

export default function ConciergePage() {
  const [agents, setAgents] = useState<AgentConfig[]>([]);
  const [concierge, setConcierge] = useState<AgentConfig | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [currentAgent, setCurrentAgent] = useState<AgentConfig | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [showWelcome, setShowWelcome] = useState(true);
  const [showAgentDirectory, setShowAgentDirectory] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);

  // Get department agents (non-router)
  const departmentAgents = agents.filter(a => !a.is_router && a.status === "active");

  // Load agents on mount
  useEffect(() => {
    loadAgents();
    initSpeechRecognition();
  }, []);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const loadAgents = async () => {
    try {
      const data = await listAgents();
      const activeAgents = data.agents.filter((a) => a.status === "active");
      setAgents(activeAgents);

      const router = activeAgents.find((a) => a.is_router);
      if (router) {
        setConcierge(router);
        setCurrentAgent(router);
      }
    } catch (error) {
      console.error("Failed to load agents:", error);
    }
  };

  const initSpeechRecognition = () => {
    if (typeof window !== "undefined" && "webkitSpeechRecognition" in window) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const SpeechRecognitionAPI = (window as any).webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognitionAPI();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognitionRef.current.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setInput((prev) => prev + transcript);
        setIsListening(false);
      };

      recognitionRef.current.onerror = () => setIsListening(false);
      recognitionRef.current.onend = () => setIsListening(false);
    }
  };

  const toggleListening = () => {
    if (!recognitionRef.current) return;
    if (isListening) {
      recognitionRef.current.stop();
    } else {
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
  };

  const sendMessage = useCallback(async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    setShowWelcome(false);

    try {
      // Create conversation if needed
      let convId = conversationId;
      if (!convId) {
        const conv = await createConversation("guest", "General");
        convId = conv.id;
        setConversationId(convId);
      }

      // Save user message
      await addMessage(convId, "user", userMessage.content);

      // Always use intelligent routing through concierge first
      const routing = await routeQuery(userMessage.content);
      const targetAgent = agents.find((a) => a.id === routing.primary_agent_id);

      // If routing to a different agent, show the handoff
      if (targetAgent && targetAgent.id !== concierge?.id && !targetAgent.is_router) {
        // Show routing message with agent introduction
        const routingMessage: Message = {
          id: `routing-${Date.now()}`,
          role: "routing",
          content: `I'll connect you with our ${targetAgent.domain} specialist who can best assist you.`,
          routing,
          agentId: targetAgent.id,
          agentName: targetAgent.name,
          agentDomain: targetAgent.domain,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, routingMessage]);
        setCurrentAgent(targetAgent);
      }

      // Query the target agent
      const response = await queryAgent(routing.primary_agent_id, userMessage.content, true);

      const assistantMessage: Message = {
        id: `msg-${Date.now()}-response`,
        role: "assistant",
        content: response.response,
        agentId: response.agent_id,
        agentName: response.agent_name,
        agentDomain: targetAgent?.domain || "General",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Save assistant message
      await addMessage(convId, "assistant", response.response, response.agent_id, response.agent_name);

    } catch (error) {
      console.error("Query error:", error);
      const errorMessage: Message = {
        id: `msg-${Date.now()}-error`,
        role: "assistant",
        content: "I apologize for the inconvenience. I'm having trouble connecting right now. Please try again in a moment, or contact our support team directly.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }, [input, isLoading, conversationId, agents, concierge]);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion);
    inputRef.current?.focus();
  };

  // Quick suggestions based on available agents
  const quickSuggestions = [
    { text: "Help me with an HR question", icon: Users, domain: "HR" },
    { text: "I need finance assistance", icon: Briefcase, domain: "Finance" },
    { text: "Building permit inquiry", icon: Building2, domain: "Building" },
    { text: "Public health resources", icon: Heart, domain: "PublicHealth" },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-stone-50 via-amber-50/30 to-orange-50/20 dark:from-black dark:via-neutral-950 dark:to-neutral-900 flex flex-col">
      {/* Elegant Header */}
      <header className="bg-white/80 dark:bg-neutral-900/80 backdrop-blur-md border-b border-stone-200/50 dark:border-neutral-800 sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Back to Menu Button */}
              <Link
                href="/"
                className="flex items-center justify-center w-10 h-10 rounded-xl bg-stone-100 dark:bg-neutral-800 hover:bg-stone-200 dark:hover:bg-neutral-700 transition-colors group"
              >
                <ArrowLeft className="w-5 h-5 text-stone-600 dark:text-neutral-400 group-hover:text-stone-800 dark:group-hover:text-neutral-200" />
              </Link>

              {/* Concierge Logo/Avatar */}
              <div className="relative">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-400 via-orange-400 to-rose-400 flex items-center justify-center shadow-lg shadow-orange-200/50 dark:shadow-orange-900/30">
                  <Sparkles className="w-7 h-7 text-white" />
                </div>
                <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-emerald-500 rounded-full border-2 border-white dark:border-neutral-900 flex items-center justify-center">
                  <span className="text-[8px] text-white font-bold">ON</span>
                </div>
              </div>

              <div>
                <h1 className="text-xl font-semibold text-stone-800 dark:text-white tracking-tight">
                  {config.appName} Concierge
                </h1>
                <p className="text-sm text-stone-500 dark:text-neutral-400 flex items-center gap-2">
                  <Star className="w-3 h-3 text-amber-500 fill-amber-500" />
                  Your personal guide to {config.organization}
                </p>
              </div>
            </div>

            {/* Status & Agents Directory */}
            <div className="flex items-center gap-3">
              <Badge className="bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800 hover:bg-emerald-100 dark:hover:bg-emerald-900/50">
                <Clock className="w-3 h-3 mr-1" />
                Available 24/7
              </Badge>

              {/* Agent Directory Button */}
              <Sheet open={showAgentDirectory} onOpenChange={setShowAgentDirectory}>
                <SheetTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="bg-gradient-to-r from-purple-50 to-violet-50 dark:from-purple-950/50 dark:to-violet-950/50 border-purple-200 dark:border-purple-800 hover:from-purple-100 hover:to-violet-100 dark:hover:from-purple-900/50 dark:hover:to-violet-900/50 text-purple-700 dark:text-purple-300"
                  >
                    <Grid3X3 className="w-4 h-4 mr-2" />
                    Agents
                    <Badge className="ml-2 bg-purple-500 text-white border-0 text-xs px-1.5">
                      {departmentAgents.length}
                    </Badge>
                  </Button>
                </SheetTrigger>
                <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
                  <SheetHeader className="text-left">
                    <SheetTitle className="flex items-center gap-2">
                      <div className="p-2 rounded-xl bg-gradient-to-br from-purple-500 to-violet-600">
                        <Bot className="w-5 h-5 text-white" />
                      </div>
                      Agent Directory
                    </SheetTitle>
                    <SheetDescription>
                      {departmentAgents.length} specialist agents available to assist you
                    </SheetDescription>
                  </SheetHeader>

                  <div className="mt-6 space-y-3">
                    {departmentAgents.map((agent, index) => {
                      const colors = domainColors[agent.domain] || domainColors.General;
                      const DomainIcon = domainIcons[agent.domain] || HelpCircle;

                      return (
                        <div
                          key={agent.id}
                          className={cn(
                            "p-4 rounded-xl border-2 transition-all hover:shadow-md animate-in fade-in",
                            colors.bg,
                            colors.accent
                          )}
                          style={{ animationDelay: `${index * 50}ms` }}
                        >
                          <div className="flex items-start gap-3">
                            <div className={cn(
                              "p-2.5 rounded-xl shadow-md",
                              `bg-gradient-to-br ${colors.gradient}`
                            )}>
                              <DomainIcon className="w-5 h-5 text-white" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className={cn("font-semibold", colors.text)}>
                                  {agent.name}
                                </span>
                                <Badge variant="secondary" className="text-xs">
                                  {agent.domain}
                                </Badge>
                              </div>
                              <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
                                {agent.description}
                              </p>
                              {agent.gpt_url && (
                                <a
                                  href={agent.gpt_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className={cn(
                                    "inline-flex items-center gap-1.5 text-sm font-medium transition-colors",
                                    "text-purple-600 dark:text-purple-400 hover:text-purple-800 dark:hover:text-purple-300"
                                  )}
                                >
                                  <Sparkles className="w-3.5 h-3.5" />
                                  Open Custom GPT
                                  <ExternalLink className="w-3 h-3" />
                                </a>
                              )}
                              {!agent.gpt_url && agent.capabilities && agent.capabilities.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {agent.capabilities.slice(0, 3).map((cap) => (
                                    <Badge key={cap} variant="outline" className="text-xs">
                                      {cap}
                                    </Badge>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}

                    {departmentAgents.length === 0 && (
                      <div className="text-center py-12">
                        <div className="inline-flex p-4 rounded-full bg-muted mb-4">
                          <Bot className="w-8 h-8 text-muted-foreground" />
                        </div>
                        <p className="font-medium">No agents available</p>
                        <p className="text-sm text-muted-foreground">
                          Agents will appear here once configured
                        </p>
                      </div>
                    )}
                  </div>
                </SheetContent>
              </Sheet>
            </div>
          </div>
        </div>
      </header>

      {/* Main Chat Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-6 py-6 flex flex-col">
        <ScrollArea className="flex-1" ref={scrollRef}>
          {/* Welcome State */}
          {showWelcome && messages.length === 0 && (
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center animate-in fade-in duration-700">
              {/* Elegant Welcome Card */}
              <div className="relative mb-8">
                <div className="absolute inset-0 bg-gradient-to-r from-amber-200 via-orange-200 to-rose-200 dark:from-amber-900/40 dark:via-orange-900/40 dark:to-rose-900/40 rounded-full blur-3xl opacity-40"></div>
                <div className="relative w-28 h-28 rounded-full bg-gradient-to-br from-amber-400 via-orange-400 to-rose-400 flex items-center justify-center shadow-2xl shadow-orange-300/30 dark:shadow-orange-900/30">
                  <Sparkles className="w-14 h-14 text-white" />
                </div>
              </div>

              <h2 className="text-3xl font-semibold text-stone-800 dark:text-white mb-3 tracking-tight">
                {getGreeting()}
              </h2>
              <p className="text-lg text-stone-600 dark:text-neutral-300 mb-2 max-w-md">
                Welcome to the {config.organization} Concierge
              </p>
              <p className="text-stone-500 dark:text-neutral-400 mb-8 max-w-lg leading-relaxed">
                I'm here to guide you to the right resources and specialists.
                Whether you have questions about HR, finance, permits, or any city service,
                I'll connect you with the perfect expert.
              </p>

              {/* Service Highlights */}
              <div className="flex flex-wrap justify-center gap-3 mb-10">
                <Badge variant="outline" className="py-2 px-4 bg-white/80 dark:bg-neutral-800/80 border-stone-200 dark:border-neutral-700">
                  <Shield className="w-4 h-4 mr-2 text-emerald-600 dark:text-emerald-400" />
                  Secure & Confidential
                </Badge>
                <Badge variant="outline" className="py-2 px-4 bg-white/80 dark:bg-neutral-800/80 border-stone-200 dark:border-neutral-700">
                  <Zap className="w-4 h-4 mr-2 text-amber-600 dark:text-amber-400" />
                  Instant Routing
                </Badge>
                <Badge variant="outline" className="py-2 px-4 bg-white/80 dark:bg-neutral-800/80 border-stone-200 dark:border-neutral-700">
                  <Users className="w-4 h-4 mr-2 text-blue-600 dark:text-blue-400" />
                  {agents.filter(a => !a.is_router).length} Specialists Available
                </Badge>
              </div>

              {/* Quick Start Suggestions */}
              <div className="w-full max-w-2xl">
                <p className="text-sm text-stone-500 dark:text-neutral-400 mb-4 font-medium">How can I assist you today?</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {quickSuggestions.map((suggestion, i) => {
                    const colors = domainColors[suggestion.domain] || domainColors.General;
                    const Icon = suggestion.icon;
                    return (
                      <button
                        key={i}
                        onClick={() => handleSuggestionClick(suggestion.text)}
                        className={cn(
                          "group flex items-center gap-4 p-4 rounded-xl border-2 text-left transition-all duration-300",
                          "bg-white/80 dark:bg-neutral-800/60 hover:bg-white dark:hover:bg-neutral-800 hover:shadow-lg hover:shadow-stone-200/50 dark:hover:shadow-black/50",
                          "border-stone-200 dark:border-neutral-700 hover:border-stone-300 dark:hover:border-neutral-600",
                          "hover:scale-[1.02] active:scale-[0.98]"
                        )}
                      >
                        <div className={cn(
                          "w-12 h-12 rounded-xl flex items-center justify-center transition-transform group-hover:scale-110",
                          `bg-gradient-to-br ${colors.gradient}`
                        )}>
                          <Icon className="w-6 h-6 text-white" />
                        </div>
                        <div className="flex-1">
                          <p className="font-medium text-stone-700 dark:text-neutral-200 group-hover:text-stone-900 dark:group-hover:text-white">
                            {suggestion.text}
                          </p>
                        </div>
                        <ChevronRight className="w-5 h-5 text-stone-400 dark:text-neutral-500 group-hover:text-stone-600 dark:group-hover:text-neutral-300 group-hover:translate-x-1 transition-all" />
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Messages */}
          {messages.length > 0 && (
            <div className="space-y-6 pb-4">
              {messages.map((message, index) => {
                const colors = domainColors[message.agentDomain || "General"] || domainColors.General;
                const DomainIcon = domainIcons[message.agentDomain || "General"] || HelpCircle;

                // Routing/Handoff Message - Premium Agent Introduction
                if (message.role === "routing") {
                  const routedAgent = agents.find(a => a.id === message.agentId);
                  const agentColors = domainColors[routedAgent?.domain || "General"] || domainColors.General;
                  const AgentIcon = domainIcons[routedAgent?.domain || "General"] || HelpCircle;

                  return (
                    <div
                      key={message.id}
                      className="flex justify-center animate-in fade-in slide-in-from-bottom-4 duration-700"
                      style={{ animationDelay: `${index * 100}ms` }}
                    >
                      <Card className="w-full max-w-lg bg-gradient-to-br from-white via-amber-50/30 to-orange-50/30 dark:from-neutral-900 dark:via-neutral-900 dark:to-neutral-800 border-amber-200/60 dark:border-neutral-700 shadow-xl shadow-amber-100/30 dark:shadow-black/30 overflow-hidden">
                        {/* Header Banner */}
                        <div className={cn(
                          "h-2 w-full bg-gradient-to-r",
                          agentColors.gradient
                        )} />

                        <CardContent className="p-6">
                          {/* Concierge Introduction */}
                          <div className="flex items-center gap-3 mb-5">
                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-md">
                              <Sparkles className="w-5 h-5 text-white" />
                            </div>
                            <div>
                              <p className="text-sm font-medium text-stone-700 dark:text-neutral-200">
                                I've found the perfect specialist for you
                              </p>
                              <p className="text-xs text-stone-500 dark:text-neutral-400">
                                Let me introduce you...
                              </p>
                            </div>
                          </div>

                          {/* Agent Profile Card */}
                          {routedAgent && (
                            <div className={cn(
                              "rounded-xl border-2 p-5 transition-all",
                              agentColors.bg, agentColors.accent
                            )}>
                              <div className="flex items-start gap-4">
                                {/* Agent Avatar */}
                                <div className={cn(
                                  "w-16 h-16 rounded-xl flex items-center justify-center shadow-lg",
                                  `bg-gradient-to-br ${agentColors.gradient}`
                                )}>
                                  <AgentIcon className="w-8 h-8 text-white" />
                                </div>

                                <div className="flex-1 min-w-0">
                                  {/* Agent Name & Title */}
                                  <h3 className={cn("font-bold text-lg", agentColors.text)}>
                                    {routedAgent.name}
                                  </h3>
                                  <p className="text-sm text-stone-600 dark:text-neutral-400 mb-2">
                                    {routedAgent.title}
                                  </p>

                                  {/* Domain Badge */}
                                  <Badge className={cn(
                                    "mb-3",
                                    agentColors.bg, agentColors.text, "border", agentColors.accent
                                  )}>
                                    {routedAgent.domain} Specialist
                                  </Badge>

                                  {/* Description */}
                                  <p className="text-sm text-stone-600 dark:text-neutral-400 leading-relaxed mb-4">
                                    {routedAgent.description}
                                  </p>

                                  {/* Capabilities */}
                                  {routedAgent.capabilities.length > 0 && (
                                    <div>
                                      <p className="text-xs font-semibold text-stone-500 dark:text-neutral-500 uppercase tracking-wide mb-2">
                                        Can help you with
                                      </p>
                                      <div className="flex flex-wrap gap-2">
                                        {routedAgent.capabilities.slice(0, 4).map((cap, i) => (
                                          <Badge
                                            key={i}
                                            variant="outline"
                                            className="bg-white/80 dark:bg-neutral-800/80 text-stone-600 dark:text-neutral-300 border-stone-200 dark:border-neutral-700 text-xs"
                                          >
                                            {cap}
                                          </Badge>
                                        ))}
                                        {routedAgent.capabilities.length > 4 && (
                                          <Badge
                                            variant="outline"
                                            className="bg-white/80 dark:bg-neutral-800/80 text-stone-500 dark:text-neutral-400 border-stone-200 dark:border-neutral-700 text-xs"
                                          >
                                            +{routedAgent.capabilities.length - 4} more
                                          </Badge>
                                        )}
                                      </div>
                                    </div>
                                  )}

                                  {/* External Link if available */}
                                  {routedAgent.gpt_url && (
                                    <div className="mt-4 pt-4 border-t border-stone-200 dark:border-neutral-700">
                                      <a
                                        href={routedAgent.gpt_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className={cn(
                                          "inline-flex items-center gap-2 text-sm font-medium transition-colors",
                                          agentColors.text, "hover:underline"
                                        )}
                                      >
                                        <FileText className="w-4 h-4" />
                                        Access full assistant profile
                                        <ChevronRight className="w-4 h-4" />
                                      </a>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Confidence & Status */}
                          <div className="flex items-center justify-between mt-4 pt-4 border-t border-amber-200/50 dark:border-neutral-700">
                            {message.routing && (
                              <div className="flex items-center gap-2 text-sm text-amber-700 dark:text-amber-400">
                                <div className="flex">
                                  {[...Array(5)].map((_, i) => (
                                    <Star
                                      key={i}
                                      className={cn(
                                        "w-4 h-4",
                                        i < Math.round(message.routing!.confidence * 5)
                                          ? "fill-amber-400 text-amber-400"
                                          : "fill-stone-200 dark:fill-neutral-700 text-stone-200 dark:text-neutral-700"
                                      )}
                                    />
                                  ))}
                                </div>
                                <span className="font-medium">
                                  {Math.round(message.routing.confidence * 100)}% match
                                </span>
                              </div>
                            )}
                            <Badge className="bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800">
                              <div className="w-2 h-2 bg-emerald-500 rounded-full mr-2 animate-pulse" />
                              Connected
                            </Badge>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  );
                }

                // User Message
                if (message.role === "user") {
                  return (
                    <div
                      key={message.id}
                      className="flex gap-4 justify-end animate-in fade-in slide-in-from-right-4 duration-300"
                      style={{ animationDelay: `${index * 100}ms` }}
                    >
                      <div className="max-w-[75%]">
                        <Card className="bg-gradient-to-br from-stone-800 to-stone-900 dark:from-neutral-700 dark:to-neutral-800 text-white border-0 shadow-xl shadow-stone-300/30 dark:shadow-black/30">
                          <CardContent className="p-4">
                            <FormattedMessage content={message.content} className="text-white" />
                          </CardContent>
                        </Card>
                        <p className="text-xs text-stone-400 dark:text-neutral-500 mt-2 text-right pr-2">
                          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                      <div className="w-10 h-10 rounded-full bg-stone-200 dark:bg-neutral-700 flex items-center justify-center flex-shrink-0">
                        <User className="w-5 h-5 text-stone-600 dark:text-neutral-300" />
                      </div>
                    </div>
                  );
                }

                // Assistant Message
                return (
                  <div
                    key={message.id}
                    className="flex gap-4 animate-in fade-in slide-in-from-left-4 duration-300"
                    style={{ animationDelay: `${index * 100}ms` }}
                  >
                    <div className={cn(
                      "w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 shadow-lg",
                      `bg-gradient-to-br ${colors.gradient}`
                    )}>
                      <DomainIcon className="w-5 h-5 text-white" />
                    </div>
                    <div className="max-w-[75%]">
                      {message.agentName && (
                        <div className="flex items-center gap-2 mb-2">
                          <span className={cn("text-sm font-semibold", colors.text)}>
                            {message.agentName}
                          </span>
                          <Badge className={cn("text-xs", colors.bg, colors.text, "border-0")}>
                            {message.agentDomain}
                          </Badge>
                        </div>
                      )}
                      <Card className="bg-white dark:bg-neutral-800 border-stone-200 dark:border-neutral-700 shadow-lg shadow-stone-100/50 dark:shadow-black/30">
                        <CardContent className="p-4">
                          <FormattedMessage content={message.content} className="text-stone-700 dark:text-neutral-200" />
                        </CardContent>
                      </Card>
                      <p className="text-xs text-stone-400 dark:text-neutral-500 mt-2 pl-2">
                        {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </div>
                );
              })}

              {/* Loading State */}
              {isLoading && (
                <div className="flex gap-4 animate-in fade-in duration-300">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center flex-shrink-0 shadow-lg">
                    <Sparkles className="w-5 h-5 text-white" />
                  </div>
                  <Card className="bg-white dark:bg-neutral-800 border-stone-200 dark:border-neutral-700 shadow-lg dark:shadow-black/30">
                    <CardContent className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="flex gap-1">
                          <span className="w-2 h-2 bg-amber-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                          <span className="w-2 h-2 bg-orange-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                          <span className="w-2 h-2 bg-rose-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                        </div>
                        <span className="text-stone-500 dark:text-neutral-400 text-sm">Finding the best way to help you...</span>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}
            </div>
          )}
        </ScrollArea>

        {/* Elegant Input Area */}
        <div className="mt-6 pt-4 border-t border-stone-200/50 dark:border-neutral-800">
          <div className="relative">
            <div className="flex items-end gap-3 bg-white dark:bg-neutral-800 rounded-2xl border-2 border-stone-200 dark:border-neutral-700 focus-within:border-amber-400 dark:focus-within:border-amber-500 focus-within:shadow-lg focus-within:shadow-amber-100/50 dark:focus-within:shadow-amber-900/20 transition-all duration-300 p-2">
              {/* Voice Input */}
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleListening}
                disabled={!recognitionRef.current}
                className={cn(
                  "h-10 w-10 rounded-xl transition-all",
                  isListening
                    ? "bg-red-100 dark:bg-red-950 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900"
                    : "hover:bg-stone-100 dark:hover:bg-neutral-700 text-stone-400 dark:text-neutral-500"
                )}
              >
                {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              </Button>

              {/* Text Input */}
              <Textarea
                ref={inputRef}
                placeholder="How can I help you today?"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyPress}
                disabled={isLoading}
                className="flex-1 min-h-[44px] max-h-32 resize-none border-0 focus-visible:ring-0 bg-transparent text-stone-700 dark:text-neutral-200 placeholder:text-stone-400 dark:placeholder:text-neutral-500"
                rows={1}
              />

              {/* Send Button */}
              <Button
                onClick={sendMessage}
                disabled={!input.trim() || isLoading}
                className={cn(
                  "h-11 w-11 rounded-xl transition-all duration-300",
                  input.trim()
                    ? "bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 shadow-lg shadow-amber-200/50 dark:shadow-amber-900/30"
                    : "bg-stone-100 dark:bg-neutral-700 text-stone-400 dark:text-neutral-500"
                )}
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </Button>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between mt-4 px-2">
            <p className="text-xs text-stone-400 dark:text-neutral-500">
              Powered by {config.appName}
            </p>
            <div className="flex items-center gap-4 text-xs text-stone-400 dark:text-neutral-500">
              <span className="flex items-center gap-1">
                <Shield className="w-3 h-3" />
                Secure
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                24/7 Available
              </span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
