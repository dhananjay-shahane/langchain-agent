import { useState, useEffect } from "react";
import AgentConfig from "@/components/agent-config";
import ChatInterface from "@/components/chat-interface";
import FileBrowser from "@/components/file-browser";
import ImageViewer from "@/components/image-viewer";
import EmailNotifications from "@/components/email-notifications";
import { useSocket } from "@/hooks/use-socket";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Mail, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

export default function Home() {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [emailConfig, setEmailConfig] = useState({
    server: "",
    port: "993",
    username: "",
    password: "",
    folder: "INBOX",
  });
  const [emailConnected, setEmailConnected] = useState(false);

  // Load email config from localStorage on mount
  useEffect(() => {
    const savedEmailConfig = localStorage.getItem("emailConfig");
    if (savedEmailConfig) {
      try {
        const parsedConfig = JSON.parse(savedEmailConfig);
        setEmailConfig(parsedConfig.config || emailConfig);
        setEmailConnected(parsedConfig.isConnected || false);
      } catch (error) {
        console.error("Error loading saved email config:", error);
      }
    }
  }, []);

  // Save email config to localStorage whenever it changes
  const handleEmailConfigChange = (newConfig: any) => {
    setEmailConfig(newConfig);
    localStorage.setItem(
      "emailConfig",
      JSON.stringify({
        config: newConfig,
        isConnected: emailConnected,
        lastSaved: new Date().toISOString(),
      }),
    );
  };

  const handleEmailTest = async () => {
    try {
      const response = await fetch("/api/email/test", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: emailConfig.username,
          password: emailConfig.password,
        }),
      });

      const result = await response.json();
      setEmailConnected(result.success);

      // Update localStorage
      localStorage.setItem(
        "emailConfig",
        JSON.stringify({
          config: emailConfig,
          isConnected: result.success,
          lastTested: new Date().toISOString(),
          message: result.message,
        }),
      );

      // Show result to user
      alert(result.success ? `✅ ${result.message}` : `❌ ${result.message}`);
    } catch (error) {
      console.error("Email test failed:", error);
      setEmailConnected(false);
      alert("❌ Email test failed: Connection error");
    }
  };

  const handleSaveEmailConfig = () => {
    localStorage.setItem(
      "emailConfig",
      JSON.stringify({
        config: emailConfig,
        isConnected: emailConnected,
        lastSaved: new Date().toISOString(),
      }),
    );
    console.log("Email configuration saved:", emailConfig);
  };
  useSocket(); // Initialize socket connection

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <div className="w-100 bg-card border-r border-border flex flex-col min-h-0 overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-border">
          <h1 className="text-xl font-semibold text-foreground">
            LangChain MCP Agent
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            LAS File Processing System
          </p>
        </div>

        {/* Scrollable Content */}
        <ScrollArea className="flex-1 h-0">
          <div className="min-h-0">
            {/* Agent Configuration */}
            <AgentConfig />

            {/* Email Configuration */}
            <div className="p-4 border-b border-border">
              <div className="flex items-center gap-2 mb-3">
                <Mail className="w-4 h-4 text-muted-foreground" />
                <h2 className="text-base font-medium text-foreground">
                  Email (IMAP/SMTP)
                </h2>
              </div>

              <div className="space-y-3">
                <div>
                  <Label className="block text-xs font-medium text-foreground mb-1">
                    Email Address
                  </Label>
                  <Input
                    type="email"
                    value={emailConfig.username}
                    onChange={(e) =>
                      handleEmailConfigChange({
                        ...emailConfig,
                        username: e.target.value,
                      })
                    }
                    placeholder="your.email@gmail.com"
                    className="text-xs h-8"
                  />
                </div>

                <div>
                  <Label className="block text-xs font-medium text-foreground mb-1">
                    App Password
                  </Label>
                  <Input
                    type="password"
                    value={emailConfig.password}
                    onChange={(e) =>
                      handleEmailConfigChange({
                        ...emailConfig,
                        password: e.target.value,
                      })
                    }
                    placeholder="App-specific password"
                    className="text-xs h-8"
                  />
                </div>
              </div>

              {/* Connection Status */}
              <div className="mt-3 p-2 bg-accent/10 rounded-md">
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${emailConnected ? "bg-green-500" : "bg-red-500"}`}
                  ></div>
                  <span className="text-xs font-medium text-foreground">
                    {emailConnected ? "Connected" : "Not Connected"}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {emailConnected
                    ? "IMAP & SMTP ready"
                    : "Auto-detects email provider"}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2 mt-3">
                <Button
                  onClick={handleEmailTest}
                  className="flex-1 h-7"
                  size="sm"
                >
                  Test Email
                </Button>
              </div>
            </div>

            {/* Email Notifications */}
            <div className="p-4 border-b border-border">
              <EmailNotifications />
            </div>

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
