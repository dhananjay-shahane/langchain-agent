import type { Express } from "express";
import { createServer, type Server } from "http";
import { Server as SocketIOServer } from "socket.io";
import { storage } from "./storage";
import { insertAgentConfigSchema, insertChatMessageSchema, insertLasFileSchema, insertOutputFileSchema, insertEmailSchema, insertEmailMonitorStatusSchema } from "@shared/schema";
import { spawn, exec } from "child_process";
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
      const configData = { ...req.body };
      
      // Convert lastTested string to Date object if present
      if (configData.lastTested && typeof configData.lastTested === 'string') {
        configData.lastTested = new Date(configData.lastTested);
      }
      
      // Remove fields that should be omitted by the schema
      delete configData.id;
      delete configData.createdAt;
      
      const validatedConfig = insertAgentConfigSchema.parse(configData);
      const config = await storage.updateAgentConfig(validatedConfig);
      
      // Emit config update to all clients
      io.emit("config_updated", config);
      
      res.json(config);
    } catch (error) {
      console.log("Config validation error:", error);
      res.status(400).json({ error: "Invalid config data", details: error instanceof Error ? error.message : String(error) });
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
      
      res.status(201).json(email);
    } catch (error) {
      console.error("Email creation error:", error);
      res.status(400).json({ error: "Invalid email data" });
    }
  });

  app.delete("/api/emails/:id", async (req, res) => {
    try {
      const { id } = req.params;
      const success = await storage.deleteEmail(id);
      
      if (success) {
        io.emit("email_deleted", { id });
        res.json({ success: true });
      } else {
        res.status(404).json({ error: "Email not found" });
      }
    } catch (error) {
      res.status(500).json({ error: "Failed to delete email" });
    }
  });

  // Email Monitor Status Routes
  app.get("/api/emails/monitor/status", async (req, res) => {
    try {
      const status = await storage.getEmailMonitorStatus();
      res.json(status || { isRunning: false, emailsProcessed: "0" });
    } catch (error) {
      res.status(500).json({ error: "Failed to get monitor status" });
    }
  });

  app.put("/api/emails/monitor/status", async (req, res) => {
    try {
      // Convert timestamps from Python script to Date objects
      const body = { ...req.body };
      if (body.lastStarted && typeof body.lastStarted === 'number') {
        body.lastStarted = new Date(body.lastStarted);
      }
      if (body.lastStopped && typeof body.lastStopped === 'number') {
        body.lastStopped = new Date(body.lastStopped);
      }
      
      const validatedStatus = insertEmailMonitorStatusSchema.parse(body);
      const status = await storage.updateEmailMonitorStatus(validatedStatus);
      
      // Emit status update to all clients
      io.emit("email_monitor_status", status);
      
      res.json(status);
    } catch (error) {
      console.error("Status update error:", error);
      res.status(400).json({ error: "Invalid status data" });
    }
  });

  // Email Monitor Control Routes
  app.post("/api/emails/monitor/start", async (req, res) => {
    try {
      // Check if monitor is already running
      const status = await storage.getEmailMonitorStatus();
      if (status?.isRunning) {
        return res.status(400).json({ error: "Email monitor is already running" });
      }

      // Start the Python email monitor script
      const scriptPath = path.join(process.cwd(), "scripts/email_monitor.py");
      
      if (!fs.existsSync(scriptPath)) {
        return res.status(500).json({ error: "Email monitor script not found" });
      }

      const python = spawn("uv", ["run", "python", scriptPath, "start"], {
        detached: true,
        stdio: ["ignore", "pipe", "pipe"]
      });

      // Store the process reference globally so we can stop it later
      global.emailMonitorProcess = python;

      python.stdout?.on("data", (data) => {
        console.log("Email Monitor:", data.toString());
      });

      python.stderr?.on("data", (data) => {
        console.error("Email Monitor Error:", data.toString());
      });

      python.on("close", async (code) => {
        console.log(`Email monitor process exited with code ${code}`);
        await storage.updateEmailMonitorStatus({ isRunning: false });
        io.emit("email_monitor_status", { isRunning: false });
      });

      python.on("error", async (err) => {
        console.error("Email monitor spawn error:", err);
        await storage.updateEmailMonitorStatus({ 
          isRunning: false, 
          lastError: err.message 
        });
      });

      // Update status
      const newStatus = await storage.updateEmailMonitorStatus({ 
        isRunning: true,
        lastStarted: new Date(),
        lastError: null
      });
      
      io.emit("email_monitor_status", newStatus);
      
      res.json({ success: true, message: "Email monitor started" });
    } catch (error) {
      console.error("Failed to start email monitor:", error);
      res.status(500).json({ error: "Failed to start email monitor" });
    }
  });

  app.post("/api/emails/monitor/stop", async (req, res) => {
    try {
      // Check if monitor is running
      const status = await storage.getEmailMonitorStatus();
      if (!status?.isRunning) {
        return res.status(400).json({ error: "Email monitor is not running" });
      }

      // Kill the Python process if it exists
      if (global.emailMonitorProcess) {
        global.emailMonitorProcess.kill("SIGTERM");
        global.emailMonitorProcess = undefined;
      }

      // Update status
      const newStatus = await storage.updateEmailMonitorStatus({ 
        isRunning: false,
        lastStopped: new Date()
      });
      
      io.emit("email_monitor_status", newStatus);
      
      res.json({ success: true, message: "Email monitor stopped" });
    } catch (error) {
      console.error("Failed to stop email monitor:", error);
      res.status(500).json({ error: "Failed to stop email monitor" });
    }
  });

  // Email Processing Routes (Email Agent)
  app.post("/api/emails/process", async (req, res) => {
    try {
      const { emailId, emailContent, emailFrom, emailSubject, attachments } = req.body;
      
      if (!emailId || !emailContent || !emailFrom) {
        return res.status(400).json({ error: "Missing required email data" });
      }

      // Get agent config for email processing
      const config = await storage.getAgentConfig();
      if (!config) {
        return res.status(404).json({ error: "No agent config found" });
      }

      // Process email with email agent
      const result = await processEmailWithAgent({
        emailId,
        emailContent,
        emailFrom,
        emailSubject: emailSubject || "No Subject",
        attachments: attachments || []
      }, config);

      if (result.success) {
        // Update email status to completed
        const emails = await storage.getEmails();
        const email = emails.find(e => e.id === emailId);
        if (email) {
          await storage.updateEmailStatus(emailId, "completed");
          
          // Emit status update to all clients
          io.emit("email_status_updated", { emailId, status: "completed" });
        }

        res.json({
          success: true,
          response: result.response,
          metadata: result.metadata
        });
      } else {
        res.status(500).json({
          success: false,
          error: result.error,
          response: result.response || "Failed to process email"
        });
      }
    } catch (error) {
      console.error("Email processing error:", error);
      res.status(500).json({ error: "Failed to process email" });
    }
  });

  // Email Attachments Route
  app.get("/api/emails/attachments/:filename", async (req, res) => {
    try {
      const filename = req.params.filename;
      
      // Security: Validate filename to prevent path traversal
      if (!filename || filename.includes('..') || filename.includes('/') || filename.includes('\\')) {
        return res.status(400).json({ error: "Invalid filename" });
      }
      
      const attachmentsDir = path.join(process.cwd(), "data/email-attachments");
      const filepath = path.join(attachmentsDir, filename);
      
      // Security: Ensure the resolved path is within the attachments directory
      const resolvedPath = path.resolve(filepath);
      const resolvedAttachmentsDir = path.resolve(attachmentsDir);
      if (!resolvedPath.startsWith(resolvedAttachmentsDir + path.sep) && resolvedPath !== resolvedAttachmentsDir) {
        return res.status(403).json({ error: "Access denied" });
      }
      
      if (!fs.existsSync(filepath)) {
        return res.status(404).json({ error: "Attachment not found" });
      }
      
      res.sendFile(filepath);
    } catch (error) {
      console.error("Attachment serving error:", error);
      res.status(500).json({ error: "Failed to serve attachment" });
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

async function processEmailWithAgent(emailData: any, config: any): Promise<{ success: boolean; response?: string; error?: string; metadata?: any }> {
  return new Promise((resolve) => {
    // Security: Validate config parameters to prevent command injection
    if (!config || typeof config.provider !== 'string' || typeof config.model !== 'string') {
      resolve({ success: false, error: "Invalid configuration parameters" });
      return;
    }
    
    // Security: Sanitize string inputs to prevent command injection
    const safeProvider = config.provider.replace(/[^a-zA-Z0-9_-]/g, '');
    const safeModel = config.model.replace(/[^a-zA-Z0-9_.-]/g, '');
    const safeEndpointUrl = config.endpointUrl || '';
    
    const scriptPath = path.join(process.cwd(), "server/services/email-agent.py");
    
    // Security: Verify script exists
    if (!fs.existsSync(scriptPath)) {
      resolve({ success: false, error: "Email agent script not found" });
      return;
    }
    
    // Security: Sanitize email data
    const safeEmailContent = (emailData.emailContent || "").substring(0, 5000); // Limit content length
    const safeEmailFrom = (emailData.emailFrom || "").replace(/[^\w@.-]/g, ''); // Basic email sanitization
    const safeEmailSubject = (emailData.emailSubject || "").substring(0, 200); // Limit subject length
    const safeAttachments = Array.isArray(emailData.attachments) ? emailData.attachments.slice(0, 10) : []; // Limit attachments
    
    const python = spawn("uv", [
      "run",
      "python", 
      scriptPath,
      "process",
      safeEmailContent,
      safeEmailFrom,
      safeEmailSubject,
      JSON.stringify(safeAttachments),
      JSON.stringify({
        provider: safeProvider,
        model: safeModel,
        endpointUrl: safeEndpointUrl
      })
    ]);

    let output = "";
    let errorOutput = "";
    
    python.stdout.on("data", (data) => {
      output += data.toString();
    });

    python.stderr.on("data", (data) => {
      errorOutput += data.toString();
      console.error("Email agent error:", data.toString());
    });

    python.on("close", (code) => {
      if (code === 0 && output.trim()) {
        try {
          const result = JSON.parse(output);
          resolve({
            success: result.success || true,
            response: result.response || "Email processed successfully",
            metadata: result.metadata || {}
          });
        } catch (parseError) {
          // If JSON parsing fails, treat output as raw response
          resolve({
            success: true,
            response: output.trim() || "Email processed successfully",
            metadata: { raw_output: true }
          });
        }
      } else {
        resolve({
          success: false,
          error: errorOutput || `Process exited with code ${code}`,
          response: "Failed to process email with agent"
        });
      }
    });

    python.on('error', (err) => {
      console.error('Email agent spawn error:', err);
      resolve({
        success: false,
        error: err.message,
        response: "Failed to start email agent process"
      });
    });

    setTimeout(() => {
      python.kill();
      resolve({
        success: false,
        error: "Email processing timeout",
        response: "Email processing took too long"
      });
    }, 30000); // 30 second timeout
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
  var emailMonitorProcess: any | undefined;
}
