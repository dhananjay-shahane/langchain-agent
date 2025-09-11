import type { Express } from "express";
import { createServer, type Server } from "http";
import { Server as SocketIOServer } from "socket.io";
import { storage } from "./storage";
import { insertAgentConfigSchema, insertChatMessageSchema, insertLasFileSchema, insertOutputFileSchema, insertEmailSchema } from "@shared/schema";
import { spawn, exec } from "child_process";
import path from "path";
import fs from "fs";
import "./services/file-watcher";

// Simple rate limiting for email monitor endpoints
interface RateLimitEntry {
  count: number;
  resetTime: number;
}

const rateLimitMap = new Map<string, RateLimitEntry>();
const RATE_LIMIT_WINDOW = 60 * 1000; // 1 minute
const RATE_LIMIT_MAX_REQUESTS = 10; // 10 requests per minute

function checkRateLimit(ip: string): boolean {
  const now = Date.now();
  const entry = rateLimitMap.get(ip);
  
  if (!entry || now > entry.resetTime) {
    rateLimitMap.set(ip, { count: 1, resetTime: now + RATE_LIMIT_WINDOW });
    return true;
  }
  
  if (entry.count >= RATE_LIMIT_MAX_REQUESTS) {
    return false;
  }
  
  entry.count++;
  return true;
}

