import { useState } from "react";
import AgentConfig from "@/components/agent-config";
import ChatInterface from "@/components/chat-interface";
import FileBrowser from "@/components/file-browser";
import ImageViewer from "@/components/image-viewer";
import { useSocket } from "@/hooks/use-socket";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Link } from "wouter";
import { Mail } from "lucide-react";

export default function Home() {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  
  useSocket(); // Initialize socket connection

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <div className="w-100 bg-card border-r border-border flex flex-col min-h-0 overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-border">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-foreground">
                LangChain MCP Agent
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                LAS File Processing System
              </p>
            </div>
          </div>
          
          {/* Navigation */}
          <div className="mt-4 space-y-2">
            <Link href="/emails">
              <Button variant="outline" className="w-full justify-start" data-testid="button-nav-emails">
                <Mail className="w-4 h-4 mr-2" />
                Email Monitor
              </Button>
            </Link>
          </div>
        </div>

        {/* Scrollable Content */}
        <ScrollArea className="flex-1 h-0">
          <div className="min-h-0">
            {/* Agent Configuration */}
            <AgentConfig />

            {/* File Browser */}
            <FileBrowser onImageSelect={setSelectedImage} />
          </div>
        </ScrollArea>
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
