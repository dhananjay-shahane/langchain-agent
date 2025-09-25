import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";

interface AgentConfig {
  provider: string;
  model: string;
  endpointUrl: string;
  isConnected: boolean;
  lastTested: string | null;
}

export default function AgentConfig() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [localConnectionStatus, setLocalConnectionStatus] = useState(false);

  // Load saved config from localStorage on mount
  useEffect(() => {
    const savedConfig = localStorage.getItem('agentConfig');
    if (savedConfig) {
      try {
        const parsedConfig = JSON.parse(savedConfig);
        if (parsedConfig.provider && parsedConfig.model && parsedConfig.endpointUrl) {
          updateConfigMutation.mutate(parsedConfig);
        }
        setLocalConnectionStatus(parsedConfig.isConnected || false);
      } catch (error) {
        console.error('Error loading saved config:', error);
      }
    }
  }, []);

  const { data: config, isLoading } = useQuery<AgentConfig>({
    queryKey: ["/api/agent/config"],
  });

  const updateConfigMutation = useMutation({
    mutationFn: async (newConfig: Partial<AgentConfig>) => {
      const response = await apiRequest("POST", "/api/agent/config", newConfig);
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["/api/agent/config"] });
      // Save to localStorage
      localStorage.setItem('agentConfig', JSON.stringify(data));
      toast({
        title: "Configuration saved",
        description: "Agent configuration has been updated successfully.",
      });
    },
    onError: () => {
      toast({
        title: "Error",
        description: "Failed to save configuration.",
        variant: "destructive",
      });
    },
  });

  const testConnectionMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest("POST", "/api/agent/test-connection");
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["/api/agent/config"] });
      setLocalConnectionStatus(data.success);
      
      // Update localStorage with connection status
      const savedConfig = localStorage.getItem('agentConfig');
      if (savedConfig) {
        const config = JSON.parse(savedConfig);
        config.isConnected = data.success;
        config.lastTested = new Date().toISOString();
        localStorage.setItem('agentConfig', JSON.stringify(config));
      }
      
      if (data.success) {
        toast({
          title: "Connection successful",
          description: data.message,
        });
      } else {
        toast({
          title: "Connection failed",
          description: data.message,
          variant: "destructive",
        });
      }
    },
    onError: () => {
      toast({
        title: "Error",
        description: "Failed to test connection.",
        variant: "destructive",
      });
    },
  });

  const handleProviderChange = (provider: string) => {
    let defaultModel = "qwen:1.8b";
    let defaultEndpoint = "";

    if (provider === "openai") {
      defaultModel = "gpt-4";
      defaultEndpoint = "https://api.openai.com/v1";
    } else if (provider === "anthropic") {
      defaultModel = "claude-3-sonnet-20240229";
      defaultEndpoint = "https://api.anthropic.com";
    } else if (provider === "ollama") {
      defaultModel = "qwen:1.8b";
      defaultEndpoint = ""; // No hardcoded endpoint - user must configure
    }

    updateConfigMutation.mutate({
      provider,
      model: defaultModel,
      endpointUrl: defaultEndpoint,
    });
  };

  const handleSaveConfig = () => {
    if (!config) return;
    updateConfigMutation.mutate(config);
  };

  const handleTestConnection = async () => {
    setIsTestingConnection(true);
    try {
      await testConnectionMutation.mutateAsync();
    } finally {
      setIsTestingConnection(false);
    }
  };

  const getModelOptions = () => {
    if (!config) return [];
    
    switch (config.provider) {
      case "ollama":
        return ["qwen:1.8b", "llama3.2:1b", "llama3.2:3b", "llama3.1:8b"];
      case "openai":
        return ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"];
      case "anthropic":
        return ["claude-3-sonnet-20240229", "claude-3-opus-20240229", "claude-3-haiku-20240307"];
      default:
        return [];
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 border-b border-border">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-muted rounded w-1/2"></div>
          <div className="h-10 bg-muted rounded"></div>
          <div className="h-10 bg-muted rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 border-b border-border">
      <h2 className="text-lg font-medium text-foreground mb-4">Agent Configuration</h2>
      
      {/* Provider Selection */}
      <div className="mb-4">
        <Label className="block text-sm font-medium text-foreground mb-2">Provider</Label>
        <Select
          value={config?.provider || "ollama"}
          onValueChange={handleProviderChange}
          data-testid="select-provider"
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select provider" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ollama">Ollama (Default)</SelectItem>
            <SelectItem value="openai">OpenAI</SelectItem>
            <SelectItem value="anthropic">Anthropic</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Model Selection */}
      <div className="mb-4">
        <Label className="block text-sm font-medium text-foreground mb-2">Model</Label>
        <Select
          value={config?.model || "qwen:1.8b"}
          onValueChange={(model) => updateConfigMutation.mutate({ model })}
          data-testid="select-model"
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select model" />
          </SelectTrigger>
          <SelectContent>
            {getModelOptions().map((model) => (
              <SelectItem key={model} value={model}>
                {model}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Endpoint URL */}
      <div className="mb-4">
        <Label className="block text-sm font-medium text-foreground mb-2">Endpoint URL</Label>
        <Input
          type="url"
          value={config?.endpointUrl || ""}
          onChange={(e) => updateConfigMutation.mutate({ endpointUrl: e.target.value })}
          placeholder="Enter endpoint URL"
          data-testid="input-endpoint"
        />
      </div>

      {/* Connection Status */}
      <div className="mb-4 p-3 bg-accent/10 rounded-md">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${localConnectionStatus || config?.isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          <span className="text-sm font-medium text-foreground">
            {localConnectionStatus || config?.isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          {localConnectionStatus || config?.isConnected ? 'Agent server responding' : 'Connection not tested'}
        </p>
      </div>

      {/* MCP Server Status */}
      <div className="mb-4">
        <h3 className="text-sm font-medium text-foreground mb-3">MCP Server Status</h3>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Plotting Tools</span>
            <Badge variant="secondary" className="text-xs">Active</Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">LAS Resources</span>
            <Badge variant="secondary" className="text-xs">Ready</Badge>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2">
        <Button
          onClick={handleSaveConfig}
          disabled={updateConfigMutation.isPending}
          className="flex-1"
          data-testid="button-save-config"
        >
          {updateConfigMutation.isPending ? "Saving..." : "Save Config"}
        </Button>
        <Button
          variant="outline"
          onClick={handleTestConnection}
          disabled={isTestingConnection || testConnectionMutation.isPending}
          data-testid="button-test-connection"
        >
          {isTestingConnection ? "Testing..." : "Test"}
        </Button>
      </div>
    </div>
  );
}
