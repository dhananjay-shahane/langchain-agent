import express, { type Request, Response, NextFunction } from "express";
import { registerRoutes } from "./routes";
import { setupVite, serveStatic, log } from "./vite";
import { spawn } from "child_process";
import path from "path";
import fs from "fs";

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: false }));

app.use((req, res, next) => {
  const start = Date.now();
  const path = req.path;
  let capturedJsonResponse: Record<string, any> | undefined = undefined;

  const originalResJson = res.json;
  res.json = function (bodyJson, ...args) {
    capturedJsonResponse = bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };

  res.on("finish", () => {
    const duration = Date.now() - start;
    if (path.startsWith("/api")) {
      let logLine = `${req.method} ${path} ${res.statusCode} in ${duration}ms`;
      if (capturedJsonResponse) {
        logLine += ` :: ${JSON.stringify(capturedJsonResponse)}`;
      }

      if (logLine.length > 80) {
        logLine = logLine.slice(0, 79) + "…";
      }

      log(logLine);
    }
  });

  next();
});

(async () => {
  const server = await registerRoutes(app);

  app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
    const status = err.status || err.statusCode || 500;
    const message = err.message || "Internal Server Error";

    res.status(status).json({ message });
    throw err;
  });

  // importantly only setup vite in development and after
  // setting up all the other routes so the catch-all route
  // doesn't interfere with the other routes
  if (app.get("env") === "development") {
    await setupVite(app, server);
  } else {
    serveStatic(app);
  }

  // ALWAYS serve the app on the port specified in the environment variable PORT
  // Other ports are firewalled. Default to 5000 if not specified.
  // this serves both the API and the client.
  // It is the only port that is not firewalled.
  const port = parseInt(process.env.PORT || '5000', 10);
  server.listen({
    port,
    host: "0.0.0.0",
    reusePort: true,
  }, () => {
    log(`serving on port ${port}`);
    
    // Load email credentials from config file and start monitor
    try {
      const configPath = path.join(process.cwd(), 'server', 'email-config.json');
      if (fs.existsSync(configPath)) {
        const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        if (config.username && config.password) {
          process.env.EMAIL_USER = config.username;
          process.env.EMAIL_PASS = config.password;
          log("Email credentials loaded from config");
          startEmailMonitor();
        }
      }
    } catch (error) {
      log(`Could not load email config: ${error}`);
    }
  });
})();

// Email monitor service management
let emailMonitorProcess: any = null;

function startEmailMonitor() {
  if (emailMonitorProcess) {
    log("Email monitor already running");
    return;
  }

  try {
    emailMonitorProcess = spawn("python", [
      path.join(process.cwd(), "server/services/email-monitor.py")
    ], {
      stdio: ['ignore', 'pipe', 'pipe'],
      detached: false
    });

    emailMonitorProcess.stdout.on("data", (data: Buffer) => {
      const message = data.toString().trim();
      if (message) {
        log(`[EmailMonitor] ${message}`);
      }
    });

    emailMonitorProcess.stderr.on("data", (data: Buffer) => {
      const message = data.toString().trim();
      if (message) {
        log(`[EmailMonitor ERROR] ${message}`);
      }
    });

    emailMonitorProcess.on("close", (code: number) => {
      log(`Email monitor exited with code ${code}`);
      emailMonitorProcess = null;
      
      // Restart if it wasn't intentionally killed and credentials exist
      if (code !== 0 && process.env.EMAIL_USER && process.env.EMAIL_PASS) {
        setTimeout(() => {
          log("Restarting email monitor...");
          startEmailMonitor();
        }, 5000);
      }
    });

    emailMonitorProcess.on("error", (error: Error) => {
      log(`Email monitor error: ${error.message}`);
      emailMonitorProcess = null;
    });

    log("Email monitor service started");
  } catch (error) {
    log(`Failed to start email monitor: ${error}`);
  }
}

function stopEmailMonitor() {
  if (emailMonitorProcess) {
    emailMonitorProcess.kill();
    emailMonitorProcess = null;
    log("Email monitor service stopped");
  }
}

// Graceful shutdown
process.on('SIGINT', () => {
  log('Shutting down gracefully...');
  stopEmailMonitor();
  process.exit(0);
});

process.on('SIGTERM', () => {
  log('Shutting down gracefully...');
  stopEmailMonitor();
  process.exit(0);
});

// Export functions for use in routes
global.startEmailMonitor = startEmailMonitor;
global.stopEmailMonitor = stopEmailMonitor;
