import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import { io, Socket } from "socket.io-client";

let socket: Socket | null = null;

export function useSocket() {
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
        description: `${file.filename} added via email`,
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


    // Register event listeners
    socket.on("connect", handleConnect);
    socket.on("disconnect", handleDisconnect);
    socket.on("new_message", handleNewMessage);
    socket.on("agent_response", handleAgentResponse);
    socket.on("config_updated", handleConfigUpdated);
    socket.on("new_las_file", handleNewLasFile);
    socket.on("new_output_file", handleNewOutputFile);
    socket.on("files_updated", handleFilesUpdated);

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
    };
  }, [queryClient, toast]);

  return socket;
}
