import type { Express } from "express";
import { createServer, type Server } from "http";
import { Server as SocketIOServer } from "socket.io";
import { storage } from "./storage";
import { insertAgentConfigSchema, insertChatMessageSchema, insertLasFileSchema, insertEmailSchema } from "@shared/schema";
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

  // Email Test Route
  app.post("/api/email/test", async (req, res) => {
    try {
      const { username, password } = req.body;
      
      if (!username || !password) {
        return res.status(400).json({ 
          success: false, 
          message: "Email address and password required" 
        });
      }
      
      // Set environment variables for the test
      process.env.EMAIL_USER = username;
      process.env.EMAIL_PASS = password;
      
      // Call the SMTP/IMAP test script
      const python = spawn("python", [
        path.join(process.cwd(), "server/services/email-smtp.py")
      ]);
      
      let output = "";
      let errorOutput = "";
      
      python.stdout.on("data", (data) => {
        output += data.toString();
      });
      
      python.stderr.on("data", (data) => {
        errorOutput += data.toString();
      });
      
      let responseSet = false;
      
      python.on("close", (code) => {
        if (responseSet) {
          return; // Response already sent
        }
        responseSet = true;
        
        if (code === 0) {
          // Email test successful, save credentials and start monitor
          try {
            // Save credentials to config file
            const emailConfig = {
              username: username,
              password: password,
              lastTested: new Date().toISOString()
            };
            fs.writeFileSync(path.join(process.cwd(), 'server', 'email-config.json'), JSON.stringify(emailConfig, null, 2));
            console.log("Email credentials saved successfully");
            
            // Start the monitor service
            try {
              if ((global as any).startEmailMonitor) {
                (global as any).startEmailMonitor();
                console.log("Email monitor started successfully");
              } else {
                console.log("startEmailMonitor function not available");
              }
            } catch (monitorError) {
              console.log("Could not start email monitor:", monitorError);
            }
          } catch (saveError) {
            console.log("Could not save email config:", saveError);
          }
          
          res.json({ 
            success: true, 
            message: "Email system tested successfully - IMAP & SMTP working. Email monitoring started." 
          });
        } else {
          res.json({ 
            success: false, 
            message: errorOutput || "Email test failed" 
          });
        }
      });
      
      const timeoutId = setTimeout(() => {
        if (responseSet) {
          return; // Response already sent
        }
        responseSet = true;
        
        python.kill();
        res.json({ 
          success: false, 
          message: "Email test timeout" 
        });
      }, 15000);
      
    } catch (error) {
      res.status(500).json({ 
        success: false, 
        message: "Email test error: " + (error as Error).message 
      });
    }
  });

  // Debug endpoint to force immediate email check
  app.post("/api/email/force-check", async (req, res) => {
    try {
      if (!process.env.EMAIL_USER || !process.env.EMAIL_PASS) {
        return res.status(400).json({ 
          success: false, 
          message: "Email credentials not configured" 
        });
      }

      // Force immediate email check using Python script
      const python = spawn("python", [
        path.join(process.cwd(), "test_email_debug.py")
      ], {
        env: {
          ...process.env,
          EMAIL_USER: process.env.EMAIL_USER,
          EMAIL_PASS: process.env.EMAIL_PASS
        }
      });

      let output = "";
      let errorOutput = "";

      python.stdout.on("data", (data) => {
        output += data.toString();
      });

      python.stderr.on("data", (data) => {
        errorOutput += data.toString();
      });

      python.on("close", (code) => {
        if (code === 0) {
          res.json({ 
            success: true, 
            message: "Email check completed", 
            details: output 
          });
        } else {
          res.json({ 
            success: false, 
            message: errorOutput || "Email check failed" 
          });
        }
      });

      setTimeout(() => {
        python.kill();
        res.json({ 
          success: false, 
          message: "Email check timeout" 
        });
      }, 30000);

    } catch (error) {
      res.status(500).json({ 
        success: false, 
        message: "Email check error: " + (error as Error).message 
      });
    }
  });

  // API endpoint to get received emails and their attachments
  app.get("/api/emails/received", async (req, res) => {
    try {
      const limit = req.query.limit ? parseInt(req.query.limit as string) : 20;
      const emails = await storage.getEmails(limit);
      
      res.json({
        totalEmails: emails.length,
        emails: emails.map(email => ({
          id: email.id,
          uid: email.uid,
          sender: email.sender,
          subject: email.subject,
          content: email.content,
          hasAttachments: email.hasAttachments,
          processed: email.processed,
          autoProcessed: email.autoProcessed,
          relatedLasFiles: email.relatedLasFiles,
          relatedOutputFiles: email.relatedOutputFiles,
          replyEmailSent: email.replyEmailSent,
          receivedAt: email.receivedAt,
        }))
      });
    } catch (error) {
      res.status(500).json({ error: "Failed to get received emails" });
    }
  });

  // API endpoint to store new email (used by email monitor)
  app.post("/api/emails/store", async (req, res) => {
    try {
      const validatedEmail = insertEmailSchema.parse(req.body);
      const email = await storage.addEmail(validatedEmail);
      
      // Emit new email notification to all clients
      io.emit("new_email", {
        id: email.id,
        sender: email.sender,
        subject: email.subject,
        hasAttachments: email.hasAttachments,
        receivedAt: email.receivedAt
      });
      
      res.json({ 
        success: true, 
        email_id: email.id,
        message: "Email stored successfully" 
      });
    } catch (error) {
      res.status(400).json({ error: "Invalid email data" });
    }
  });

  // API endpoint to update email status
  app.patch("/api/emails/:emailId", async (req, res) => {
    try {
      const emailId = req.params.emailId;
      const updates = req.body;
      const email = await storage.updateEmail(emailId, updates);
      
      if (!email) {
        return res.status(404).json({ error: "Email not found" });
      }

      // Emit email update to all clients
      io.emit("email_updated", email);
      
      res.json({ 
        success: true, 
        message: "Email updated successfully",
        email: email 
      });
    } catch (error) {
      res.status(500).json({ error: "Failed to update email" });
    }
  });

  // API endpoint to manually trigger email processing
  app.post("/api/emails/process/:emailId", async (req, res) => {
    try {
      const emailId = req.params.emailId;
      const email = await storage.updateEmail(emailId, { processed: true });
      
      if (!email) {
        return res.status(404).json({ error: "Email not found" });
      }

      // Trigger email processing logic here
      // This will be implemented with LangChain agent integration
      
      res.json({ 
        success: true, 
        message: "Email processing started",
        email: email 
      });
    } catch (error) {
      res.status(500).json({ error: "Failed to process email" });
    }
  });

  // API endpoint to manually fetch unseen emails one by one
  app.post("/api/emails/fetch-unseen", async (req, res) => {
    try {
      // Trigger the Python script to fetch unseen emails
      const python = spawn("python", [
        path.join(process.cwd(), "server/services/email-monitor.py"),
        "fetch-unseen"
      ]);

      let output = "";
      python.stdout.on("data", (data) => {
        output += data.toString();
      });

      python.on("close", (code) => {
        if (code === 0) {
          res.json({ 
            success: true, 
            message: "Unseen emails fetched successfully",
            output: output 
          });
        } else {
          res.status(500).json({ 
            success: false, 
            message: "Failed to fetch unseen emails",
            output: output 
          });
        }
      });

      setTimeout(() => {
        python.kill();
        res.status(408).json({ 
          success: false, 
          message: "Fetch unseen emails timeout" 
        });
      }, 30000); // 30 seconds timeout

    } catch (error) {
      res.status(500).json({ error: "Failed to trigger unseen email fetch" });
    }
  });

  // Webhook endpoint for real-time email notifications from IMAP IDLE
  app.post("/api/emails/webhook", async (req, res) => {
    try {
      const emailData = req.body;
      
      // Create email record for database
      const emailRecord = {
        uid: emailData.uid,
        sender: emailData.sender,
        subject: emailData.subject,
        content: emailData.content,
        hasAttachments: emailData.hasAttachments || false,
        processed: false,
        autoProcessed: false,
        replyEmailSent: false,
        relatedLasFiles: [],
        relatedOutputFiles: []
      };

      // Store in database
      const savedEmail = await storage.addEmail(emailRecord);
      
      // Emit real-time notification to all connected clients
      io.emit("realtime_email", {
        id: savedEmail.id,
        uid: savedEmail.uid,
        sender: savedEmail.sender,
        subject: savedEmail.subject,
        hasAttachments: savedEmail.hasAttachments,
        receivedAt: savedEmail.receivedAt,
        realTime: true
      });
      
      // Also emit general new_email event for compatibility
      io.emit("new_email", {
        id: savedEmail.id,
        sender: savedEmail.sender,
        subject: savedEmail.subject,
        hasAttachments: savedEmail.hasAttachments,
        receivedAt: savedEmail.receivedAt
      });
      
      console.log(`🔔 Real-time email notification sent: ${savedEmail.sender} - ${savedEmail.subject}`);
      
      res.json({ 
        success: true, 
        message: "Real-time email processed successfully",
        emailId: savedEmail.id
      });
    } catch (error) {
      console.error("Webhook error:", error);
      res.status(500).json({ error: "Failed to process real-time email" });
    }
  });

  return httpServer;
}

async function testAgentConnection(config: any): Promise<{ success: boolean; message: string }> {
  return new Promise((resolve) => {
    const python = spawn("python", [
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
    const python = spawn("python", [
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
