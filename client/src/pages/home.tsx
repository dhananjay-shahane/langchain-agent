import { useState } from "react";
import AgentConfig from "@/components/agent-config";
import ChatInterface from "@/components/chat-interface";
import FileBrowser from "@/components/file-browser";
import ImageViewer from "@/components/image-viewer";
import { useSocket } from "@/hooks/use-socket";

export default function Home() {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  useSocket(); // Initialize socket connection

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <div className="w-96 bg-card border-r border-border flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-border">
          <h1 className="text-xl font-semibold text-foreground">LangChain MCP Agent</h1>
          <p className="text-sm text-muted-foreground mt-1">LAS File Processing System</p>
        </div>

        {/* Agent Configuration */}
        <AgentConfig />

        {/* File Browser */}
        <FileBrowser onImageSelect={setSelectedImage} />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <ChatInterface />
      </div>

      {/* Image Viewer Modal */}
      {selectedImage && (
        <ImageViewer
          imageSrc={selectedImage}
          onClose={() => setSelectedImage(null)}
        />
      )}
    </div>
  );
}
