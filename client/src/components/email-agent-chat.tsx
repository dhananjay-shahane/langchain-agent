import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Bot, Mail, Send, CheckCircle, Clock, User, Download, Paperclip } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import type { Email } from "@shared/schema";

// Helper function to extract clean email address
function extractEmailAddress(emailString: string): string {
  if (!emailString) return "";
  
  // If contains < and >, extract email from format "Name <email@domain.com>"
  if (emailString.includes('<') && emailString.includes('>')) {
    const match = emailString.match(/<([^>]+)>/);
    return match ? match[1].trim() : emailString;
  }
  
  // Otherwise return as is
  return emailString;
}

interface EmailProcessingMessage {
  id: string;
  role: "user" | "agent" | "system";
  content: string;
  metadata?: any;
  timestamp: string;
  emailId?: string;
}

export default function EmailAgentChat() {
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
  const [processingMessages, setProcessingMessages] = useState<EmailProcessingMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();

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
    onError: () => {
      toast({
        title: "Send Failed",
        description: "Failed to send email reply. Please try again.",
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
      // Extract clean response content instead of raw JSON
      let responseContent = "Email processed successfully";
      
      // Check if data has response field directly
      if (data && data.response) {
        responseContent = data.response;
      }
      // Check if data itself is a string containing JSON
      else if (typeof data === 'string') {
        try {
          const parsed = JSON.parse(data);
          responseContent = parsed.response || parsed.message || "Email processed successfully";
        } catch (e) {
          responseContent = data;
        }
      }
      // Check if the response is an object that was stringified
      else if (data && typeof data === 'object') {
        responseContent = data.response || data.message || JSON.stringify(data);
        
        // If it's still JSON-like, try to extract the message
        if (typeof responseContent === 'string' && responseContent.includes('"response":')) {
          try {
            const parsed = JSON.parse(responseContent);
            responseContent = parsed.response || responseContent;
          } catch (e) {
            // Keep as is if parsing fails
          }
        }
      }
      
      // Add agent response message
      const agentMessage: EmailProcessingMessage = {
        id: `agent-${Date.now()}`,
        role: "agent",
        content: responseContent,
        metadata: {
          ...data.metadata,
          showReplyButton: true,
          originalEmail: {
            from: data.metadata?.sender_email || extractEmailAddress(email.from || ""),
            subject: data.metadata?.originalEmail?.subject || `Re: ${email.subject || ""}`,
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
    onError: () => {
      toast({
        title: "Processing Failed",
        description: "Failed to process email. Please try again.",
        variant: "destructive",
      });
    },
    onSettled: () => {
      setIsProcessing(false);
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
      timestamp: email.createdAt || new Date().toISOString(),
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
                      toEmail: originalEmail.from,
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