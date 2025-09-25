import type { Express } from "express";
import { createServer, type Server } from "http";
import { Server as SocketIOServer } from "socket.io";
import { storage } from "./storage";
import { insertAgentConfigSchema, insertChatMessageSchema, insertLasFileSchema, insertOutputFileSchema, insertEmailSchema, insertEmailMonitorStatusSchema } from "@shared/schema";
import { spawn, exec } from "child_process";
import path from "path";
import fs from "fs";
import "./services/file-watcher";

// MCP email processing will use spawn-based communication with Python


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

  // Update email status
  app.put("/api/emails/:id/status", async (req, res) => {
    try {
      const { id } = req.params;
      const { status } = req.body;
      
      if (!status) {
        return res.status(400).json({ error: "Status is required" });
      }
      
      const success = await storage.updateEmailStatus(id, status);
      
      if (success) {
        // Emit status update to all clients
        io.emit("email_status_updated", { emailId: id, status });
        res.json({ success: true, status });
      } else {
        res.status(404).json({ error: "Email not found" });
      }
    } catch (error) {
      console.error("Error updating email status:", error);
      res.status(500).json({ error: "Failed to update email status" });
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
        stdio: ["ignore", "pipe", "pipe"],
        env: {
          ...process.env,
          EMAIL_USER: process.env.EMAIL_USER,
          EMAIL_PASSWORD: process.env.EMAIL_PASSWORD,
          SMTP_SERVER: process.env.SMTP_SERVER || "smtp.gmail.com",
          SMTP_PORT: process.env.SMTP_PORT || "587"
        }
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

      // Process email with MCP intelligent agent
      const result = await processEmailWithMCP({
        id: emailId,
        body: emailContent,
        from: emailFrom,
        subject: emailSubject || "No Subject",
        attachments: attachments || []
      });

      if (result.success) {
        // Don't automatically change status - let user control when to mark as completed
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

  // Automatic email processing - process all pending emails one by one
  app.post("/api/emails/process-auto", async (req, res) => {
    try {
      // Get all pending emails
      const allEmails = await storage.getEmails();
      const pendingEmails = allEmails.filter(email => email.replyStatus === "pending");
      
      if (pendingEmails.length === 0) {
        return res.json({ 
          success: true, 
          message: "No pending emails to process", 
          processed: 0 
        });
      }

      // Get agent config
      const config = await storage.getAgentConfig();
      if (!config) {
        return res.status(400).json({ error: "Agent configuration not found" });
      }

      const results = [];
      let processed = 0;
      let errors = 0;

      // Emit processing start event
      io.emit("auto_processing_started", { totalEmails: pendingEmails.length });

      // Process emails one by one
      for (const email of pendingEmails) {
        try {
          console.log(`🔄 Auto-processing email ${processed + 1}/${pendingEmails.length}: ${email.subject}`);
          
          // Emit current email being processed
          io.emit("processing_email", { 
            emailId: email.id, 
            step: processed + 1, 
            total: pendingEmails.length,
            subject: email.subject 
          });

          // Process email with step-by-step tracking
          const result = await processEmailWithMCP({
            id: email.id,
            body: email.body,
            from: email.from,
            subject: email.subject || "No Subject",
            attachments: email.attachments || []
          });

          if (result.success) {
            console.log(`✅ Generated response for: ${email.subject}`);
            
            // Emit response generated event
            io.emit("response_generated", { 
              emailId: email.id, 
              response: result.response 
            });

            // Automatically send the reply
            const replyResult = await sendEmailReply({
              toEmail: email.from.includes('<') ? email.from.split('<')[1].split('>')[0].trim() : email.from,
              subject: `Re: ${email.subject}`,
              content: result.response
            }, config);

            if (replyResult.success) {
              console.log(`📧 Auto-sent reply to: ${email.from}`);
              
              // Update email status to completed
              await storage.updateEmailStatus(email.id, "completed");
              
              // Emit reply sent and status updated events
              io.emit("reply_sent", { 
                emailId: email.id, 
                sentAt: replyResult.sent_at 
              });
              io.emit("email_status_updated", { 
                emailId: email.id, 
                status: "completed" 
              });
              
              processed++;
              results.push({
                emailId: email.id,
                subject: email.subject,
                success: true,
                message: "Processed and reply sent automatically",
                sentAt: replyResult.sent_at
              });
            } else {
              console.error(`❌ Failed to send reply for: ${email.subject}`, replyResult.error);
              errors++;
              results.push({
                emailId: email.id,
                subject: email.subject,
                success: false,
                error: `Reply generation succeeded but sending failed: ${replyResult.error}`
              });
            }
          } else {
            console.error(`❌ Failed to process: ${email.subject}`, result.error);
            errors++;
            results.push({
              emailId: email.id,
              subject: email.subject,
              success: false,
              error: result.error
            });
          }

          // Add small delay between processing emails
          await new Promise(resolve => setTimeout(resolve, 1000));

        } catch (emailError) {
          console.error(`❌ Error processing email ${email.id}:`, emailError);
          errors++;
          results.push({
            emailId: email.id,
            subject: email.subject,
            success: false,
            error: emailError instanceof Error ? emailError.message : String(emailError)
          });
        }
      }

      // Emit processing completed event
      io.emit("auto_processing_completed", { 
        totalProcessed: processed, 
        totalErrors: errors, 
        results 
      });

      console.log(`🎯 Auto-processing completed: ${processed} successful, ${errors} errors`);

      res.json({
        success: true,
        message: `Automatic processing completed: ${processed} emails processed successfully, ${errors} errors`,
        totalEmails: pendingEmails.length,
        processed,
        errors,
        results
      });

    } catch (error) {
      console.error("Auto-processing error:", error);
      io.emit("auto_processing_error", { error: error instanceof Error ? error.message : String(error) });
      res.status(500).json({ error: "Failed to auto-process emails" });
    }
  });

  // Send email reply
  app.post("/api/emails/send-reply", async (req, res) => {
    try {
      const { toEmail, subject, content } = req.body;
      
      if (!toEmail || !subject || !content) {
        return res.status(400).json({ error: "Missing required email data" });
      }

      // Get agent config for email processing
      const config = await storage.getAgentConfig();
      if (!config) {
        return res.status(400).json({ error: "Agent configuration not found" });
      }

      // Send email reply using email agent
      const result = await sendEmailReply({
        toEmail,
        subject,
        content
      }, config);

      res.json({
        success: result.success,
        message: result.message,
        sentAt: result.sent_at,
        error: result.error
      });
    } catch (error) {
      console.error("Email send error:", error);
      res.status(500).json({ error: "Failed to send email reply" });
    }
  });

  // Enhanced Email Processing with Plot Generation
  app.post("/api/emails/process-enhanced", async (req, res) => {
    try {
      const { emailId, emailContent, emailFrom, emailSubject, attachments } = req.body;
      
      if (!emailId || !emailContent || !emailFrom) {
        return res.status(400).json({ error: "Missing required email data" });
      }

      console.log(`🚀 Starting enhanced email processing for: ${emailSubject}`);

      // Process email with enhanced agent (plot generation + reply)
      const result = await processEmailWithEnhancedAgent({
        id: emailId,
        body: emailContent,
        from: emailFrom,
        subject: emailSubject || "No Subject",
        attachments: attachments || []
      });

      if (result.success) {
        console.log(`✅ Enhanced processing completed for: ${emailSubject}`);
        
        // Update email status if reply was sent
        if (result.reply_sent) {
          await storage.updateEmailStatus(emailId, "completed");
          io.emit("email_status_updated", { emailId, status: "completed" });
        }

        // Emit processing results to clients
        io.emit("enhanced_processing_completed", {
          emailId,
          success: true,
          generated_plots: result.generated_plots,
          processing_steps: result.processing_steps,
          reply_sent: result.reply_sent
        });

        res.json({
          success: true,
          response: result.response,
          generated_plots: result.generated_plots,
          processing_steps: result.processing_steps,
          reply_sent: result.reply_sent,
          query_analysis: result.query_analysis
        });
      } else {
        console.error(`❌ Enhanced processing failed for: ${emailSubject}`, result.error);
        
        io.emit("enhanced_processing_failed", {
          emailId,
          error: result.error
        });

        res.status(500).json({
          success: false,
          error: result.error,
          response: result.response || "Failed to process email with enhanced features"
        });
      }
    } catch (error) {
      console.error("Enhanced email processing error:", error);
      res.status(500).json({ error: "Failed to process email with enhanced features" });
    }
  });

  // Get Processing Steps for Progress Tracking
  app.get("/api/emails/processing-steps", async (req, res) => {
    try {
      const limit = parseInt(req.query.limit as string) || 20;
      
      // Call MCP plotting server to get processing steps
      const result = await getProcessingSteps(limit);
      
      if (result.error) {
        return res.status(500).json({ error: result.error });
      }

      res.json(result);
    } catch (error) {
      console.error("Error getting processing steps:", error);
      res.status(500).json({ error: "Failed to get processing steps" });
    }
  });

  // Clear Processing Steps
  app.delete("/api/emails/processing-steps", async (req, res) => {
    try {
      const result = await clearProcessingSteps();
      
      if (result.includes("Error")) {
        return res.status(500).json({ error: result });
      }

      res.json({ success: true, message: result });
    } catch (error) {
      console.error("Error clearing processing steps:", error);
      res.status(500).json({ error: "Failed to clear processing steps" });
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

async function sendEmailReply(emailData: any, config: any): Promise<{ success: boolean; message?: string; sent_at?: string; error?: string }> {
  return new Promise((resolve) => {
    // Security: Validate config parameters
    if (!config || typeof config.provider !== 'string' || typeof config.model !== 'string') {
      resolve({ success: false, error: "Invalid configuration parameters" });
      return;
    }
    
    // Security: Sanitize inputs
    const safeToEmail = (emailData.toEmail || "").replace(/[^a-zA-Z0-9@._-]/g, '');
    const safeSubject = (emailData.subject || "").substring(0, 200);
    const safeContent = (emailData.content || "").substring(0, 5000);
    
    const scriptPath = path.join(process.cwd(), "server/services/email-agent.py");
    
    if (!fs.existsSync(scriptPath)) {
      resolve({ success: false, error: "Email agent script not found" });
      return;
    }

    const python = spawn("uv", ["run", "python", 
      scriptPath,
      "send_reply",
      safeToEmail,
      safeSubject,
      safeContent,
      JSON.stringify(config)
    ], {
      env: {
        ...process.env,
        EMAIL_USER: process.env.EMAIL_USER,
        EMAIL_PASSWORD: process.env.EMAIL_PASSWORD,
        SMTP_SERVER: process.env.SMTP_SERVER || "smtp.gmail.com",
        SMTP_PORT: process.env.SMTP_PORT || "587"
      }
    });

    let output = "";
    let errorOutput = "";

    python.stdout.on("data", (data) => {
      output += data.toString();
    });

    python.stderr.on("data", (data) => {
      errorOutput += data.toString();
      console.error("Email send error:", data.toString());
    });

    python.on("close", (code) => {
      if (code === 0 && output.trim()) {
        try {
          const result = JSON.parse(output);
          resolve({
            success: result.success || true,
            message: result.message || "Email sent successfully",
            sent_at: result.sent_at || new Date().toISOString()
          });
        } catch (parseError) {
          resolve({
            success: true,
            message: "Email sent successfully",
            sent_at: new Date().toISOString()
          });
        }
      } else {
        resolve({
          success: false,
          error: errorOutput || `Process exited with code ${code}`
        });
      }
    });

    python.on('error', (err) => {
      console.error('Email send spawn error:', err);
      resolve({
        success: false,
        error: err.message
      });
    });

    setTimeout(() => {
      python.kill();
      resolve({
        success: false,
        error: "Email send timeout"
      });
    }, 30000); // 30 second timeout for email sending
  });
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
    const safeModel = config.model.replace(/[^a-zA-Z0-9_.:/-]/g, '');
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

async function processEmailWithMCP(emailData: any): Promise<{ success: boolean; response?: string; error?: string; metadata?: any }> {
  return new Promise((resolve) => {
    console.log("Processing email with MCP architecture:", emailData.subject || "No Subject");
    
    // Use spawn to call Python MCP client with proper JSON communication
    const scriptPath = path.join(process.cwd(), "server/services/mcp_email_client.py");
    
    // Verify script exists
    if (!fs.existsSync(scriptPath)) {
      resolve({ 
        success: false, 
        error: "MCP email client script not found",
        response: "Email processing system is not available"
      });
      return;
    }
    
    // Prepare email data for Python processing
    const emailJson = JSON.stringify({
      id: emailData.id || "unknown",
      from: emailData.from || "",
      subject: emailData.subject || "No Subject", 
      body: emailData.body || "",
      attachments: emailData.attachments || []
    });
    
    const python = spawn("uv", [
      "run",
      "python",
      scriptPath,
      "process_email",
      emailJson
    ], {
      env: {
        ...process.env,
        PYTHONPATH: process.cwd()
      }
    });

    let output = "";
    let errorOutput = "";
    
    python.stdout.on("data", (data) => {
      output += data.toString();
    });

    python.stderr.on("data", (data) => {
      errorOutput += data.toString();
      console.error("MCP processing error:", data.toString());
    });

    python.on("close", (code) => {
      if (code === 0 && output.trim()) {
        try {
          const result = JSON.parse(output.trim());
          resolve({
            success: result.success || true,
            response: result.response?.body || result.response || "Email processed with natural language understanding",
            metadata: {
              generated_files: result.generated_files || [],
              analysis: result.analysis || {},
              processing_time: result.processing_time,
              mcp_enabled: true
            }
          });
        } catch (parseError) {
          console.error("Failed to parse MCP output:", parseError);
          resolve({
            success: true,
            response: output.trim() || "Email processed with MCP system",
            metadata: { raw_output: true, mcp_enabled: true }
          });
        }
      } else {
        resolve({
          success: false,
          error: errorOutput || `MCP process exited with code ${code}`,
          response: "Thank you for your email. We are processing it with our advanced analysis system."
        });
      }
    });

    python.on('error', (err) => {
      console.error('MCP spawn error:', err);
      resolve({
        success: false,
        error: err.message,
        response: "Email processing system temporarily unavailable"
      });
    });

    // 2 minute timeout for MCP processing
    setTimeout(() => {
      python.kill();
      resolve({
        success: false,
        error: "MCP processing timeout",
        response: "Email processing is taking longer than expected. Please try again."
      });
    }, 120000);
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
        
        // Remove thinking message and add real response with thinking steps
        const agentMessage = await storage.addChatMessage({
          role: "agent",
          content: response.content,
          metadata: {
            ...(response.metadata || {}),
            thinking_steps: response.thinking_steps || []
          }
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
    
    // Add timeout for the entire process - extended for LLM processing
    setTimeout(() => {
      if (!python.killed) {
        python.kill();
        console.error("Agent process timeout");
      }
    }, 180000); // 3 minute timeout for LLM processing
    
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

// Enhanced Email Processing Function
async function processEmailWithEnhancedAgent(emailData: any): Promise<any> {
  return new Promise((resolve) => {
    // Security: Validate inputs
    if (!emailData || typeof emailData.body !== 'string' || typeof emailData.from !== 'string') {
      resolve({ success: false, error: "Invalid email data" });
      return;
    }
    
    // Security: Sanitize inputs
    const safeEmailData = {
      id: (emailData.id || "").substring(0, 100),
      body: emailData.body.substring(0, 10000),
      from: emailData.from.substring(0, 200),
      subject: (emailData.subject || "").substring(0, 500),
      attachments: Array.isArray(emailData.attachments) ? emailData.attachments.slice(0, 10) : []
    };
    
    const scriptPath = path.join(process.cwd(), "server/services/enhanced_email_agent.py");
    
    if (!fs.existsSync(scriptPath)) {
      resolve({ success: false, error: "Enhanced email agent script not found" });
      return;
    }

    console.log("🔄 Calling enhanced email agent with plot generation...");

    const python = spawn("uv", [
      "run",
      "python",
      scriptPath,
      "process_email",
      JSON.stringify(safeEmailData)
    ], {
      env: {
        ...process.env,
        EMAIL_USER: process.env.EMAIL_USER,
        EMAIL_PASS: process.env.EMAIL_PASS,
        SMTP_SERVER: process.env.SMTP_SERVER || "smtp.gmail.com",
        SMTP_PORT: process.env.SMTP_PORT || "587"
      }
    });

    let output = "";
    let errorOutput = "";

    python.stdout.on("data", (data) => {
      output += data.toString();
    });

    python.stderr.on("data", (data) => {
      errorOutput += data.toString();
      console.error("Enhanced agent error:", data.toString());
    });

    python.on("close", (code) => {
      if (code === 0 && output.trim()) {
        try {
          const result = JSON.parse(output.trim());
          console.log("✅ Enhanced email processing completed successfully");
          resolve(result);
        } catch (parseError) {
          console.error("Failed to parse enhanced agent output:", parseError);
          resolve({
            success: false,
            error: "Failed to parse enhanced agent response",
            response: output.trim()
          });
        }
      } else {
        console.error("Enhanced agent failed with code:", code);
        resolve({
          success: false,
          error: errorOutput || `Enhanced agent process exited with code ${code}`,
          response: "Enhanced email processing failed"
        });
      }
    });

    python.on('error', (err) => {
      console.error('Enhanced agent spawn error:', err);
      resolve({
        success: false,
        error: err.message,
        response: "Enhanced email processing system unavailable"
      });
    });

    // 5 minute timeout for enhanced processing (longer due to plot generation)
    setTimeout(() => {
      python.kill();
      resolve({
        success: false,
        error: "Enhanced processing timeout",
        response: "Email processing with plot generation is taking longer than expected"
      });
    }, 300000);
  });
}

// Get Processing Steps Function
async function getProcessingSteps(limit: number = 20): Promise<any> {
  try {
    const outputDir = path.join(process.cwd(), "output");
    const logFile = path.join(outputDir, "processing_steps.json");
    
    if (fs.existsSync(logFile)) {
      const logData = JSON.parse(fs.readFileSync(logFile, 'utf8'));
      const recentSteps = logData.slice(-limit);
      
      return {
        steps: recentSteps,
        total: logData.length,
        showing: recentSteps.length
      };
    } else {
      return {
        steps: [],
        total: 0,
        showing: 0
      };
    }
  } catch (error) {
    return { error: `Failed to get processing steps: ${error instanceof Error ? error.message : String(error)}` };
  }
}

// Clear Processing Steps Function
async function clearProcessingSteps(): Promise<string> {
  try {
    const outputDir = path.join(process.cwd(), "output");
    const logFile = path.join(outputDir, "processing_steps.json");
    
    if (fs.existsSync(logFile)) {
      fs.unlinkSync(logFile);
    }
    
    return "Processing steps cleared successfully";
  } catch (error) {
    return `Error clearing processing steps: ${error instanceof Error ? error.message : String(error)}`;
  }
}

// Global declaration for TypeScript
declare global {
  var io: SocketIOServer | undefined;
  var emailMonitorProcess: any | undefined;
}
