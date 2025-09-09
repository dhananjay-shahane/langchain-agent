import { useState, useEffect } from "react";
import AgentConfig from "@/components/agent-config";
import ChatInterface from "@/components/chat-interface";
import FileBrowser from "@/components/file-browser";
import ImageViewer from "@/components/image-viewer";
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
    server: '',
    port: '993',
    username: '',
    password: '',
    folder: 'INBOX'
  });
  const [emailConnected, setEmailConnected] = useState(false);

  // Load email config from localStorage on mount
  useEffect(() => {
    const savedEmailConfig = localStorage.getItem('emailConfig');
    if (savedEmailConfig) {
      try {
        const parsedConfig = JSON.parse(savedEmailConfig);
        setEmailConfig(parsedConfig.config || emailConfig);
        setEmailConnected(parsedConfig.isConnected || false);
      } catch (error) {
        console.error('Error loading saved email config:', error);
      }
    }
  }, []);

  // Save email config to localStorage whenever it changes
  const handleEmailConfigChange = (newConfig: any) => {
    setEmailConfig(newConfig);
    localStorage.setItem('emailConfig', JSON.stringify({
      config: newConfig,
      isConnected: emailConnected,
      lastSaved: new Date().toISOString()
    }));
  };

  const handleEmailTest = () => {
    // Simulate connection test
    const newConnectionStatus = !emailConnected;
    setEmailConnected(newConnectionStatus);
    
    // Update localStorage
    localStorage.setItem('emailConfig', JSON.stringify({
      config: emailConfig,
      isConnected: newConnectionStatus,
      lastTested: new Date().toISOString()
    }));
  };

  const handleSaveEmailConfig = () => {
    localStorage.setItem('emailConfig', JSON.stringify({
      config: emailConfig,
      isConnected: emailConnected,
      lastSaved: new Date().toISOString()
    }));
    console.log('Email configuration saved:', emailConfig);
  };
  useSocket(); // Initialize socket connection

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <div className="w-96 bg-card border-r border-border flex flex-col min-h-0">
        {/* Header */}
        <div className="p-6 border-b border-border">
          <h1 className="text-xl font-semibold text-foreground">LangChain MCP Agent</h1>
          <p className="text-sm text-muted-foreground mt-1">LAS File Processing System</p>
        </div>

        {/* Scrollable Content */}
        <ScrollArea className="flex-1 overflow-y-auto">
          <div className="min-h-0">
            {/* Agent Configuration */}
            <AgentConfig />

            {/* Email Configuration */}
            <div className="p-6 border-b border-border">
            <div className="flex items-center gap-2 mb-4">
              <Mail className="w-5 h-5 text-muted-foreground" />
              <h2 className="text-lg font-medium text-foreground">Email Configuration</h2>
            </div>
            
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="block text-sm font-medium text-foreground mb-1">Server</Label>
                  <Input
                    type="text"
                    value={emailConfig.server}
                    onChange={(e) => handleEmailConfigChange({...emailConfig, server: e.target.value})}
                    placeholder="imap.gmail.com"
                    className="text-sm"
                  />
                </div>
                <div>
                  <Label className="block text-sm font-medium text-foreground mb-1">Port</Label>
                  <Input
                    type="number"
                    value={emailConfig.port}
                    onChange={(e) => handleEmailConfigChange({...emailConfig, port: e.target.value})}
                    placeholder="993"
                    className="text-sm"
                  />
                </div>
              </div>
              
              <div>
                <Label className="block text-sm font-medium text-foreground mb-1">Username/Email</Label>
                <Input
                  type="email"
                  value={emailConfig.username}
                  onChange={(e) => handleEmailConfigChange({...emailConfig, username: e.target.value})}
                  placeholder="your.email@gmail.com"
                  className="text-sm"
                />
              </div>
              
              <div>
                <Label className="block text-sm font-medium text-foreground mb-1">Password/App Password</Label>
                <Input
                  type="password"
                  value={emailConfig.password}
                  onChange={(e) => handleEmailConfigChange({...emailConfig, password: e.target.value})}
                  placeholder="Your app password"
                  className="text-sm"
                />
              </div>
              
              <div>
                <Label className="block text-sm font-medium text-foreground mb-1">Folder</Label>
                <Input
                  type="text"
                  value={emailConfig.folder}
                  onChange={(e) => handleEmailConfigChange({...emailConfig, folder: e.target.value})}
                  placeholder="INBOX"
                  className="text-sm"
                />
              </div>
            </div>

            {/* Connection Status */}
            <div className="mt-4 p-3 bg-accent/10 rounded-md">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${emailConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="text-sm font-medium text-foreground">
                  {emailConnected ? 'Connected' : 'Not Connected'}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {emailConnected ? 'Monitoring for LAS files' : 'Configure email to receive files'}
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2 mt-4">
              <Button 
                onClick={handleSaveEmailConfig}
                className="flex-1"
                size="sm"
              >
                Save Config
              </Button>
              <Button 
                variant="outline"
                onClick={handleEmailTest}
                size="sm"
              >
                Test
              </Button>
            </div>
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