function rateLimitMiddleware(req: any, res: any, next: any) {
  const clientIp = req.ip || req.connection?.remoteAddress || 'unknown';
  
  if (!checkRateLimit(clientIp)) {
    return res.status(429).json({ 
      error: "Too many requests. Please try again later.",
      retryAfter: Math.ceil(RATE_LIMIT_WINDOW / 1000)
    });
  }
  
  next();
}

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
      
      // Security: Validate filename to prevent path traversal
      if (!filename || filename.includes('..') || filename.includes('/') || filename.includes('\\')) {
        return res.status(400).json({ error: "Invalid filename" });
      }
      
      // Security: Only allow specific file extensions
      const allowedExtensions = ['.png', '.jpg', '.jpeg', '.svg', '.txt', '.json', '.pdf'];
      const hasValidExtension = allowedExtensions.some(ext => filename.toLowerCase().endsWith(ext));
      if (!hasValidExtension) {
        return res.status(400).json({ error: "File type not allowed" });
      }
      
      const outputDir = path.join(process.cwd(), "output");
      const filepath = path.join(outputDir, filename);
      
      // Security: Ensure the resolved path is within the output directory
      const resolvedPath = path.resolve(filepath);
      const resolvedOutputDir = path.resolve(outputDir);
      if (!resolvedPath.startsWith(resolvedOutputDir + path.sep) && resolvedPath !== resolvedOutputDir) {
        return res.status(403).json({ error: "Access denied" });
      }
      
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
      console.error("File serving error:", error);
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
      console.error("Email validation error:", error);
      console.error("Request body:", req.body);
      if (error instanceof Error && 'issues' in error) {
        console.error("Validation issues:", (error as any).issues);
      }
      res.status(400).json({ error: "Invalid email data", details: error instanceof Error ? error.message : "Unknown error" });
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

  app.post("/api/email/monitor/start", rateLimitMiddleware, async (req, res) => {
    try {
      // Check if credentials are configured
      if (!process.env.EMAIL_USER || !process.env.EMAIL_PASSWORD) {
        return res.status(400).json({ error: "Email credentials not configured" });
      }
      
      // Check if already running
      exec("pgrep -f email_monitor.py", { timeout: 5000 }, (error: any, stdout: string, stderr: string) => {
        if (error && error.code !== 1 && !error.killed) {
          console.error("Process check error:", error);
          return res.status(500).json({ error: "Failed to check current status" });
        }
        
        if (stdout && stdout.trim()) {
          return res.json({ 
            message: "Email monitoring already running",
            status: "running"
          });
        }
        
        // Start email monitoring workflow
        const scriptPath = path.join(process.cwd(), "scripts/email_monitor.py");
        
        // Security: Validate script path exists and is within expected directory
        if (!fs.existsSync(scriptPath)) {
          return res.status(500).json({ error: "Email monitor script not found" });
        }
        
        const monitor = spawn("uv", [
          "run", 
          "python", 
          scriptPath
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

  app.post("/api/email/monitor/stop", rateLimitMiddleware, async (req, res) => {
    try {
      // Kill email monitoring processes
      exec("pkill -f email_monitor.py", { timeout: 5000 }, (error: any, stdout: string, stderr: string) => {
        if (error && error.code !== 1 && !error.killed) {
          // Code 1 means no process found, which is fine
          console.error("Error stopping email monitor:", error);
          return res.status(500).json({ error: "Failed to stop email monitoring" });
        }
        
        res.json({ 
          message: "Email monitoring stopped",
          status: "stopped"
        });
      });
    } catch (error) {
      console.error('Email monitor stop error:', error);
      res.status(500).json({ error: "Failed to stop email monitoring" });
    }
  });

  app.get("/api/email/monitor/status", rateLimitMiddleware, async (req, res) => {
    try {
      exec("pgrep -f email_monitor.py", { timeout: 5000 }, (error: any, stdout: string, stderr: string) => {
        if (error && error.code !== 1 && !error.killed) {
          console.error("Process check error:", error);
          return res.status(500).json({ error: "Failed to check monitoring status" });
        }
        
        const isRunning = stdout && stdout.trim() !== "";
        res.json({
          running: isRunning,
          message: isRunning ? "Email monitoring is running" : "Email monitoring is stopped"
        });
      });
    } catch (error) {
      console.error("Status check error:", error);
      res.status(500).json({ error: "Failed to check monitoring status" });
    }
  });

  return httpServer;
}

async function testAgentConnection(config: any): Promise<{ success: boolean; message: string }> {
  return new Promise((resolve) => {
    // Security: Validate config parameters to prevent command injection
    if (!config || typeof config.provider !== 'string' || typeof config.model !== 'string') {
      resolve({ success: false, message: "Invalid configuration parameters" });
      return;
    }
    
    // Security: Sanitize string inputs to prevent command injection
    const safeProvider = config.provider.replace(/[^a-zA-Z0-9_-]/g, '');
    const safeModel = config.model.replace(/[^a-zA-Z0-9_.-]/g, '');
    const safeEndpointUrl = config.endpointUrl || '';
    
    const scriptPath = path.join(process.cwd(), "server/services/langchain-agent.py");
    
    // Security: Verify script exists
    if (!fs.existsSync(scriptPath)) {
      resolve({ success: false, message: "Agent script not found" });
      return;
    }
    
    const python = spawn("uv", [
      "run",
      "python", 
      scriptPath,
      "test",
      safeProvider,
      safeModel,
      safeEndpointUrl
    ]);

    let output = "";
    python.stdout.on("data", (data) => {
      output += data.toString();
    });

    python.stderr.on("data", (data) => {
      console.error("Agent test error:", data.toString());
    });

    python.on("close", (code) => {
      if (code === 0) {
        resolve({ success: true, message: "Connection successful" });
      } else {
        resolve({ success: false, message: output || "Connection failed" });
      }
    });

    python.on('error', (err) => {
      console.error('Spawn error:', err);
      resolve({ success: false, message: "Failed to start connection test" });
    });

    setTimeout(() => {
      python.kill();
      resolve({ success: false, message: "Connection timeout" });
    }, 3000);
  });
}

async function processUserMessage(content: string, selectedLasFile?: string) {
  try {
    // Security: Validate and sanitize inputs
    if (typeof content !== 'string' || content.length > 10000) {
      console.error("Invalid message content");
      return;
    }
    
    // Add agent thinking message
    const thinkingMessage = await storage.addChatMessage({
      role: "agent",
      content: "Processing your request...",
      metadata: { thinking: true }
    });
    
    global.io?.emit("new_message", thinkingMessage);

    // Call the LangChain agent
    const config = await storage.getAgentConfig();
    const scriptPath = path.join(process.cwd(), "server/services/langchain-agent.py");
    
    // Security: Verify script exists
    if (!fs.existsSync(scriptPath)) {
      throw new Error("Agent script not found");
    }
    
    // Security: Sanitize selectedLasFile path
    let safeLasFile = "";
    if (selectedLasFile) {
      // Only allow filenames without path traversal
      if (!selectedLasFile.includes('..') && !selectedLasFile.includes('/') && !selectedLasFile.includes('\\')) {
        safeLasFile = selectedLasFile;
      }
    }
    
    const python = spawn("uv", [
      "run",
      "python", 
      scriptPath,
      "process",
      content,
      safeLasFile,
      JSON.stringify(config)
    ]);

    let output = "";
    python.stdout.on("data", (data) => {
      output += data.toString();
    });

    python.stderr.on("data", (data) => {
      console.error("Agent process error:", data.toString());
    });

    python.on("close", async (code) => {
      try {
        if (!output.trim()) {
          throw new Error("No response from agent");
        }
        
        const response = JSON.parse(output);
        
        // Security: Validate response structure
        if (typeof response.content !== 'string') {
          throw new Error("Invalid response format");
        }
        
        // Remove thinking message and add real response
        const agentMessage = await storage.addChatMessage({
          role: "agent",
          content: response.content,
          metadata: response.metadata || {}
        });
        
        global.io?.emit("agent_response", agentMessage);
        
        // If files were generated, update file lists
        if (response.generated_files && Array.isArray(response.generated_files)) {
          for (const file of response.generated_files) {
            // Security: Validate file paths are within output directory
            if (file.filename && typeof file.filename === 'string' && 
                !file.filename.includes('..') && !file.filename.includes('/')) {
              await storage.addOutputFile({
                filename: file.filename,
                filepath: file.filepath || path.join("output", file.filename),
                type: file.type || "unknown",
                relatedLasFile: file.relatedLasFile
              });
            }
          }
          global.io?.emit("files_updated");
        }
      } catch (error) {
        console.error("Agent response processing error:", error);
        const errorMessage = await storage.addChatMessage({
          role: "agent",
          content: "I encountered an error processing your request. Please try again.",
          metadata: { error: true }
        });
        
        global.io?.emit("new_message", errorMessage);
      }
    });
    
    python.on('error', (err) => {
      console.error('Agent spawn error:', err);
    });
    
    // Add timeout for the entire process
    setTimeout(() => {
      if (!python.killed) {
        python.kill();
        console.error("Agent process timeout");
      }
    }, 30000); // 30 second timeout
    
  } catch (error) {
    console.error("Error processing user message:", error);
    
    const errorMessage = await storage.addChatMessage({
      role: "agent",
      content: "I encountered an error processing your request. Please try again.",
      metadata: { error: true }
    });
    
    global.io?.emit("new_message", errorMessage);
  }
}

// Global declaration for TypeScript
declare global {
  var io: SocketIOServer | undefined;
}
