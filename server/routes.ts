import type { Express } from "express";
import { createServer, type Server } from "http";
import { Server as SocketIOServer } from "socket.io";
import { storage } from "./storage";
import { insertAgentConfigSchema, insertChatMessageSchema, insertLasFileSchema, insertOutputFileSchema, insertEmailSchema } from "@shared/schema";
import { spawn } from "child_process";
import path from "path";
import fs from "fs";
import "./services/file-watcher";

export async function registerRoutes(app: Express): Promise<Server> {
  const httpServer = createServer(app);
  const io = new SocketIOServer(httpServer, {
    cors: {
      origin: "*",
      methods: ["GET", "POST"]
    }
  });

  // Socket.io connection handling
  io.on("connection", (socket) => {
    console.log("Client connected:", socket.id);
    
    socket.on("disconnect", () => {
      console.log("Client disconnected:", socket.id);
    });
  });

  // Make io available globally for other services
  global.io = io;

  // Agent Configuration Routes
  app.get("/api/agent/config", async (req, res) => {
    try {
      const config = await storage.getAgentConfig();
      res.json(config);
    } catch (error) {
      res.status(500).json({ error: "Failed to get agent config" });
    }
  });

  app.post("/api/agent/config", async (req, res) => {
    try {
      const validatedConfig = insertAgentConfigSchema.parse(req.body);
      const config = await storage.updateAgentConfig(validatedConfig);
      
      // Emit config update to all clients
      io.emit("config_updated", config);
      
      res.json(config);
    } catch (error) {
      res.status(400).json({ error: "Invalid config data" });
    }
  });

  app.post("/api/agent/test-connection", async (req, res) => {
    try {
      const config = await storage.getAgentConfig();
      if (!config) {
        return res.status(404).json({ error: "No config found" });
      }

      // Test connection to the agent service
      const testResult = await testAgentConnection(config);
      
      // Update connection status
      await storage.updateAgentConfig({
        ...config,
        isConnected: testResult.success,
      });

      res.json(testResult);
    } catch (error) {
      res.status(500).json({ error: "Connection test failed" });
    }
  });

  // Chat Routes
  app.get("/api/chat/messages", async (req, res) => {
    try {
      const messages = await storage.getChatMessages();
      res.json(messages);
    } catch (error) {
      res.status(500).json({ error: "Failed to get messages" });
    }
  });

  app.post("/api/chat/message", async (req, res) => {
    try {
      const validatedMessage = insertChatMessageSchema.parse(req.body);
      const message = await storage.addChatMessage(validatedMessage);
      
      // Emit new message to all clients
      io.emit("new_message", message);
      
      // If it's a user message, process it with the agent
      if (message.role === "user") {
        const metadata = message.metadata as any;
        processUserMessage(message.content, metadata?.selectedLasFile);
      }
      
      res.json(message);
    } catch (error) {
      res.status(400).json({ error: "Invalid message data" });
    }
  });

  // File Routes
  app.get("/api/files/las", async (req, res) => {
    try {
      const files = await storage.getLasFiles();
      res.json(files);
    } catch (error) {
      res.status(500).json({ error: "Failed to get LAS files" });
    }
  });

  app.post("/api/files/las", async (req, res) => {
    try {
      const validatedFile = insertLasFileSchema.parse(req.body);
      const file = await storage.addLasFile(validatedFile);
      
      // Emit files update to all clients
      io.emit("files_updated");
      io.emit("new_las_file", file);
      
      res.json(file);
    } catch (error) {
      res.status(400).json({ error: "Invalid LAS file data" });
    }
  });

  app.get("/api/files/output", async (req, res) => {
    try {
      const files = await storage.getOutputFiles();
      res.json(files);
    } catch (error) {
      res.status(500).json({ error: "Failed to get output files" });
    }
  });

  app.get("/api/files/output/:filename", async (req, res) => {
    try {
      const filename = req.params.filename;
      const filepath = path.join(process.cwd(), "output", filename);
      
      if (!fs.existsSync(filepath)) {
        return res.status(404).json({ error: "File not found" });
      }
      
      // Check if it's an SVG file disguised as PNG
      if (filename.endsWith('.png')) {
        const content = fs.readFileSync(filepath, 'utf8');
        if (content.startsWith('<?xml') && content.includes('<svg')) {
          res.setHeader('Content-Type', 'image/svg+xml');
          res.send(content);
          return;
        }
      }
      
      res.sendFile(filepath);
    } catch (error) {
      res.status(500).json({ error: "Failed to serve file" });
    }
  });

  // Email Routes
  app.get("/api/emails", async (req, res) => {
    try {
      const emails = await storage.getEmails();
      res.json(emails);
    } catch (error) {
      res.status(500).json({ error: "Failed to get emails" });
    }
  });

  app.post("/api/emails", async (req, res) => {
    try {
      const validatedEmail = insertEmailSchema.parse(req.body);
      const email = await storage.addEmail(validatedEmail);
      
      // Emit new email to all clients
      io.emit("new_email", email);
      
      res.json(email);
    } catch (error) {
      res.status(400).json({ error: "Invalid email data" });
    }
  });

  app.get("/api/email/config", async (req, res) => {
    try {
      // Return only configuration status for security
      const hasCredentials = !!(process.env.EMAIL_USER && process.env.EMAIL_PASSWORD);
      res.json({
        isConfigured: hasCredentials
      });
    } catch (error) {
      res.status(500).json({ error: "Failed to get email config" });
    }
  });

  app.post("/api/email/monitor/start", async (req, res) => {
    try {
      // Check if credentials are configured
      if (!process.env.EMAIL_USER || !process.env.EMAIL_PASSWORD) {
        return res.status(400).json({ error: "Email credentials not configured" });
      }
      
      // Check if already running
      const { exec } = require("child_process");
      exec("pgrep -f email_monitor.py", (error, stdout, stderr) => {
        if (stdout.trim()) {
          return res.json({ 
            message: "Email monitoring already running",
            status: "running"
          });
        }
        
        // Start email monitoring workflow
        const { spawn } = require("child_process");
        const monitor = spawn("uv", [
          "run", 
          "python", 
          path.join(process.cwd(), "scripts/email_monitor.py")
        ], {
          detached: true,
          stdio: ['ignore', 'ignore', 'ignore']
        });
        
        monitor.on('error', (err) => {
          console.error('Failed to start email monitor:', err);
        });
        
        monitor.unref();
        
        res.json({ 
          message: "Email monitoring started",
          status: "running"
        });
      });
      
    } catch (error) {
      console.error('Email monitor start error:', error);
      res.status(500).json({ error: "Failed to start email monitoring" });
    }
  });

  app.post("/api/email/monitor/stop", async (req, res) => {
    try {
      // Kill email monitoring processes
      const { exec } = require("child_process");
      exec("pkill -f email_monitor.py", (error) => {
        if (error && error.code !== 1) {
          // Code 1 means no process found, which is fine
          console.error("Error stopping email monitor:", error);
        }
      });
      
      res.json({ 
        message: "Email monitoring stopped",
        status: "stopped"
      });
    } catch (error) {
      res.status(500).json({ error: "Failed to stop email monitoring" });
    }
  });

  app.get("/api/email/monitor/status", async (req, res) => {
    try {
      const { exec } = require("child_process");
      exec("pgrep -f email_monitor.py", (error, stdout, stderr) => {
        const isRunning = stdout.trim() !== "";
        res.json({
          running: isRunning,
          message: isRunning ? "Email monitoring is running" : "Email monitoring is stopped"
        });
      });
    } catch (error) {
      res.status(500).json({ error: "Failed to check monitoring status" });
    }
  });

  return httpServer;
}

