import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import { io, Socket } from "socket.io-client";

let socket: Socket | null = null;

interface SocketEventHandlers {
  onNewEmail?: (email: any) => void;
  onEmailDeleted?: (data: { id: string }) => void;
  onEmailMonitorStatus?: (status: any) => void;
  onAutoProcessingStarted?: (data: { totalEmails: number }) => void;
  onProcessingEmail?: (data: { emailId: string; step: number; total: number; subject: string }) => void;
  onResponseGenerated?: (data: { emailId: string; response: string }) => void;
  onReplySent?: (data: { emailId: string; toEmail: string; subject: string }) => void;
  onEmailStatusUpdated?: (data: { emailId: string; status: string }) => void;
  onAutoProcessingCompleted?: (data: { processed: number; errors: number; results: any[] }) => void;
  onAutoProcessingError?: (data: { error: string }) => void;
}

export function useSocket(handlers: SocketEventHandlers = {}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  useEffect(() => {
    // Initialize socket connection
    if (!socket) {
      socket = io(window.location.origin, {
        transports: ['websocket', 'polling']
      });
    }

    const handleConnect = () => {
      console.log("Connected to server");
    };

    const handleDisconnect = () => {
      console.log("Disconnected from server");
    };

    const handleNewMessage = (message: any) => {
      queryClient.invalidateQueries({ queryKey: ["/api/chat/messages"] });
    };

    const handleAgentResponse = (message: any) => {
      queryClient.invalidateQueries({ queryKey: ["/api/chat/messages"] });
      
      if (message.metadata?.generated_file) {
        queryClient.invalidateQueries({ queryKey: ["/api/files/output"] });
      }
    };

    const handleConfigUpdated = (config: any) => {
      queryClient.invalidateQueries({ queryKey: ["/api/agent/config"] });
      toast({
        title: "Configuration updated",
        description: "Agent configuration has been synchronized.",
      });
    };

    const handleNewLasFile = (file: any) => {
      queryClient.invalidateQueries({ queryKey: ["/api/files/las"] });
      toast({
        title: "New LAS file received",
        description: `${file.filename} detected in data folder`,
      });
    };

    const handleNewOutputFile = (file: any) => {
      queryClient.invalidateQueries({ queryKey: ["/api/files/output"] });
      toast({
        title: "Output file generated",
        description: `${file.filename} has been created`,
      });
    };

    const handleFilesUpdated = () => {
      queryClient.invalidateQueries({ queryKey: ["/api/files/las"] });
      queryClient.invalidateQueries({ queryKey: ["/api/files/output"] });
    };

    const handleNewEmail = (email: any) => {
      if (handlers.onNewEmail) {
        handlers.onNewEmail(email);
      } else {
        queryClient.invalidateQueries({ queryKey: ["/api/emails"] });
        toast({
          title: "📧 New Email Received",
          description: `From: ${email.from}`,
        });
      }
    };

    const handleEmailDeleted = (data: { id: string }) => {
      if (handlers.onEmailDeleted) {
        handlers.onEmailDeleted(data);
      } else {
        queryClient.invalidateQueries({ queryKey: ["/api/emails"] });
      }
    };

    const handleEmailMonitorStatus = (status: any) => {
      if (handlers.onEmailMonitorStatus) {
        handlers.onEmailMonitorStatus(status);
      } else {
        queryClient.setQueryData(["/api/emails/monitor/status"], status);
      }
    };

    // Auto-processing event handlers
    const handleAutoProcessingStarted = (data: { totalEmails: number }) => {
      if (handlers.onAutoProcessingStarted) {
        handlers.onAutoProcessingStarted(data);
      } else {
        toast({
          title: "🚀 Auto-Processing Started",
          description: `Processing ${data.totalEmails} pending email(s)`,
        });
      }
    };

    const handleProcessingEmail = (data: { emailId: string; step: number; total: number; subject: string }) => {
      if (handlers.onProcessingEmail) {
        handlers.onProcessingEmail(data);
      }
      // Note: Individual email processing notifications are handled by the component
    };

    const handleResponseGenerated = (data: { emailId: string; response: string }) => {
      if (handlers.onResponseGenerated) {
        handlers.onResponseGenerated(data);
      }
      // Note: Response generation notifications are handled by the component
    };

    const handleReplySent = (data: { emailId: string; toEmail: string; subject: string }) => {
      if (handlers.onReplySent) {
        handlers.onReplySent(data);
      }
      // Note: Reply sent notifications are handled by the component
    };

    const handleEmailStatusUpdated = (data: { emailId: string; status: string }) => {
      if (handlers.onEmailStatusUpdated) {
        handlers.onEmailStatusUpdated(data);
      } else {
        queryClient.invalidateQueries({ queryKey: ["/api/emails"] });
      }
    };

    const handleAutoProcessingCompleted = (data: { processed: number; errors: number; results: any[] }) => {
      if (handlers.onAutoProcessingCompleted) {
        handlers.onAutoProcessingCompleted(data);
      } else {
        queryClient.invalidateQueries({ queryKey: ["/api/emails"] });
        toast({
          title: "✅ Auto-Processing Completed",
          description: `Processed ${data.processed} emails${data.errors > 0 ? ` (${data.errors} errors)` : ''}`,
        });
      }
    };

    const handleAutoProcessingError = (data: { error: string }) => {
      if (handlers.onAutoProcessingError) {
        handlers.onAutoProcessingError(data);
      } else {
        toast({
          title: "❌ Auto-Processing Error",
          description: data.error,
          variant: "destructive",
        });
      }
    };


    // Register event listeners
    socket.on("connect", handleConnect);
    socket.on("disconnect", handleDisconnect);
    socket.on("new_message", handleNewMessage);
    socket.on("agent_response", handleAgentResponse);
    socket.on("config_updated", handleConfigUpdated);
    socket.on("new_las_file", handleNewLasFile);
    socket.on("new_output_file", handleNewOutputFile);
    socket.on("files_updated", handleFilesUpdated);
    socket.on("new_email", handleNewEmail);
    socket.on("email_deleted", handleEmailDeleted);
    socket.on("email_monitor_status", handleEmailMonitorStatus);
    
    // Auto-processing event listeners
    socket.on("auto_processing_started", handleAutoProcessingStarted);
    socket.on("processing_email", handleProcessingEmail);
    socket.on("response_generated", handleResponseGenerated);
    socket.on("reply_sent", handleReplySent);
    socket.on("email_status_updated", handleEmailStatusUpdated);
    socket.on("auto_processing_completed", handleAutoProcessingCompleted);
    socket.on("auto_processing_error", handleAutoProcessingError);

    return () => {
      // Clean up listeners but keep connection alive
      socket?.off("connect", handleConnect);
      socket?.off("disconnect", handleDisconnect);
      socket?.off("new_message", handleNewMessage);
      socket?.off("agent_response", handleAgentResponse);
      socket?.off("config_updated", handleConfigUpdated);
      socket?.off("new_las_file", handleNewLasFile);
      socket?.off("new_output_file", handleNewOutputFile);
      socket?.off("files_updated", handleFilesUpdated);
      socket?.off("new_email", handleNewEmail);
      socket?.off("email_deleted", handleEmailDeleted);
      socket?.off("email_monitor_status", handleEmailMonitorStatus);
      
      // Auto-processing event listener cleanup
      socket?.off("auto_processing_started", handleAutoProcessingStarted);
      socket?.off("processing_email", handleProcessingEmail);
      socket?.off("response_generated", handleResponseGenerated);
      socket?.off("reply_sent", handleReplySent);
      socket?.off("email_status_updated", handleEmailStatusUpdated);
      socket?.off("auto_processing_completed", handleAutoProcessingCompleted);
      socket?.off("auto_processing_error", handleAutoProcessingError);
    };
  }, [queryClient, toast]);

  return socket;
}
