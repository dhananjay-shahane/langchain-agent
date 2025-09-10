import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Mail, Play, Settings, RefreshCw, Eye, Clock, CheckCircle, AlertCircle, Paperclip, ArrowLeft } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { Link } from "wouter";
import type { Email, AgentConfig, EmailConfig } from "@shared/schema";

interface EmailAnalysis {
  category?: string;
  topics?: string[];
  sentiment?: string;
  action_items?: string[];
  priority?: string;
  summary?: string;
  error?: string;
}

export function EmailMonitor() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
  const [emailConfig, setEmailConfig] = useState({
    emailAddress: "",
    emailPassword: "",
    imapHost: "imap.gmail.com",
    smtpHost: "smtp.gmail.com",
    pollInterval: 20
  });

  // Fetch agent configuration
  const { data: agentConfig } = useQuery({
    queryKey: ["/api/agent/config"],
  });

  // Fetch email configuration
  const { data: existingEmailConfig } = useQuery({
    queryKey: ["/api/email/config"],
    queryFn: async () => {
      const response = await fetch("/api/email/config");
      if (!response.ok) {
        if (response.status === 404) return null;
        throw new Error("Failed to fetch email config");
      }
      return response.json();
    },
  });

  // Fetch emails
  const { data: emails = [], isLoading: emailsLoading } = useQuery({
    queryKey: ["/api/emails"],
    queryFn: async () => {
      const response = await fetch("/api/emails?limit=50");
      if (!response.ok) throw new Error("Failed to fetch emails");
      return response.json();
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Save email configuration
  const saveEmailConfigMutation = useMutation({
    mutationFn: async (config: typeof emailConfig) => {
      return await apiRequest("POST", "/api/email/config", config);
    },
    onSuccess: () => {
      toast({
        title: "Configuration Saved",
        description: "Email configuration has been saved successfully",
      });
      queryClient.invalidateQueries({ queryKey: ["/api/email/config"] });
    },
    onError: (error: any) => {
      toast({
        title: "Save Failed",
        description: error.message || "Failed to save email configuration",
        variant: "destructive",
      });
    },
  });

  // Run email agent
  const runEmailAgentMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch("/api/emails/run-agent", { method: "POST" });
      if (!response.ok) throw new Error("Failed to run email agent");
      return response.json();
    },
    onSuccess: (data) => {
      toast({
        title: "Email Agent Completed",
        description: data.message,
      });
      queryClient.invalidateQueries({ queryKey: ["/api/emails"] });
    },
    onError: (error: any) => {
      toast({
        title: "Email Agent Failed",
        description: error.message || "Failed to run email agent",
        variant: "destructive",
      });
    },
  });

  // Load existing email configuration
  useEffect(() => {
    if (existingEmailConfig) {
      setEmailConfig({
        emailAddress: existingEmailConfig.emailAddress || "",
        emailPassword: existingEmailConfig.emailPassword || "",
        imapHost: existingEmailConfig.imapHost || "imap.gmail.com",
        smtpHost: existingEmailConfig.smtpHost || "smtp.gmail.com",
        pollInterval: parseInt(existingEmailConfig.pollInterval || "20")
      });
    }
  }, [existingEmailConfig]);

  // Listen for real-time updates
  useEffect(() => {
    const handleNewEmail = (email: Email) => {
      queryClient.setQueryData(["/api/emails"], (oldData: Email[] = []) => [email, ...oldData]);
      toast({
        title: "New Email Received",
        description: `From: ${email.sender}`,
      });
    };

    const handleEmailUpdated = (email: Email) => {
      queryClient.setQueryData(["/api/emails"], (oldData: Email[] = []) =>
        oldData.map(e => e.id === email.id ? email : e)
      );
    };

    const handleAgentCompleted = (data: { success: boolean; output: string }) => {
      if (data.success) {
        queryClient.invalidateQueries({ queryKey: ["/api/emails"] });
        toast({
          title: "Email Processing Complete",
          description: "New emails have been processed by the agent",
        });
      }
    };

    // WebSocket event listeners would go here
    // global.io?.on("new_email", handleNewEmail);
    // global.io?.on("email_updated", handleEmailUpdated);
    // global.io?.on("email_agent_completed", handleAgentCompleted);

    return () => {
      // global.io?.off("new_email", handleNewEmail);
      // global.io?.off("email_updated", handleEmailUpdated);
      // global.io?.off("email_agent_completed", handleAgentCompleted);
    };
  }, [queryClient, toast]);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleString();
  };

  const getPriorityColor = (priority?: string) => {
    switch (priority?.toLowerCase()) {
      case "high": return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300";
      case "medium": return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300";
      case "low": return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300";
      default: return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300";
    }
  };

  const getSentimentColor = (sentiment?: string) => {
    switch (sentiment?.toLowerCase()) {
      case "positive": return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300";
      case "negative": return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300";
      case "neutral": return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300";
      default: return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300";
    }
  };

  return (
    <div className="container mx-auto p-6" data-testid="email-monitor">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" size="sm" data-testid="button-back-home">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Home
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Email Monitor</h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              AI-powered email monitoring and analysis
              {agentConfig && (agentConfig as AgentConfig).provider && (
                <span className="ml-2 text-sm">
                  • Using {(agentConfig as AgentConfig).provider} ({(agentConfig as AgentConfig).model})
                </span>
              )}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => runEmailAgentMutation.mutate()}
            disabled={runEmailAgentMutation.isPending}
            data-testid="button-run-agent"
          >
            {runEmailAgentMutation.isPending ? (
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-2" />
            )}
            Run Agent
          </Button>
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="outline" data-testid="button-config">
                <Settings className="h-4 w-4 mr-2" />
                Config
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Email Configuration</DialogTitle>
                <DialogDescription>
                  Configure your email monitoring settings
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="email-address">Email Address</Label>
                  <Input
                    id="email-address"
                    type="email"
                    value={emailConfig.emailAddress}
                    onChange={(e) => setEmailConfig(prev => ({ ...prev, emailAddress: e.target.value }))}
                    placeholder="your-email@example.com"
                    data-testid="input-email-address"
                  />
                </div>
                <div>
                  <Label htmlFor="email-password">App Password</Label>
                  <Input
                    id="email-password"
                    type="password"
                    value={emailConfig.emailPassword}
                    onChange={(e) => setEmailConfig(prev => ({ ...prev, emailPassword: e.target.value }))}
                    placeholder="App-specific password"
                    data-testid="input-email-password"
                  />
                </div>
                <div>
                  <Label htmlFor="imap-host">IMAP Host</Label>
                  <Input
                    id="imap-host"
                    value={emailConfig.imapHost}
                    onChange={(e) => setEmailConfig(prev => ({ ...prev, imapHost: e.target.value }))}
                    data-testid="input-imap-host"
                  />
                </div>
                <div>
                  <Label htmlFor="poll-interval">Poll Interval (seconds)</Label>
                  <Input
                    id="poll-interval"
                    type="number"
                    value={emailConfig.pollInterval}
                    onChange={(e) => setEmailConfig(prev => ({ ...prev, pollInterval: parseInt(e.target.value) }))}
                    min={5}
                    max={300}
                    data-testid="input-poll-interval"
                  />
                </div>
                <Button 
                  className="w-full" 
                  onClick={() => saveEmailConfigMutation.mutate(emailConfig)}
                  disabled={saveEmailConfigMutation.isPending}
                  data-testid="button-save-config"
                >
                  {saveEmailConfigMutation.isPending ? (
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  ) : null}
                  Save Configuration
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Email List */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Mail className="h-5 w-5" />
                Recent Emails ({emails.length})
              </CardTitle>
              <CardDescription>
                Latest emails processed by the AI agent
              </CardDescription>
            </CardHeader>
            <CardContent>
              {emailsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="h-6 w-6 animate-spin" />
                  <span className="ml-2">Loading emails...</span>
                </div>
              ) : emails.length === 0 ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  <Mail className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>No emails found</p>
                  <p className="text-sm">Run the email agent to check for new messages</p>
                </div>
              ) : (
                <ScrollArea className="h-96">
                  <div className="space-y-3">
                    {emails.map((email) => (
                      <div
                        key={email.id}
                        className={`p-3 border rounded-lg cursor-pointer transition-colors hover:bg-gray-50 dark:hover:bg-gray-800 ${
                          selectedEmail?.id === email.id ? "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800" : ""
                        }`}
                        onClick={() => setSelectedEmail(email)}
                        data-testid={`email-item-${email.id}`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-medium text-sm truncate">
                                {email.sender}
                              </span>
                              {email.hasAttachments && (
                                <Paperclip className="h-3 w-3 text-gray-400" />
                              )}
                            </div>
                            <p className="text-sm font-medium truncate mb-1">
                              {email.subject}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                              {email.body ? email.body.substring(0, 100) + "..." : "No content"}
                            </p>
                          </div>
                          <div className="flex flex-col items-end gap-1 ml-2">
                            {email.processed ? (
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            ) : (
                              <Clock className="h-4 w-4 text-yellow-500" />
                            )}
                            <span className="text-xs text-gray-400">
                              {formatDate(email.receivedAt)}
                            </span>
                          </div>
                        </div>
                        {email.aiAnalysis && (
                          <div className="flex gap-1 mt-2">
                            {(email.aiAnalysis as EmailAnalysis).priority && (
                              <Badge 
                                variant="secondary" 
                                className={`text-xs ${getPriorityColor((email.aiAnalysis as EmailAnalysis).priority)}`}
                              >
                                {(email.aiAnalysis as EmailAnalysis).priority}
                              </Badge>
                            )}
                            {(email.aiAnalysis as EmailAnalysis).sentiment && (
                              <Badge 
                                variant="secondary"
                                className={`text-xs ${getSentimentColor((email.aiAnalysis as EmailAnalysis).sentiment)}`}
                              >
                                {(email.aiAnalysis as EmailAnalysis).sentiment}
                              </Badge>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Email Details */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Eye className="h-5 w-5" />
                Email Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              {selectedEmail ? (
                <Tabs defaultValue="details" className="w-full">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="details">Details</TabsTrigger>
                    <TabsTrigger value="analysis">Analysis</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="details" className="space-y-4">
                    <div>
                      <Label className="text-sm font-medium">From</Label>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{selectedEmail.sender}</p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium">Subject</Label>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{selectedEmail.subject}</p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium">Received</Label>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        {formatDate(selectedEmail.receivedAt ? selectedEmail.receivedAt.toString() : null)}
                      </p>
                    </div>
                    {selectedEmail.processedAt && (
                      <div>
                        <Label className="text-sm font-medium">Processed</Label>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {formatDate(selectedEmail.processedAt ? selectedEmail.processedAt.toString() : null)}
                        </p>
                      </div>
                    )}
                    <Separator />
                    <div>
                      <Label className="text-sm font-medium">Content</Label>
                      <ScrollArea className="h-32 mt-1">
                        <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                          {selectedEmail.body || "No content available"}
                        </p>
                      </ScrollArea>
                    </div>
                    {selectedEmail.attachments && Array.isArray(selectedEmail.attachments) && selectedEmail.attachments.length > 0 && (
                      <div>
                        <Label className="text-sm font-medium">Attachments</Label>
                        <div className="space-y-1 mt-1">
                          {(selectedEmail.attachments as any[]).map((attachment: any, index: number) => (
                            <div key={index} className="text-xs p-2 bg-gray-50 dark:bg-gray-800 rounded">
                              <div className="font-medium">{attachment.filename}</div>
                              <div className="text-gray-500">{attachment.content_type}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </TabsContent>
                  
                  <TabsContent value="analysis" className="space-y-4">
                    {selectedEmail.aiAnalysis ? (
                      <div className="space-y-3">
                        {(selectedEmail.aiAnalysis as EmailAnalysis).error ? (
                          <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
                            <AlertCircle className="h-4 w-4" />
                            <span className="text-sm">Analysis failed</span>
                          </div>
                        ) : (
                          <>
                            {(selectedEmail.aiAnalysis as EmailAnalysis).category && (
                              <div>
                                <Label className="text-sm font-medium">Category</Label>
                                <Badge variant="outline" className="ml-2">
                                  {(selectedEmail.aiAnalysis as EmailAnalysis).category}
                                </Badge>
                              </div>
                            )}
                            {(selectedEmail.aiAnalysis as EmailAnalysis).priority && (
                              <div>
                                <Label className="text-sm font-medium">Priority</Label>
                                <Badge 
                                  className={`ml-2 ${getPriorityColor((selectedEmail.aiAnalysis as EmailAnalysis).priority)}`}
                                >
                                  {(selectedEmail.aiAnalysis as EmailAnalysis).priority}
                                </Badge>
                              </div>
                            )}
                            {(selectedEmail.aiAnalysis as EmailAnalysis).sentiment && (
                              <div>
                                <Label className="text-sm font-medium">Sentiment</Label>
                                <Badge 
                                  className={`ml-2 ${getSentimentColor((selectedEmail.aiAnalysis as EmailAnalysis).sentiment)}`}
                                >
                                  {(selectedEmail.aiAnalysis as EmailAnalysis).sentiment}
                                </Badge>
                              </div>
                            )}
                            {(selectedEmail.aiAnalysis as EmailAnalysis).summary && (
                              <div>
                                <Label className="text-sm font-medium">Summary</Label>
                                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                                  {(selectedEmail.aiAnalysis as EmailAnalysis).summary}
                                </p>
                              </div>
                            )}
                            {(selectedEmail.aiAnalysis as EmailAnalysis).topics && (selectedEmail.aiAnalysis as EmailAnalysis).topics!.length > 0 && (
                              <div>
                                <Label className="text-sm font-medium">Topics</Label>
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {(selectedEmail.aiAnalysis as EmailAnalysis).topics!.map((topic, index) => (
                                    <Badge key={index} variant="secondary" className="text-xs">
                                      {topic}
                                    </Badge>
                                  ))}
                                </div>
                              </div>
                            )}
                            {(selectedEmail.aiAnalysis as EmailAnalysis).action_items && (selectedEmail.aiAnalysis as EmailAnalysis).action_items!.length > 0 && (
                              <div>
                                <Label className="text-sm font-medium">Action Items</Label>
                                <ul className="text-sm text-gray-600 dark:text-gray-400 mt-1 space-y-1">
                                  {(selectedEmail.aiAnalysis as EmailAnalysis).action_items!.map((item, index) => (
                                    <li key={index} className="flex items-start gap-2">
                                      <span className="w-1 h-1 bg-gray-400 rounded-full mt-2 flex-shrink-0"></span>
                                      {item}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-4 text-gray-500 dark:text-gray-400">
                        <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">No AI analysis available</p>
                        <p className="text-xs">Run the email agent to analyze this email</p>
                      </div>
                    )}
                  </TabsContent>
                </Tabs>
              ) : (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  <Eye className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>Select an email to view details</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}