async function testAgentConnection(config: any): Promise<{ success: boolean; message: string }> {
  return new Promise((resolve) => {
    const python = spawn("uv", [
      "run",
      "python", 
      path.join(process.cwd(), "server/services/langchain-agent.py"),
      "test",
      config.provider,
      config.model,
      config.endpointUrl
    ]);

    let output = "";
    python.stdout.on("data", (data) => {
      output += data.toString();
    });

    python.on("close", (code) => {
      if (code === 0) {
        resolve({ success: true, message: "Connection successful" });
      } else {
        resolve({ success: false, message: output || "Connection failed" });
      }
    });

    setTimeout(() => {
      python.kill();
      resolve({ success: false, message: "Connection timeout" });
    }, 3000); // Reduced to 3 seconds
  });
}

async function processUserMessage(content: string, selectedLasFile?: string) {
  try {
    // Add agent thinking message
    const thinkingMessage = await storage.addChatMessage({
      role: "agent",
      content: "Processing your request...",
      metadata: { thinking: true }
    });
    
    global.io?.emit("new_message", thinkingMessage);

    // Call the LangChain agent
    const config = await storage.getAgentConfig();
    const python = spawn("uv", [
      "run",
      "python", 
      path.join(process.cwd(), "server/services/langchain-agent.py"),
      "process",
      content,
      selectedLasFile || "",
      JSON.stringify(config)
    ]);

    let output = "";
    python.stdout.on("data", (data) => {
      output += data.toString();
    });

    python.on("close", async (code) => {
      try {
        const response = JSON.parse(output);
        
        // Remove thinking message and add real response
        const agentMessage = await storage.addChatMessage({
          role: "agent",
          content: response.content,
          metadata: response.metadata || {}
        });
        
        global.io?.emit("agent_response", agentMessage);
        
        // If files were generated, update file lists
        if (response.generated_files) {
          for (const file of response.generated_files) {
            await storage.addOutputFile({
              filename: file.filename,
              filepath: file.filepath,
              type: file.type,
              relatedLasFile: file.relatedLasFile
            });
          }
          global.io?.emit("files_updated");
        }
      } catch (error) {
        const errorMessage = await storage.addChatMessage({
          role: "agent",
          content: "I encountered an error processing your request. Please try again.",
          metadata: { error: true }
        });
        
        global.io?.emit("new_message", errorMessage);
      }
    });
  } catch (error) {
    console.error("Error processing user message:", error);
  }
}

// Global declaration for TypeScript
declare global {
  var io: SocketIOServer | undefined;
}
