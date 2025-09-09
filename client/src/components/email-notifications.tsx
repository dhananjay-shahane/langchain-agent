import React, { useState, useEffect } from "react";
import { useSocket } from "@/hooks/use-socket";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { Mail, MailOpen, FileText, Clock, User, ExternalLink, AlertCircle } from "lucide-react";

interface Email {
  id: string;
  uid: string;
  sender: string;
  subject: string;
  content?: string;
  hasAttachments: boolean;
  processed: boolean;
  autoProcessed: boolean;
  relatedLasFiles: string[];
  relatedOutputFiles: string[];
  replyEmailSent: boolean;
  receivedAt: string;
}

interface EmailNotificationsProps {
  onEmailReceived?: (email: any) => void;
}

export default function EmailNotifications({ onEmailReceived }: EmailNotificationsProps) {
  const [notifications, setNotifications] = useState<any[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const { toast } = useToast();
  const socket = useSocket();

  // Query for recent emails
  const { data: emailsData, refetch: refetchEmails } = useQuery<{totalEmails: number, emails: Email[]}>({
    queryKey: ['/api/emails/received'],
    queryFn: async () => {
      const response = await fetch('/api/emails/received?limit=20');
      return response.json();
    },
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  const emails = emailsData?.emails || [];
  const totalEmails = emailsData?.totalEmails || 0;

  // Socket listeners for real-time email notifications
  useEffect(() => {
    if (!socket) return;

    const handleNewEmail = (emailData: any) => {
      console.log("📧 New email received:", emailData);
      
      // Show toast notification
      toast({
        title: "📧 New Email Received",
        description: `From: ${emailData.sender}\nSubject: ${emailData.subject}`,
        action: (
          <div className="flex items-center gap-2">
            {emailData.hasAttachments && (
              <Badge variant="secondary" className="text-xs">
                <FileText className="w-3 h-3 mr-1" />
                Attachments
              </Badge>
            )}
          </div>
        ),
      });

      // Add to notifications
      const notification = {
        id: emailData.id,
        type: 'email',
        message: `New email from ${emailData.sender}`,
        timestamp: new Date(),
        read: false,
        data: emailData
      };

      setNotifications(prev => [notification, ...prev.slice(0, 9)]); // Keep last 10
      setUnreadCount(prev => prev + 1);
      
      // Trigger callback if provided
      if (onEmailReceived) {
        onEmailReceived(emailData);
      }

      // Refetch emails to update the list
      refetchEmails();
    };

    const handleEmailUpdated = (emailData: any) => {
      console.log("📧 Email updated:", emailData);
      
      if (emailData.autoProcessed && emailData.replyEmailSent) {
        toast({
          title: "✅ Email Processed",
          description: `Analysis complete for ${emailData.sender}`,
          action: (
            <Badge variant="default" className="bg-green-500">
              Auto-replied
            </Badge>
          ),
        });
      }

      refetchEmails();
    };

    socket.on('new_email', handleNewEmail);
    socket.on('email_updated', handleEmailUpdated);

    return () => {
      socket.off('new_email', handleNewEmail);
      socket.off('email_updated', handleEmailUpdated);
    };
  }, [socket, toast, onEmailReceived, refetchEmails]);

  const markNotificationRead = (notificationId: string) => {
    setNotifications(prev => 
      prev.map(n => 
        n.id === notificationId ? { ...n, read: true } : n
      )
    );
    setUnreadCount(prev => Math.max(0, prev - 1));
  };

  const clearAllNotifications = () => {
    setNotifications([]);
    setUnreadCount(0);
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="space-y-4">
      {/* Email Status Header */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <Mail className="w-4 h-4" />
              Email Monitor
              {unreadCount > 0 && (
                <Badge variant="destructive" className="text-xs px-1.5 py-0.5 min-w-[20px] h-5">
                  {unreadCount}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              Active
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0 pb-4">
          <div className="flex justify-between items-center text-sm">
            <span className="text-muted-foreground">
              Total emails: <strong>{totalEmails}</strong>
            </span>
            {notifications.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearAllNotifications}
                className="text-xs h-7"
              >
                Clear all
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Recent Notifications */}
      {notifications.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              Recent Notifications
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <ScrollArea className="max-h-48">
              <div className="space-y-2">
                {notifications.slice(0, 5).map((notification, index) => (
                  <div key={notification.id} className="space-y-2">
                    <div 
                      className={`flex items-start gap-3 p-2 rounded-lg cursor-pointer transition-colors ${
                        notification.read 
                          ? 'bg-muted/30 text-muted-foreground' 
                          : 'bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/30'
                      }`}
                      onClick={() => markNotificationRead(notification.id)}
                    >
                      <div className="mt-0.5">
                        {notification.read ? (
                          <MailOpen className="w-3 h-3" />
                        ) : (
                          <Mail className="w-3 h-3 text-blue-500" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {notification.message}
                        </p>
                        {notification.data && (
                          <p className="text-xs text-muted-foreground truncate">
                            Subject: {notification.data.subject}
                          </p>
                        )}
                        <p className="text-xs text-muted-foreground">
                          {formatTimeAgo(notification.timestamp.toISOString())}
                        </p>
                      </div>
                    </div>
                    {index < notifications.slice(0, 5).length - 1 && (
                      <Separator />
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {/* Recent Emails List */}
      {emails.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4" />
                Recent Emails ({emails.length})
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetchEmails()}
                className="h-7 text-xs"
              >
                Refresh
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <ScrollArea className="max-h-64">
              <div className="space-y-2">
                {emails.slice(0, 10).map((email, index) => (
                  <div key={email.id} className="space-y-2">
                    <div className="p-3 border rounded-lg hover:bg-muted/50 transition-colors">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <User className="w-3 h-3 text-muted-foreground" />
                            <p className="text-sm font-medium truncate">
                              {email.sender}
                            </p>
                            {email.hasAttachments && (
                              <Badge variant="secondary" className="text-xs px-1.5 py-0.5">
                                <FileText className="w-3 h-3 mr-1" />
                                {email.relatedLasFiles.length}
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground truncate mb-1">
                            {email.subject}
                          </p>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Clock className="w-3 h-3" />
                            {formatTimeAgo(email.receivedAt)}
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-1">
                          {email.autoProcessed && (
                            <Badge variant="default" className="text-xs bg-green-500">
                              Auto-processed
                            </Badge>
                          )}
                          {email.replyEmailSent && (
                            <Badge variant="outline" className="text-xs">
                              Replied
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                    {index < emails.slice(0, 10).length - 1 && (
                      <Separator />
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {/* No emails message */}
      {totalEmails === 0 && (
        <Card>
          <CardContent className="pt-6 pb-6 text-center">
            <Mail className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">
              No emails received yet. The monitor is active and waiting for new messages.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}