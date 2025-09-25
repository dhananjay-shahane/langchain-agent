import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import { Bot, Mail, Send, CheckCircle, Clock, User, Download, Paperclip, Zap, PlayCircle, StopCircle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { useSocket } from "@/hooks/use-socket";
import type { Email } from "@shared/schema";

// Helper function to extract clean email address and name
function extractEmailAddress(emailString: string): string {
  if (!emailString) return "";
  
  // If contains < and >, extract email from format "Name <email@domain.com>"
  if (emailString.includes('<') && emailString.includes('>')) {
    const match = emailString.match(/<([^>]+)>/);
    return match ? match[1].trim() : emailString;
  }
  
  // Otherwise return as is
  return emailString.trim();
}

// Helper function to extract name from email string
function extractSenderName(emailString: string): string {
  if (!emailString) return "";
  
  // If contains < and >, extract name from format "Name <email@domain.com>"
  if (emailString.includes('<') && emailString.includes('>')) {
    const namePart = emailString.split('<')[0].trim();
    return namePart.replace(/"/g, ''); // Remove quotes if present
  }
  
  // If no name format, return the email itself
  return emailString.trim();
}

interface EmailProcessingMessage {
  id: string;
  role: "user" | "agent" | "system";
  content: string;
  metadata?: any;
  timestamp: string;
  emailId?: string;
}

interface AutoProcessingStatus {
  isRunning: boolean;
  currentStep: number;
  totalEmails: number;
  currentEmail?: {
    id: string;
    subject: string;
  };
  completed: number;
  errors: number;
}

export default function EmailAgentChat() {
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
  const [processingMessages, setProcessingMessages] = useState<EmailProcessingMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [autoProcessingStatus, setAutoProcessingStatus] = useState<AutoProcessingStatus>({
    isRunning: false,
    currentStep: 0,
    totalEmails: 0,
    completed: 0,
    errors: 0
  });
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
  // Socket with auto-processing event handlers
  const socket = useSocket({
    onAutoProcessingStarted: (data) => {
      setAutoProcessingStatus({
        isRunning: true,
        currentStep: 0,
        totalEmails: data.totalEmails,
        completed: 0,
        errors: 0
      });
    },
    onProcessingEmail: (data) => {
      setAutoProcessingStatus(prev => ({
        ...prev,
        currentStep: data.step,
        currentEmail: {
          id: data.emailId,
          subject: data.subject
        }
      }));
    },
    onResponseGenerated: (data) => {
      // Add response to processing messages
      const agentMessage: EmailProcessingMessage = {
        id: `auto-agent-${Date.now()}-${data.emailId}`,
        role: "agent",
        content: data.response,
        metadata: { autoProcessed: true },
        timestamp: new Date().toISOString(),
        emailId: data.emailId
      };
      setProcessingMessages(prev => [...prev, agentMessage]);
    },
    onReplySent: (data) => {
      // Add system message about reply being sent
      const systemMessage: EmailProcessingMessage = {
        id: `auto-system-${Date.now()}-${data.emailId}`,
        role: "system",
        content: `✅ Reply sent to ${data.toEmail}`,
        timestamp: new Date().toISOString(),
        emailId: data.emailId
      };
      setProcessingMessages(prev => [...prev, systemMessage]);
    },
    onAutoProcessingCompleted: (data) => {
      setAutoProcessingStatus(prev => ({
        ...prev,
        isRunning: false,
        completed: data.processed,
        errors: data.errors
      }));
      
      // Add final summary message
      const summaryMessage: EmailProcessingMessage = {
        id: `auto-summary-${Date.now()}`,
        role: "system",
        content: `🎉 Auto-processing completed! Processed ${data.processed} email(s)${data.errors > 0 ? ` with ${data.errors} error(s)` : ' successfully'}.`,
        timestamp: new Date().toISOString()
      };
      setProcessingMessages(prev => [...prev, summaryMessage]);
    },
    onAutoProcessingError: (data) => {
      setAutoProcessingStatus(prev => ({
        ...prev,
        isRunning: false,
        errors: prev.errors + 1
      }));
      
      // Add error message
      const errorMessage: EmailProcessingMessage = {
        id: `auto-error-${Date.now()}`,
        role: "agent",
        content: `❌ Auto-processing error: ${data.error}`,
        metadata: { error: true },
        timestamp: new Date().toISOString()
      };
      setProcessingMessages(prev => [...prev, errorMessage]);
    }
  });

  // Fetch pending emails
  const { data: emails = [], isLoading: loadingEmails } = useQuery<Email[]>({
    queryKey: ["/api/emails"],
  });

  // Filter pending emails
  const pendingEmails = emails.filter(email => email.replyStatus === "pending");

  // Send email reply mutation
  const sendEmailMutation = useMutation({
    mutationFn: async ({ toEmail, subject, content }: { toEmail: string, subject: string, content: string }) => {
      const response = await apiRequest("POST", "/api/emails/send-reply", {
        toEmail,
        subject,
        content
      });
      return response.json();
    },
    onSuccess: (data, variables) => {
      toast({
        title: "Email Sent",
        description: `Reply sent successfully to ${variables.toEmail}`,
      });
      
      // Refresh emails to update status
      queryClient.invalidateQueries({ queryKey: ["/api/emails"] });
    },
    onError: (error: any) => {
      console.error("Email send error:", error);
      toast({
        title: "Send Failed",
        description: error?.message || "Failed to send email reply. Please try again.",
        variant: "destructive",
      });
    }
  });

  const processEmailMutation = useMutation({
    mutationFn: async (email: Email) => {
      const response = await apiRequest("POST", "/api/emails/process", {
        emailId: email.id,
        emailContent: email.body,
        emailFrom: email.from,
        emailSubject: email.subject,
        attachments: email.attachments || []
      });
      return response.json();
    },
    onSuccess: (data, email) => {
      // Extract only the clean email response content, no metadata
      let responseContent = "Email processed successfully";
      
      // Handle error cases first
      if (data && data.error) {
        responseContent = typeof data.error === 'string' ? data.error : JSON.stringify(data.error);
      }
      else if (data && data.response) {
        // If response is a string, extract clean response
        if (typeof data.response === 'string') {
          let cleanResponse = data.response.trim();
          
          // Remove initialization text (everything before JSON)
          const jsonMatch = cleanResponse.match(/{.*}$/);
          if (jsonMatch) {
            try {
              const jsonData = JSON.parse(jsonMatch[0]);
              responseContent = jsonData.response || jsonData.message || "Email processed successfully";
            } catch (e) {
              // If JSON parsing fails, try to extract text between quotes
              const responseMatch = cleanResponse.match(/"response":\s*"([^"]+)"/);
              responseContent = responseMatch ? responseMatch[1] : cleanResponse;
            }
          } else {
            responseContent = cleanResponse;
          }
        } else if (typeof data.response === 'object') {
          // If response is an object, safely extract the content
          responseContent = data.response.message || data.response.content || data.response.response || 
                          (data.response.error ? String(data.response.error) : String(data.response));
        } else {
          // Convert non-string, non-object responses to string
          responseContent = String(data.response);
        }
      }
      // If data is an object, extract the response
      else if (data && typeof data === 'object') {
        if (data.error) {
          responseContent = typeof data.error === 'string' ? data.error : JSON.stringify(data.error);
        } else {
          // Safely extract content and ensure it's a string
          let content = data.response || data.message || data.content;
          if (typeof content === 'string') {
            responseContent = content;
          } else if (content !== undefined && content !== null) {
            responseContent = JSON.stringify(content);
          } else {
            responseContent = String(data);
          }
        }
      }
      
      // Final defensive guard: ensure responseContent is always a string
      if (typeof responseContent !== 'string') {
        responseContent = JSON.stringify(responseContent);
      }
      
      // Final cleanup: remove any remaining escape characters and metadata
      if (typeof responseContent === 'string') {
        responseContent = responseContent
          .replace(/\\n/g, '\n')
          .replace(/\\"/g, '"')
          .replace(/^["']/g, '')
          .replace(/["']$/g, '')
          .trim();
      }
      
      // Add agent response message
      const agentMessage: EmailProcessingMessage = {
        id: `agent-${Date.now()}`,
        role: "agent",
        content: responseContent,
        metadata: {
          ...(data?.metadata || {}),
          showReplyButton: true,
          originalEmail: {
            from: extractEmailAddress(email.from || ""),
            subject: `Re: ${email.subject || ""}`,
            content: email.body || ""
          }
        },
        timestamp: new Date().toISOString(),
        emailId: email.id
      };
      
      setProcessingMessages(prev => [...prev, agentMessage]);
      
      // Refresh emails to update status
      queryClient.invalidateQueries({ queryKey: ["/api/emails"] });
      
      toast({
        title: "Email Response Generated",
        description: `Ready to send reply for: ${email.subject}`,
      });
    },
    onError: (error: any) => {
      // Handle error objects properly
      let errorMessage = "Failed to process email. Please try again.";
      
      if (error) {
        if (typeof error === 'string') {
          errorMessage = error;
        } else if (error.message) {
          errorMessage = error.message;
        } else if (typeof error === 'object') {
          errorMessage = JSON.stringify(error);
        }
      }
      
      // Add error message to chat
      const errorMsg: EmailProcessingMessage = {
        id: `error-${Date.now()}`,
        role: "agent",
        content: `Error: ${errorMessage}`,
        metadata: { error: true },
        timestamp: new Date().toISOString(),
        emailId: selectedEmail?.id
      };
      
      setProcessingMessages(prev => [...prev, errorMsg]);
      
      toast({
        title: "Processing Failed",
        description: errorMessage,
        variant: "destructive",
      });
    },
    onSettled: () => {
      setIsProcessing(false);
    }
  });

  // Auto-processing mutation for batch email processing
  const autoProcessEmailsMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest("POST", "/api/emails/process-auto", {});
      return response.json();
    },
    onSuccess: (data) => {
      // Clear any existing messages and show auto-processing started message
      const startMessage: EmailProcessingMessage = {
        id: `auto-start-${Date.now()}`,
        role: "system",
        content: `🚀 Starting automatic processing of ${pendingEmails.length} pending email(s)...`,
        timestamp: new Date().toISOString()
      };
      setProcessingMessages([startMessage]);
      
      toast({
        title: "Auto-Processing Started",
        description: `Processing ${pendingEmails.length} pending email(s)`,
      });
    },
    onError: (error: any) => {
      console.error("Auto-processing error:", error);
      
      let errorMessage = "Failed to start auto-processing. Please try again.";
      
      if (error) {
        if (typeof error === 'string') {
          errorMessage = error;
        } else if (error.message) {
          errorMessage = error.message;
        } else if (typeof error === 'object') {
          errorMessage = JSON.stringify(error);
        }
      }
      
      // Add error message to chat
      const errorMsg: EmailProcessingMessage = {
        id: `auto-error-${Date.now()}`,
        role: "agent",
        content: `❌ Auto-processing error: ${errorMessage}`,
        metadata: { error: true },
        timestamp: new Date().toISOString()
      };
      
      setProcessingMessages(prev => [...prev, errorMsg]);
      
      // Reset auto-processing status
      setAutoProcessingStatus({
        isRunning: false,
        currentStep: 0,
        totalEmails: 0,
        completed: 0,
        errors: 0
      });
      
      toast({
        title: "Auto-Processing Failed",
        description: errorMessage,
        variant: "destructive",
      });
    }
  });

  const handleSelectEmail = (email: Email) => {
    setSelectedEmail(email);
    
    // Add email content as user message
    const userMessage: EmailProcessingMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: email.body || "",
      metadata: {
        from: email.from,
        subject: email.subject,
        attachments: email.attachments,
        emailId: email.id
      },
      timestamp: typeof email.createdAt === 'string' ? email.createdAt : (email.createdAt ? email.createdAt.toISOString() : new Date().toISOString()),
      emailId: email.id
    };
    
    setProcessingMessages([userMessage]);
  };

  const handleProcessEmail = async () => {
    if (!selectedEmail || isProcessing) return;
    
    setIsProcessing(true);
    
    // Add processing indicator
    const processingMessage: EmailProcessingMessage = {
      id: `processing-${Date.now()}`,
      role: "agent",
      content: "Processing your email and generating response...",
      metadata: { thinking: true },
      timestamp: new Date().toISOString(),
      emailId: selectedEmail.id
    };
    
    setProcessingMessages(prev => [...prev, processingMessage]);
    
    // Process the email
    await processEmailMutation.mutateAsync(selectedEmail);
  };

  const handleAutoProcessEmails = async () => {
    if (autoProcessingStatus.isRunning || pendingEmails.length === 0) return;
    
    // Start auto-processing
    await autoProcessEmailsMutation.mutateAsync();
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [processingMessages]);

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const renderMessage = (msg: EmailProcessingMessage) => {
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
            {/* Show email metadata for user messages */}
            {isUser && msg.metadata && (
              <div className="mb-3 text-xs opacity-75 space-y-1">
                <div className="flex items-center gap-1">
                  <Mail className="w-3 h-3" />
                  <span>From: {extractEmailAddress(msg.metadata.from || "")}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span>📝</span>
                  <span>Subject: {msg.metadata.subject}</span>
                </div>
                {msg.metadata.attachments && msg.metadata.attachments.length > 0 && (
                  <div className="flex items-center gap-1">
                    <Paperclip className="w-3 h-3" />
                    <span>{msg.metadata.attachments.length} attachment(s)</span>
                  </div>
                )}
              </div>
            )}
            
            <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            
            {/* Show processing indicator */}
            {msg.metadata?.thinking && (
              <div className="mt-3 flex items-center gap-2 text-xs opacity-75">
                <div className="w-2 h-2 bg-current rounded-full animate-pulse"></div>
                <span>Generating reply...</span>
              </div>
            )}

            {/* Show attachments for user messages */}
            {isUser && msg.metadata?.attachments && msg.metadata.attachments.length > 0 && (
              <div className="mt-3 p-3 bg-card/10 border border-border/20 rounded-lg">
                <div className="text-xs font-medium mb-2">Attachments:</div>
                <div className="space-y-1">
                  {msg.metadata.attachments.map((filename: string, index: number) => (
                    <div key={index} className="flex items-center gap-2 text-xs">
                      <Download className="w-3 h-3" />
                      <span>{filename}</span>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-5 px-2 text-xs"
                        onClick={() => window.open(`/api/emails/attachments/${filename}`, '_blank')}
                        data-testid={`button-download-attachment-${filename}`}
                      >
                        Download
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Show Reply Mail button for agent responses */}
            {!isUser && msg.metadata?.showReplyButton && (
              <div className="mt-4 pt-3 border-t border-border/20">
                <Button
                  onClick={() => {
                    const originalEmail = msg.metadata.originalEmail;
                    sendEmailMutation.mutate({
                      toEmail: extractEmailAddress(originalEmail.from),
                      subject: originalEmail.subject,
                      content: msg.content
                    });
                  }}
                  disabled={sendEmailMutation.isPending}
                  className="w-full"
                  data-testid="button-reply-mail"
                >
                  <Send className="w-4 h-4 mr-2" />
                  {sendEmailMutation.isPending ? "Sending..." : "Reply Mail"}
                </Button>
              </div>
            )}
          </div>
          
          <span className="text-xs text-muted-foreground mt-1 block">
            {isUser ? "Email Content" : "Agent Reply"} • {formatTimestamp(msg.timestamp)}
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
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-foreground">Email Agent Chat</h1>
        <p className="text-muted-foreground mt-2">
          Process pending emails one by one and generate automated responses
        </p>
      </div>

      {/* Auto-Processing Section */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5" />
              Automatic Email Processing
            </div>
            <Button
              onClick={handleAutoProcessEmails}
              disabled={autoProcessingStatus.isRunning || pendingEmails.length === 0 || autoProcessEmailsMutation.isPending}
              variant={autoProcessingStatus.isRunning ? "secondary" : "default"}
              data-testid="button-auto-process"
            >
              {autoProcessingStatus.isRunning ? (
                <>
                  <StopCircle className="w-4 h-4 mr-2" />
                  Processing...
                </>
              ) : (
                <>
                  <PlayCircle className="w-4 h-4 mr-2" />
                  Process All ({pendingEmails.length})
                </>
              )}
            </Button>
          </CardTitle>
          <CardDescription>
            Automatically process all pending emails and generate responses in batch
          </CardDescription>
        </CardHeader>
        <CardContent>
          {autoProcessingStatus.isRunning ? (
            <div className="space-y-4">
              {/* Progress Bar */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Processing Progress</span>
                  <span>{autoProcessingStatus.currentStep} of {autoProcessingStatus.totalEmails}</span>
                </div>
                <Progress 
                  value={(autoProcessingStatus.currentStep / autoProcessingStatus.totalEmails) * 100} 
                  className="w-full"
                  data-testid="progress-auto-processing"
                />
              </div>
              
              {/* Current Email Being Processed */}
              {autoProcessingStatus.currentEmail && (
                <div className="bg-muted/50 p-3 rounded-lg">
                  <div className="flex items-center gap-2 text-sm">
                    <div className="w-2 h-2 bg-primary rounded-full animate-pulse"></div>
                    <span className="font-medium">Currently processing:</span>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1 truncate" data-testid="text-current-email">
                    {autoProcessingStatus.currentEmail.subject}
                  </p>
                </div>
              )}
              
              {/* Statistics */}
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <div className="text-2xl font-bold text-green-600" data-testid="text-completed-count">
                    {autoProcessingStatus.completed}
                  </div>
                  <div className="text-xs text-muted-foreground">Completed</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-blue-600" data-testid="text-remaining-count">
                    {autoProcessingStatus.totalEmails - autoProcessingStatus.currentStep}
                  </div>
                  <div className="text-xs text-muted-foreground">Remaining</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-red-600" data-testid="text-errors-count">
                    {autoProcessingStatus.errors}
                  </div>
                  <div className="text-xs text-muted-foreground">Errors</div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-4">
              <div className="text-muted-foreground">
                {pendingEmails.length === 0 ? (
                  <p>No pending emails to process</p>
                ) : (
                  <p>Ready to process {pendingEmails.length} pending email(s) automatically</p>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pending Emails List */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mail className="w-5 h-5" />
              Pending Emails ({pendingEmails.length})
            </CardTitle>
            <CardDescription>
              Select an email to process with the email agent
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[600px]">
              {loadingEmails ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="animate-pulse p-3 border rounded-lg">
                      <div className="h-4 bg-muted rounded w-3/4 mb-2"></div>
                      <div className="h-3 bg-muted rounded w-1/2"></div>
                    </div>
                  ))}
                </div>
              ) : pendingEmails.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <CheckCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No pending emails</p>
                  <p className="text-sm">All emails have been processed</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {pendingEmails.map((email) => (
                    <div
                      key={email.id}
                      className={`p-3 border rounded-lg cursor-pointer transition-colors hover:bg-muted/50 ${
                        selectedEmail?.id === email.id ? "border-primary bg-muted/30" : ""
                      }`}
                      onClick={() => handleSelectEmail(email)}
                      data-testid={`email-item-${email.id}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="font-medium truncate" title={email.subject}>
                            {email.subject}
                          </div>
                          <div className="text-sm text-muted-foreground truncate" title={email.from}>
                            From: {extractEmailAddress(email.from || "")}
                          </div>
                          <div className="text-xs text-muted-foreground mt-1">
                            {formatDate(typeof email.createdAt === 'string' ? email.createdAt : new Date().toISOString())}
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-1">
                          <Badge variant="default">
                            {email.replyStatus}
                          </Badge>
                          {email.attachments && email.attachments.length > 0 && (
                            <Badge variant="outline" className="text-xs">
                              📎 {email.attachments.length}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Email Processing Chat */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Email Processing Chat</span>
              {selectedEmail && (
                <Button
                  onClick={handleProcessEmail}
                  disabled={isProcessing || !selectedEmail}
                  data-testid="button-process-email"
                >
                  {isProcessing ? (
                    <>
                      <Clock className="w-4 h-4 mr-2 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4 mr-2" />
                      Process & Reply
                    </>
                  )}
                </Button>
              )}
            </CardTitle>
            <CardDescription>
              {selectedEmail ? "Review email content and generate automated response" : "Select an email to start processing"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!selectedEmail ? (
              <div className="text-center py-8 text-muted-foreground h-[600px] flex items-center justify-center">
                <div>
                  <Bot className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Select a pending email to start processing</p>
                  <p className="text-sm">The email agent will analyze content and generate an appropriate response</p>
                </div>
              </div>
            ) : (
              <ScrollArea className="h-[600px]">
                <div className="space-y-4">
                  {processingMessages.length === 0 ? (
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center">
                        <Bot className="w-4 h-4 text-primary-foreground" />
                      </div>
                      <div className="flex-1">
                        <div className="bg-muted p-4 rounded-lg">
                          <p className="text-sm text-foreground">
                            Email Agent ready to process your email. I will:
                          </p>
                          <ul className="list-disc list-inside text-sm text-muted-foreground mt-2 space-y-1">
                            <li>Analyze the email content and context</li>
                            <li>Generate an appropriate response</li>
                            <li>Handle any attachments if present</li>
                            <li>Send the reply automatically</li>
                          </ul>
                        </div>
                        <span className="text-xs text-muted-foreground mt-1 block">Agent • just now</span>
                      </div>
                    </div>
                  ) : (
                    processingMessages.map(renderMessage)
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}