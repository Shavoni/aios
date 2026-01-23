"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Send,
  Mic,
  MicOff,
  Bot,
  User,
  FileText,
  ChevronDown,
  ChevronUp,
  Loader2,
  Building2,
  Sparkles,
} from "lucide-react";
import { listAgents, queryAgent, AgentConfig, AgentQueryResponse } from "@/lib/api";
import { config } from "@/lib/config";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  agentId?: string;
  agentName?: string;
  sources?: Array<{
    text: string;
    metadata: Record<string, unknown>;
    relevance: number;
  }>;
  timestamp: Date;
}

export default function ChatPage() {
  const [agents, setAgents] = useState<AgentConfig[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  // Load agents on mount
  useEffect(() => {
    loadAgents();
  }, []);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Initialize speech recognition
  useEffect(() => {
    if (typeof window !== "undefined" && "webkitSpeechRecognition" in window) {
      const SpeechRecognition = window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInput((prev) => prev + transcript);
        setIsListening(false);
      };

      recognitionRef.current.onerror = () => {
        setIsListening(false);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }
  }, []);

  const loadAgents = async () => {
    try {
      const data = await listAgents();
      // Filter to only active agents
      const activeAgents = data.agents.filter((a) => a.status === "active");
      setAgents(activeAgents);

      // Auto-select the router/concierge if available
      const router = activeAgents.find((a) => a.is_router);
      if (router) {
        setSelectedAgentId(router.id);
      } else if (activeAgents.length > 0) {
        setSelectedAgentId(activeAgents[0].id);
      }
    } catch (error) {
      console.error("Failed to load agents:", error);
    }
  };

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert("Speech recognition not supported in this browser.");
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  const toggleSources = (messageId: string) => {
    setExpandedSources((prev) => {
      const next = new Set(prev);
      if (next.has(messageId)) {
        next.delete(messageId);
      } else {
        next.add(messageId);
      }
      return next;
    });
  };

  const sendMessage = async () => {
    if (!input.trim() || !selectedAgentId || isLoading) return;

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response: AgentQueryResponse = await queryAgent(
        selectedAgentId,
        userMessage.content,
        true
      );

      const assistantMessage: Message = {
        id: `msg-${Date.now()}-response`,
        role: "assistant",
        content: response.response,
        agentId: response.agent_id,
        agentName: response.agent_name,
        sources: response.sources,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: `msg-${Date.now()}-error`,
        role: "assistant",
        content: `I apologize, but I encountered an error processing your request. Please try again or contact support if the issue persists.`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      console.error("Query error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const selectedAgent = agents.find((a) => a.id === selectedAgentId);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-slate-900">
                  {config.appName}
                </h1>
                <p className="text-sm text-slate-500">
                  {config.tagline} • {config.organization}
                </p>
              </div>
            </div>

            {/* Agent Selector */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-500 hidden sm:inline">Speaking with:</span>
              <Select value={selectedAgentId} onValueChange={setSelectedAgentId}>
                <SelectTrigger className="w-[200px] sm:w-[240px]">
                  <SelectValue placeholder="Select an assistant" />
                </SelectTrigger>
                <SelectContent>
                  {agents.map((agent) => (
                    <SelectItem key={agent.id} value={agent.id}>
                      <div className="flex items-center gap-2">
                        {agent.is_router && (
                          <Badge variant="secondary" className="text-xs">
                            Router
                          </Badge>
                        )}
                        <span>{agent.name}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Selected Agent Info */}
          {selectedAgent && (
            <div className="mt-3 p-3 bg-gradient-to-r from-slate-50 to-blue-50 rounded-lg border border-slate-100">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-900">{selectedAgent.title || selectedAgent.name}</p>
                  <p className="text-sm text-slate-600 line-clamp-2">{selectedAgent.description}</p>
                  {selectedAgent.capabilities.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {selectedAgent.capabilities.slice(0, 3).map((cap, i) => (
                        <Badge key={i} variant="outline" className="text-xs bg-white">
                          {cap}
                        </Badge>
                      ))}
                      {selectedAgent.capabilities.length > 3 && (
                        <Badge variant="outline" className="text-xs bg-white">
                          +{selectedAgent.capabilities.length - 3} more
                        </Badge>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Chat Area */}
      <div className="flex-1 max-w-4xl w-full mx-auto px-4 py-6 flex flex-col">
        <ScrollArea className="flex-1 pr-4" ref={scrollRef}>
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-20">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center mb-6 shadow-lg">
                <Sparkles className="w-10 h-10 text-white" />
              </div>
              <h2 className="text-2xl font-semibold text-slate-900 mb-2">
                Welcome to {config.appName}
              </h2>
              <p className="text-slate-600 max-w-md mb-2">
                Your intelligent assistant for {config.organization}.
                Ask questions about policies, procedures, and more.
              </p>
              <p className="text-sm text-slate-400 mb-6">
                Select an assistant above or use our AI Concierge for automatic routing.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
                {[
                  "What services are available?",
                  "How do I submit a request?",
                  "Help me find information",
                  "Speak with a specialist",
                ].map((suggestion, i) => (
                  <Button
                    key={i}
                    variant="outline"
                    className="text-left justify-start h-auto py-3 px-4 bg-white hover:bg-slate-50"
                    onClick={() => setInput(suggestion)}
                  >
                    <Sparkles className="w-4 h-4 mr-2 text-blue-500 flex-shrink-0" />
                    {suggestion}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-4 pb-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-3 ${
                    message.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  {message.role === "assistant" && (
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0">
                      <Bot className="w-4 h-4 text-white" />
                    </div>
                  )}

                  <div
                    className={`max-w-[80%] ${
                      message.role === "user" ? "order-1" : ""
                    }`}
                  >
                    <Card
                      className={`${
                        message.role === "user"
                          ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white border-0 shadow-md"
                          : "bg-white shadow-sm"
                      }`}
                    >
                      <CardContent className="p-3">
                        {message.role === "assistant" && message.agentName && (
                          <p className="text-xs text-blue-600 font-medium mb-1">
                            {message.agentName}
                          </p>
                        )}
                        <p className="whitespace-pre-wrap">{message.content}</p>
                      </CardContent>
                    </Card>

                    {/* Sources */}
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-xs text-slate-500 h-auto p-1 hover:text-blue-600"
                          onClick={() => toggleSources(message.id)}
                        >
                          <FileText className="w-3 h-3 mr-1" />
                          {message.sources.length} source(s) referenced
                          {expandedSources.has(message.id) ? (
                            <ChevronUp className="w-3 h-3 ml-1" />
                          ) : (
                            <ChevronDown className="w-3 h-3 ml-1" />
                          )}
                        </Button>

                        {expandedSources.has(message.id) && (
                          <div className="mt-2 space-y-2">
                            {message.sources.map((source, i) => (
                              <Card key={i} className="bg-slate-50 border-slate-200">
                                <CardContent className="p-2">
                                  <p className="text-xs font-medium text-slate-700 mb-1 flex items-center justify-between">
                                    <span className="flex items-center gap-1">
                                      <FileText className="w-3 h-3" />
                                      {(source.metadata.filename as string) || "Knowledge Base"}
                                    </span>
                                    <Badge variant="secondary" className="text-xs">
                                      {Math.round(source.relevance * 100)}% match
                                    </Badge>
                                  </p>
                                  <p className="text-xs text-slate-600 line-clamp-3">
                                    {source.text}
                                  </p>
                                </CardContent>
                              </Card>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    <p className="text-xs text-slate-400 mt-1 px-1">
                      {message.timestamp.toLocaleTimeString()}
                    </p>
                  </div>

                  {message.role === "user" && (
                    <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0">
                      <User className="w-4 h-4 text-slate-600" />
                    </div>
                  )}
                </div>
              ))}

              {isLoading && (
                <div className="flex gap-3 justify-start">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <Card className="bg-white shadow-sm">
                    <CardContent className="p-3">
                      <div className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                        <span className="text-slate-500">Thinking...</span>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}
            </div>
          )}
        </ScrollArea>

        {/* Input Area */}
        <div className="mt-4 pt-4 border-t">
          <div className="flex gap-2">
            <Button
              variant={isListening ? "destructive" : "outline"}
              size="icon"
              onClick={toggleListening}
              className="flex-shrink-0"
              title={isListening ? "Stop listening" : "Start voice input"}
            >
              {isListening ? (
                <MicOff className="w-4 h-4" />
              ) : (
                <Mic className="w-4 h-4" />
              )}
            </Button>

            <Input
              placeholder="Type your question here..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading || !selectedAgentId}
              className="flex-1"
            />

            <Button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading || !selectedAgentId}
              className="flex-shrink-0 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
          </div>

          <p className="text-xs text-center text-slate-400 mt-3">
            {config.footerText}
          </p>
        </div>
      </div>
    </div>
  );
}
