import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Send, Bot, User, FileText, MessageSquare, Plus } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import PdfUpload from "@/components/pdf-upload";

interface PdfDocument {
  id: string;
  filename: string;
  originalName: string;
  size: string;
  pageCount: string | null;
  processed: boolean;
  uploadedAt: string;
}

interface ChatSession {
  id: string;
  documentId: string;
  sessionName: string;
  createdAt: string;
}

interface ChatMessage {
  id: string;
  sessionId: string;
  role: "user" | "assistant";
  content: string;
  relevantChunks: string[];
  timestamp: string;
}

export default function PdfChat() {
  const [selectedDocument, setSelectedDocument] = useState<PdfDocument | null>(null);
  const [selectedSession, setSelectedSession] = useState<ChatSession | null>(null);
  const [messageInput, setMessageInput] = useState("");
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch chat sessions for selected document
  const { data: sessions = [], isLoading: loadingSessions } = useQuery<ChatSession[]>({
    queryKey: ["/api/pdfs", selectedDocument?.id, "sessions"],
    enabled: !!selectedDocument,
  });

  // Fetch messages for selected session
  const { data: messages = [], isLoading: loadingMessages } = useQuery<ChatMessage[]>({
    queryKey: ["/api/pdfs/sessions", selectedSession?.id, "messages"],
    enabled: !!selectedSession,
  });

  // Create new chat session
  const createSessionMutation = useMutation({
    mutationFn: async (sessionName: string) => {
      if (!selectedDocument) throw new Error("No document selected");
      
      const response = await apiRequest("POST", `/api/pdfs/${selectedDocument.id}/sessions`, { sessionName });
      return await response.json();
    },
    onSuccess: (newSession) => {
      queryClient.invalidateQueries({ queryKey: ["/api/pdfs", selectedDocument?.id, "sessions"] });
      setSelectedSession(newSession);
      toast({
        title: "Chat Session Created",
        description: "New chat session started successfully.",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.message || "Failed to create chat session.",
        variant: "destructive",
      });
    },
  });

  // Send message
  const sendMessageMutation = useMutation({
    mutationFn: async (content: string) => {
      if (!selectedSession) throw new Error("No session selected");
      
      const response = await apiRequest("POST", `/api/pdfs/sessions/${selectedSession.id}/messages`, { role: "user", content });
      return await response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ 
        queryKey: ["/api/pdfs/sessions", selectedSession?.id, "messages"] 
      });
      setMessageInput("");
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.message || "Failed to send message.",
        variant: "destructive",
      });
    },
  });

  const handleDocumentSelect = (document: PdfDocument) => {
    setSelectedDocument(document);
    setSelectedSession(null);
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!messageInput.trim() || !selectedSession) return;
    
    sendMessageMutation.mutate(messageInput);
  };

  const handleCreateNewSession = () => {
    const sessionName = `Chat ${new Date().toLocaleTimeString()}`;
    createSessionMutation.mutate(sessionName);
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-foreground mb-2">PDF Chat</h1>
          <p className="text-muted-foreground">
            Upload PDF documents and chat with them using AI-powered RAG
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[calc(100vh-200px)]">
          {/* Left Panel - Document List & Upload */}
          <div className="lg:col-span-1 space-y-4">
            <Card className="h-full">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg">Documents</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <ScrollArea className="h-[calc(100%-80px)] px-6">
                  <PdfUpload 
                    onDocumentSelect={handleDocumentSelect} 
                    selectedDocumentId={selectedDocument?.id}
                  />
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          {/* Middle Panel - Chat Sessions */}
          <div className="lg:col-span-1">
            <Card className="h-full">
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">Chat Sessions</CardTitle>
                  <Button
                    size="sm"
                    onClick={handleCreateNewSession}
                    disabled={!selectedDocument || createSessionMutation.isPending}
                    data-testid="create-session-button"
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
                {selectedDocument && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <FileText className="h-4 w-4" />
                    <span className="truncate">{selectedDocument.originalName}</span>
                  </div>
                )}
              </CardHeader>
              <CardContent className="p-0">
                <ScrollArea className="h-[calc(100%-120px)]">
                  <div className="px-6 space-y-2">
                    {!selectedDocument ? (
                      <div className="text-center py-8 text-muted-foreground">
                        <MessageSquare className="mx-auto h-12 w-12 mb-4 opacity-50" />
                        <p className="text-sm">Select a document to view chat sessions</p>
                      </div>
                    ) : loadingSessions ? (
                      <div className="space-y-2">
                        {[1, 2, 3].map((i) => (
                          <div key={i} className="animate-pulse p-3 rounded-lg bg-muted"></div>
                        ))}
                      </div>
                    ) : sessions.length === 0 ? (
                      <div className="text-center py-8 text-muted-foreground">
                        <MessageSquare className="mx-auto h-8 w-8 mb-2 opacity-50" />
                        <p className="text-sm">No chat sessions yet</p>
                        <p className="text-xs">Create one to start chatting</p>
                      </div>
                    ) : (
                      sessions.map((session) => (
                        <div
                          key={session.id}
                          className={`p-3 rounded-lg cursor-pointer transition-colors ${
                            selectedSession?.id === session.id
                              ? "bg-primary text-primary-foreground"
                              : "hover:bg-muted"
                          }`}
                          onClick={() => setSelectedSession(session)}
                          data-testid={`session-${session.id}`}
                        >
                          <p className="font-medium text-sm truncate">{session.sessionName}</p>
                          <p className="text-xs opacity-70">
                            {new Date(session.createdAt).toLocaleDateString()}
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          {/* Right Panel - Chat Messages */}
          <div className="lg:col-span-2">
            <Card className="h-full">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg">
                  {selectedSession ? selectedSession.sessionName : "Select a Chat Session"}
                </CardTitle>
                {selectedSession && (
                  <p className="text-sm text-muted-foreground">
                    Chatting with {selectedDocument?.originalName}
                  </p>
                )}
              </CardHeader>
              <CardContent className="p-0 h-[calc(100%-80px)] flex flex-col">
                {/* Messages Area */}
                <ScrollArea className="flex-1 px-6">
                  <div className="space-y-4 pb-4">
                    {!selectedSession ? (
                      <div className="text-center py-12 text-muted-foreground">
                        <Bot className="mx-auto h-16 w-16 mb-4 opacity-50" />
                        <p className="text-lg mb-2">Ready to Chat with Your PDFs</p>
                        <p className="text-sm">
                          Upload a document and create a chat session to get started
                        </p>
                      </div>
                    ) : loadingMessages ? (
                      <div className="space-y-4">
                        {[1, 2, 3].map((i) => (
                          <div key={i} className="animate-pulse flex gap-3">
                            <div className="w-8 h-8 bg-muted rounded-full"></div>
                            <div className="flex-1">
                              <div className="h-4 bg-muted rounded mb-2"></div>
                              <div className="h-4 bg-muted rounded w-3/4"></div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : messages.length === 0 ? (
                      <div className="text-center py-12 text-muted-foreground">
                        <MessageSquare className="mx-auto h-12 w-12 mb-4 opacity-50" />
                        <p className="text-lg mb-2">Start the Conversation</p>
                        <p className="text-sm">
                          Ask questions about the document content
                        </p>
                      </div>
                    ) : (
                      messages.map((message) => (
                        <div
                          key={message.id}
                          className={`flex gap-3 ${
                            message.role === "user" ? "justify-end" : ""
                          }`}
                          data-testid={`message-${message.id}`}
                        >
                          {message.role === "assistant" && (
                            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                              <Bot className="h-4 w-4 text-primary-foreground" />
                            </div>
                          )}
                          <div
                            className={`max-w-[70%] rounded-lg p-3 ${
                              message.role === "user"
                                ? "bg-primary text-primary-foreground"
                                : "bg-muted"
                            }`}
                          >
                            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                            <div className="flex items-center justify-between mt-2">
                              <span className="text-xs opacity-70">
                                {formatTime(message.timestamp)}
                              </span>
                              {message.relevantChunks.length > 0 && (
                                <Badge variant="secondary" className="text-xs">
                                  {message.relevantChunks.length} sources
                                </Badge>
                              )}
                            </div>
                          </div>
                          {message.role === "user" && (
                            <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                              <User className="h-4 w-4" />
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </ScrollArea>

                {/* Message Input */}
                {selectedSession && (
                  <>
                    <Separator />
                    <div className="p-6">
                      <form onSubmit={handleSendMessage} className="flex gap-2">
                        <Input
                          value={messageInput}
                          onChange={(e) => setMessageInput(e.target.value)}
                          placeholder="Ask a question about the document..."
                          disabled={sendMessageMutation.isPending}
                          className="flex-1"
                          data-testid="message-input"
                        />
                        <Button
                          type="submit"
                          disabled={!messageInput.trim() || sendMessageMutation.isPending}
                          data-testid="send-message-button"
                        >
                          <Send className="h-4 w-4" />
                        </Button>
                      </form>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}