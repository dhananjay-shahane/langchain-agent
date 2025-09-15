import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { toast } from "@/hooks/use-toast";
import { Mail, Play, Square, Trash2, Download, Clock, CheckCircle, AlertCircle } from "lucide-react";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { useSocket } from "@/hooks/use-socket";
import type { Email, EmailMonitorStatus } from "@shared/schema";

// Helper function to extract clean email address
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

export default function EmailsPage() {
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);

  // Socket connection for real-time updates
  useSocket({
    onNewEmail: (email: Email) => {
      queryClient.invalidateQueries({ queryKey: ["/api/emails"] });
      toast({
        title: "📧 New Email Received",
        description: `From: ${extractEmailAddress(email.from)}\nSubject: ${email.subject}`,
      });
    },
    onEmailDeleted: (data: { id: string }) => {
      queryClient.invalidateQueries({ queryKey: ["/api/emails"] });
      if (selectedEmail?.id === data.id) {
        setSelectedEmail(null);
      }
    },
    onEmailMonitorStatus: (status: EmailMonitorStatus) => {
      queryClient.setQueryData(["/api/emails/monitor/status"], status);
    },
  });

  // Fetch emails
  const { data: emails = [], isLoading: loadingEmails } = useQuery<Email[]>({
    queryKey: ["/api/emails"],
  });

  // Fetch monitor status
  const { data: monitorStatus } = useQuery<EmailMonitorStatus>({
    queryKey: ["/api/emails/monitor/status"],
  });

  // Start monitor mutation
  const startMonitorMutation = useMutation({
    mutationFn: () => apiRequest("POST", "/api/emails/monitor/start", {}),
    onMutate: () => setIsStarting(true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/emails/monitor/status"] });
      toast({
        title: "✅ Email Monitor Started",
        description: "Now monitoring for new emails",
      });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Failed to Start Monitor",
        description: error.message || "Unknown error occurred",
        variant: "destructive",
      });
    },
    onSettled: () => setIsStarting(false),
  });

  // Stop monitor mutation
  const stopMonitorMutation = useMutation({
    mutationFn: () => apiRequest("POST", "/api/emails/monitor/stop", {}),
    onMutate: () => setIsStopping(true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/emails/monitor/status"] });
      toast({
        title: "🛑 Email Monitor Stopped",
        description: "Email monitoring has been stopped",
      });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Failed to Stop Monitor",
        description: error.message || "Unknown error occurred",
        variant: "destructive",
      });
    },
    onSettled: () => setIsStopping(false),
  });

  // Delete email mutation
  const deleteEmailMutation = useMutation({
    mutationFn: (id: string) => apiRequest("DELETE", `/api/emails/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/emails"] });
      toast({
        title: "✅ Email Deleted",
        description: "Email has been removed",
      });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Failed to Delete Email",
        description: error.message || "Unknown error occurred",
        variant: "destructive",
      });
    },
  });

  // Mark email as completed mutation
  const markCompletedMutation = useMutation({
    mutationFn: async (id: string) => {
      const response = await apiRequest("PUT", `/api/emails/${id}/status`, {
        status: "completed"
      });
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/emails"] });
      toast({
        title: "✅ Email Marked Complete",
        description: "Email has been marked as completed",
      });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Failed to Update Status",
        description: error.message || "Unknown error occurred",
        variant: "destructive",
      });
    },
  });

  const handleStartMonitor = () => {
    startMonitorMutation.mutate();
  };

  const handleStopMonitor = () => {
    stopMonitorMutation.mutate();
  };

  const handleDeleteEmail = (id: string) => {
    deleteEmailMutation.mutate(id);
  };

  const markEmailCompleted = (id: string) => {
    markCompletedMutation.mutate(id);
  };

  const formatDate = (dateString: string | Date | null) => {
    if (!dateString) return "--";
    return new Date(dateString).toLocaleString();
  };

  const formatTimestamp = (timestamp: Date | null) => {
    if (!timestamp) return "--";
    return new Date(timestamp).toLocaleString();
  };

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case "pending":
        return "default";
      case "replied":
        return "secondary";
      case "completed":
        return "default";
      default:
        return "outline";
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-foreground">Email Monitor</h1>
        <p className="text-muted-foreground mt-2">
          Monitor Gmail for new emails and attachments for LAS file analysis
        </p>
      </div>

      {/* Monitor Status Card */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="w-5 h-5" />
            Email Monitor Status
          </CardTitle>
          <CardDescription>
            Control the email monitoring service and view its current status
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                {monitorStatus?.isRunning ? (
                  <CheckCircle className="w-5 h-5 text-green-500" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-red-500" />
                )}
                <span className="font-medium">
                  {monitorStatus?.isRunning ? "Running" : "Stopped"}
                </span>
              </div>
              
              <div className="text-sm text-muted-foreground">
                Emails Processed: {monitorStatus?.emailsProcessed || "0"}
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                onClick={handleStartMonitor}
                disabled={isStarting || (monitorStatus?.isRunning ?? false)}
                variant="default"
                size="sm"
                data-testid="button-start-monitor"
              >
                {isStarting ? (
                  <>Starting...</>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" />
                    Start
                  </>
                )}
              </Button>
              
              <Button
                onClick={handleStopMonitor}
                disabled={isStopping || !monitorStatus?.isRunning}
                variant="destructive"
                size="sm"
                data-testid="button-stop-monitor"
              >
                {isStopping ? (
                  <>Stopping...</>
                ) : (
                  <>
                    <Square className="w-4 h-4 mr-2" />
                    Stop
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Status Details */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 pt-4 border-t">
            <div>
              <div className="text-sm text-muted-foreground">Last Started</div>
              <div className="font-mono text-sm">
                {formatTimestamp(monitorStatus?.lastStarted || null)}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Last Stopped</div>
              <div className="font-mono text-sm">
                {formatTimestamp(monitorStatus?.lastStopped || null)}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Last Updated</div>
              <div className="font-mono text-sm">
                {formatDate(monitorStatus?.updatedAt || null)}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Status</div>
              <Badge variant={monitorStatus?.isRunning ? "default" : "secondary"}>
                {monitorStatus?.isRunning ? "Active" : "Inactive"}
              </Badge>
            </div>
          </div>

          {monitorStatus?.lastError && (
            <div className="mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
              <div className="text-sm font-medium text-destructive">Last Error:</div>
              <div className="text-sm text-destructive/80 mt-1">
                {monitorStatus.lastError}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Emails List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Email List */}
        <Card>
          <CardHeader>
            <CardTitle>Received Emails ({emails.length})</CardTitle>
            <CardDescription>
              List of emails received from the monitored Gmail account
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
              ) : emails.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Mail className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No emails received yet</p>
                  <p className="text-sm">Start the monitor to begin receiving emails</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {emails.map((email) => (
                    <div
                      key={email.id}
                      className={`p-3 border rounded-lg cursor-pointer transition-colors hover:bg-muted/50 ${
                        selectedEmail?.id === email.id ? "border-primary bg-muted/30" : ""
                      }`}
                      onClick={() => setSelectedEmail(email)}
                      data-testid={`email-item-${email.id}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="font-medium truncate" title={email.subject}>
                            {email.subject}
                          </div>
                          <div className="text-sm text-muted-foreground truncate" title={email.from}>
                            From: {extractEmailAddress(email.from)}
                          </div>
                          <div className="text-xs text-muted-foreground mt-1">
                            {formatDate(email.createdAt)}
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-1">
                          <Badge variant={getStatusBadgeColor(email.replyStatus || "pending")}>
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

        {/* Email Details */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Email Details</span>
              {selectedEmail && (
                <div className="flex gap-2">
                  {selectedEmail.replyStatus !== "completed" && (
                    <Button
                      onClick={() => markEmailCompleted(selectedEmail.id)}
                      variant="outline"
                      size="sm"
                      disabled={markCompletedMutation.isPending}
                      data-testid="button-mark-completed"
                    >
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Mark Completed
                    </Button>
                  )}
                  <Button
                    onClick={() => handleDeleteEmail(selectedEmail.id)}
                    variant="destructive"
                    size="sm"
                    disabled={deleteEmailMutation.isPending}
                    data-testid="button-delete-email"
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete
                  </Button>
                </div>
              )}
            </CardTitle>
            <CardDescription>
              {selectedEmail ? "View email content and attachments" : "Select an email to view details"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!selectedEmail ? (
              <div className="text-center py-8 text-muted-foreground">
                <Clock className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Select an email from the list to view its details</p>
              </div>
            ) : (
              <ScrollArea className="h-[600px]">
                <div className="space-y-4">
                  {/* Email Header */}
                  <div className="space-y-2">
                    <div>
                      <div className="text-sm text-muted-foreground">Subject</div>
                      <div className="font-medium" data-testid="text-email-subject">
                        {selectedEmail.subject}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">From</div>
                      <div className="font-medium" data-testid="text-email-from">
                        {extractEmailAddress(selectedEmail.from)}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Received</div>
                      <div className="font-mono text-sm">
                        {formatDate(selectedEmail.createdAt)}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Status</div>
                      <Badge variant={getStatusBadgeColor(selectedEmail.replyStatus || "pending")}>
                        {selectedEmail.replyStatus}
                      </Badge>
                    </div>
                  </div>

                  <Separator />

                  {/* Email Body */}
                  <div>
                    <div className="text-sm text-muted-foreground mb-2">Message Body</div>
                    <div className="bg-muted/30 p-3 rounded-lg">
                      <pre className="whitespace-pre-wrap text-sm font-mono">
                        {selectedEmail.body || "No message body"}
                      </pre>
                    </div>
                  </div>

                  {/* Attachments */}
                  {selectedEmail.attachments && selectedEmail.attachments.length > 0 && (
                    <>
                      <Separator />
                      <div>
                        <div className="text-sm text-muted-foreground mb-2">
                          Attachments ({selectedEmail.attachments.length})
                        </div>
                        <div className="space-y-2">
                          {selectedEmail.attachments.map((filename, index) => (
                            <div
                              key={index}
                              className="flex items-center justify-between p-2 border rounded-lg"
                              data-testid={`attachment-${filename}`}
                            >
                              <div className="flex items-center gap-2">
                                <Download className="w-4 h-4 text-muted-foreground" />
                                <span className="text-sm font-medium">{filename}</span>
                              </div>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                  window.open(`/api/emails/attachments/${filename}`, '_blank');
                                }}
                                data-testid={`button-download-${filename}`}
                              >
                                Download
                              </Button>
                            </div>
                          ))}
                        </div>
                      </div>
                    </>
                  )}

                  {/* Email JSON Data */}
                  <Separator />
                  <div>
                    <div className="text-sm text-muted-foreground mb-2">Raw JSON Data</div>
                    <div className="bg-muted/30 p-3 rounded-lg">
                      <pre className="text-xs font-mono overflow-x-auto">
                        {JSON.stringify(selectedEmail, null, 2)}
                      </pre>
                    </div>
                  </div>
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}