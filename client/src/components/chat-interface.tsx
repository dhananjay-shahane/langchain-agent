import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Paperclip, Send, Download, ChartLine, User, Bot, Clock, CheckCircle, Brain, Cog, ArrowRight, CheckSquare } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";

interface ChatMessage {
  id: string;
  role: "user" | "agent" | "system";
  content: string;
  metadata?: any;
  timestamp: string;
}

interface LasFile {
  id: string;
  filename: string;
  filepath: string;
  size: string;
  source: string;
  processed: boolean;
  createdAt: string;
}

export default function ChatInterface() {
  const [message, setMessage] = useState("");
  const [selectedLasFile, setSelectedLasFile] = useState("none");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: messages = [], isLoading: loadingMessages } = useQuery<ChatMessage[]>({
    queryKey: ["/api/chat/messages"],
  });

  const { data: lasFiles = [] } = useQuery<LasFile[]>({
    queryKey: ["/api/files/las"],
  });

  const sendMessageMutation = useMutation({
    mutationFn: async (messageData: { role: string; content: string; metadata?: any }) => {
      const response = await apiRequest("POST", "/api/chat/message", messageData);
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/chat/messages"] });
      setMessage("");
      setSelectedLasFile("none");
    },
    onError: () => {
      toast({
        title: "Error",
        description: "Failed to send message.",
        variant: "destructive",
      });
    },
  });

  const handleSendMessage = async () => {
    if (!message.trim()) return;

    await sendMessageMutation.mutateAsync({
      role: "user",
      content: message,
      metadata: selectedLasFile !== "none" ? { selectedLasFile } : undefined,
    });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleQuickAction = (actionText: string) => {
    setMessage(actionText);
  };

  const handleDownloadFile = async (filename: string) => {
    try {
      const response = await fetch(`/api/files/output/${filename}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to download file.",
        variant: "destructive",
      });
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const renderMessage = (msg: ChatMessage) => {
    const isUser = msg.role === "user";
    const isSystem = msg.role === "system";

    if (isSystem) {
      return (
        <div key={msg.id} className="flex justify-center my-4">
          <div className="bg-accent/10 border border-accent/20 rounded-lg p-3 max-w-2xl">
            <div className="flex items-center gap-2 text-sm text-foreground">
              <CheckCircle className="w-4 h-4 text-accent" />
              {msg.content}
            </div>
          </div>
        </div>
      );
    }

    return (
      <div key={msg.id} className={`flex items-start gap-3 ${isUser ? "justify-end" : ""} mb-4`}>
        {!isUser && (
          <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center">
            <Bot className="w-4 h-4 text-primary-foreground" />
          </div>
        )}
        
        <div className={`flex-1 max-w-2xl ${isUser ? "order-first" : ""}`}>
          <div className={`p-4 rounded-lg ${isUser ? "bg-primary text-primary-foreground" : "bg-muted"}`}>
            {/* Show selected LAS file for user messages */}
            {isUser && msg.metadata?.selectedLasFile && (
              <div className="mb-2 text-xs opacity-75 flex items-center gap-1">
                <span>📁</span>
                <span>LAS file: {msg.metadata.selectedLasFile}</span>
              </div>
            )}
            <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            
            {/* Agent Thinking Steps */}
            {!isUser && msg.metadata?.thinking_steps && msg.metadata.thinking_steps.length > 0 && (
              <div className="mt-4 space-y-2">
                <div className="flex items-center gap-2 mb-3">
                  <Brain className="w-4 h-4 text-blue-500" />
                  <span className="text-sm font-medium text-foreground">Agent Thinking Process</span>
                </div>
                {msg.metadata.thinking_steps.map((step: any, index: number) => (
                  <div key={index} className="border-l-2 border-l-blue-200 dark:border-l-blue-700 pl-4 py-2">
                    {step.type === "thought" && (
                      <div className="bg-blue-50 dark:bg-blue-950/30 p-3 rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <Brain className="w-3 h-3 text-blue-600 dark:text-blue-400" />
                          <span className="text-xs font-medium text-blue-700 dark:text-blue-300 uppercase tracking-wide">Thought</span>
                        </div>
                        <p className="text-xs text-blue-800 dark:text-blue-200">{step.content}</p>
                      </div>
                    )}
                    {step.type === "action" && (
                      <div className="bg-green-50 dark:bg-green-950/30 p-3 rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <Cog className="w-3 h-3 text-green-600 dark:text-green-400" />
                          <span className="text-xs font-medium text-green-700 dark:text-green-300 uppercase tracking-wide">Action</span>
                        </div>
                        <div className="space-y-1">
                          <p className="text-xs text-green-800 dark:text-green-200">
                            <span className="font-medium">Tool:</span> {step.tool_name}
                          </p>
                          {step.tool_input && Object.keys(step.tool_input).length > 0 && (
                            <div className="text-xs text-green-700 dark:text-green-300">
                              <span className="font-medium">Input:</span>
                              <pre className="mt-1 bg-green-100 dark:bg-green-900/50 p-2 rounded text-xs overflow-x-auto">
                                {JSON.stringify(step.tool_input, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                    {step.type === "action_result" && (
                      <div className="bg-purple-50 dark:bg-purple-950/30 p-3 rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <CheckSquare className="w-3 h-3 text-purple-600 dark:text-purple-400" />
                          <span className="text-xs font-medium text-purple-700 dark:text-purple-300 uppercase tracking-wide">Result</span>
                        </div>
                        <div className="text-xs text-purple-800 dark:text-purple-200">
                          <span className="font-medium">From {step.tool_name}:</span>
                          <div className="mt-1 bg-purple-100 dark:bg-purple-900/50 p-2 rounded max-h-32 overflow-y-auto">
                            <pre className="text-xs whitespace-pre-wrap">{step.content}</pre>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {/* Tool Usage Indicator */}
            {msg.metadata?.tool_usage && (
              <div className="mt-3 p-3 bg-card border border-border rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <ChartLine className="w-4 h-4 text-accent" />
                  <span className="text-sm font-medium text-foreground">MCP Tool Used</span>
                </div>
                <div className="text-xs text-muted-foreground">
                  {msg.metadata.selected_file && (
                    <div>📂 Processing: {msg.metadata.selected_file}</div>
                  )}
                  <div className="flex items-center gap-2 mt-1">
                    <Clock className="w-3 h-3" />
                    <span>Completed at {formatTimestamp(msg.metadata.processing_time || msg.timestamp)}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Generated File Display */}
            {msg.metadata?.generated_file && (
              <div className="mt-3 p-3 bg-card border border-border rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ChartLine className="w-4 h-4 text-accent" />
                    <span className="text-sm font-medium text-foreground">
                      Generated: {msg.metadata.generated_file}
                    </span>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleDownloadFile(msg.metadata.generated_file)}
                    data-testid={`button-download-${msg.metadata.generated_file}`}
                  >
                    <Download className="w-3 h-3 mr-1" />
                    Download
                  </Button>
                </div>
              </div>
            )}
          </div>
          
          <span className="text-xs text-muted-foreground mt-1 block">
            {isUser ? "User" : "Agent"} • {formatTimestamp(msg.timestamp)}
          </span>
        </div>

        {isUser && (
          <div className="w-8 h-8 bg-secondary rounded-full flex items-center justify-center">
            <User className="w-4 h-4 text-secondary-foreground" />
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      {/* Chat Header */}
      <div className="bg-card border-b border-border p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Agent Chat Interface</h2>
            <p className="text-sm text-muted-foreground">
              Interact with the LangChain agent for LAS file processing
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Real-time monitoring:</span>
            <div className="w-2 h-2 bg-accent rounded-full animate-pulse"></div>
            <span className="text-sm text-accent">Active</span>
          </div>
        </div>
      </div>

      {/* Chat Messages */}
      <ScrollArea className="flex-1 p-6">
        <div className="space-y-4">
          {loadingMessages ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="animate-pulse flex items-start gap-3">
                  <div className="w-8 h-8 bg-muted rounded-full"></div>
                  <div className="flex-1">
                    <div className="h-4 bg-muted rounded w-3/4 mb-2"></div>
                    <div className="h-4 bg-muted rounded w-1/2"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : messages.length === 0 ? (
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center">
                <Bot className="w-4 h-4 text-primary-foreground" />
              </div>
              <div className="flex-1">
                <div className="bg-muted p-4 rounded-lg">
                  <p className="text-sm text-foreground">
                    LangChain MCP Agent initialized successfully. I'm ready to help you analyze LAS files and generate plots. You can ask me to:
                  </p>
                  <ul className="list-disc list-inside text-sm text-muted-foreground mt-2 space-y-1">
                    <li>Analyze well log data from LAS files</li>
                    <li>Generate formation plots and charts</li>
                    <li>Process seismic data visualizations</li>
                    <li>Create custom plots using available scripts</li>
                  </ul>
                </div>
                <span className="text-xs text-muted-foreground mt-1 block">Agent • just now</span>
              </div>
            </div>
          ) : (
            messages.map(renderMessage)
          )}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Chat Input */}
      <div className="bg-card border-t border-border p-4">
        <div className="flex gap-4 mb-3">
          {/* LAS File Selector */}
          <div className="w-48">
            <Select value={selectedLasFile} onValueChange={setSelectedLasFile} data-testid="select-las-file">
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select LAS file (optional)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No file selected</SelectItem>
                {lasFiles.map((file) => (
                  <SelectItem key={file.id} value={file.filename}>
                    {file.filename}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Message Input */}
          <div className="flex-1 relative">
            <Input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask the agent to analyze LAS files, create plots, or process data..."
              className="pr-12"
              disabled={sendMessageMutation.isPending}
              data-testid="input-message"
            />
            <Button
              size="sm"
              variant="ghost"
              className="absolute right-2 top-1/2 transform -translate-y-1/2 p-2"
              onClick={handleSendMessage}
              disabled={!message.trim() || sendMessageMutation.isPending}
              data-testid="button-send-message"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>

          {/* Additional Actions */}
          <Button variant="outline" size="sm" className="px-4" data-testid="button-attach-file">
            <Paperclip className="w-4 h-4" />
          </Button>
        </div>

        {/* Quick Actions */}
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            className="text-xs"
            onClick={() => handleQuickAction("Generate formation plot")}
            data-testid="quick-action-formation-plot"
          >
            Generate formation plot
          </Button>
          <Button
            variant="secondary"
            size="sm"
            className="text-xs"
            onClick={() => handleQuickAction("Analyze all LAS files")}
            data-testid="quick-action-analyze-all"
          >
            Analyze all LAS files
          </Button>
          <Button
            variant="secondary"
            size="sm"
            className="text-xs"
            onClick={() => handleQuickAction("Create summary report")}
            data-testid="quick-action-summary-report"
          >
            Create summary report
          </Button>
        </div>
      </div>
    </>
  );
}
