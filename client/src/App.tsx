import { Switch, Route, Link, useLocation } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { MessageSquare, Mail, Bot } from "lucide-react";
import Home from "@/pages/home";
import Emails from "@/pages/emails";
import EmailAgent from "@/pages/email-agent";
import NotFound from "@/pages/not-found";

function Navigation() {
  const [location] = useLocation();

  return (
    <nav className="bg-card border-b border-border p-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-6">
          <h1 className="text-xl font-bold text-foreground">LangChain MCP Agent</h1>
          
          <div className="flex items-center gap-2">
            <Button
              variant={location === "/" ? "default" : "ghost"}
              size="sm"
              asChild
              data-testid="nav-home"
            >
              <Link href="/">
                <MessageSquare className="w-4 h-4 mr-2" />
                Chat Agent
              </Link>
            </Button>
            
            <Button
              variant={location === "/emails" ? "default" : "ghost"}
              size="sm"
              asChild
              data-testid="nav-emails"
            >
              <Link href="/emails">
                <Mail className="w-4 h-4 mr-2" />
                Email Monitor
              </Link>
            </Button>
            
            <Button
              variant={location === "/email-agent" ? "default" : "ghost"}
              size="sm"
              asChild
              data-testid="nav-email-agent"
            >
              <Link href="/email-agent">
                <Bot className="w-4 h-4 mr-2" />
                Email Agent Chat
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </nav>
  );
}

function Router() {
  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      <div className="flex-1">
        <Switch>
          <Route path="/" component={Home} />
          <Route path="/emails" component={Emails} />
          <Route path="/email-agent" component={EmailAgent} />
          <Route component={NotFound} />
        </Switch>
      </div>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Router />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
