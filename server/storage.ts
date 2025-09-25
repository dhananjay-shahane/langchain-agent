import { type AgentConfig, type ChatMessage, type LasFile, type OutputFile, type Email, type EmailMonitorStatus, type InsertAgentConfig, type InsertChatMessage, type InsertLasFile, type InsertOutputFile, type InsertEmail, type InsertEmailMonitorStatus } from "@shared/schema";
import { randomUUID } from "crypto";
import fs from "fs";
import path from "path";

export interface IStorage {
  // Agent Config
  getAgentConfig(): Promise<AgentConfig | undefined>;
  updateAgentConfig(config: InsertAgentConfig): Promise<AgentConfig>;
  
  // Chat Messages
  getChatMessages(): Promise<ChatMessage[]>;
  addChatMessage(message: InsertChatMessage): Promise<ChatMessage>;
  
  // LAS Files
  getLasFiles(): Promise<LasFile[]>;
  addLasFile(file: InsertLasFile): Promise<LasFile>;
  updateLasFile(id: string, updates: Partial<LasFile>): Promise<LasFile | undefined>;
  
  // Output Files
  getOutputFiles(): Promise<OutputFile[]>;
  addOutputFile(file: InsertOutputFile): Promise<OutputFile>;
  
  // Emails
  getEmails(): Promise<Email[]>;
  addEmail(email: InsertEmail): Promise<Email>;
  deleteEmail(id: string): Promise<boolean>;
  updateEmailStatus(id: string, status: string): Promise<boolean>;
  
  // Email Monitor Status
  getEmailMonitorStatus(): Promise<EmailMonitorStatus | undefined>;
  updateEmailMonitorStatus(status: InsertEmailMonitorStatus): Promise<EmailMonitorStatus>;
  
}

export class MemStorage implements IStorage {
  private agentConfig: AgentConfig | undefined;
  private chatMessages: Map<string, ChatMessage>;
  private lasFiles: Map<string, LasFile>;
  private outputFiles: Map<string, OutputFile>;
  private emails: Map<string, Email>;
  private emailMonitorStatus: EmailMonitorStatus | undefined;

  constructor() {
    this.chatMessages = new Map();
    this.lasFiles = new Map();
    this.outputFiles = new Map();
    this.emails = new Map();
    
    // Initialize with default config (no hardcoded credentials)
    this.agentConfig = {
      id: randomUUID(),
      provider: "ollama",
      model: "qwen:1.8b",
      endpointUrl: "",
      isConnected: false,
      lastTested: null,
      createdAt: new Date(),
    };
    
    // Initialize email monitor status
    this.emailMonitorStatus = {
      id: randomUUID(),
      isRunning: false,
      lastStarted: null,
      lastStopped: null,
      lastError: null,
      emailsProcessed: "0",
      updatedAt: new Date(),
    };
  }

  async getAgentConfig(): Promise<AgentConfig | undefined> {
    return this.agentConfig;
  }

  async updateAgentConfig(config: InsertAgentConfig): Promise<AgentConfig> {
    this.agentConfig = {
      ...this.agentConfig!,
      ...config,
      lastTested: new Date(),
    };
    return this.agentConfig;
  }

  async getChatMessages(): Promise<ChatMessage[]> {
    return Array.from(this.chatMessages.values()).sort(
      (a, b) => a.timestamp!.getTime() - b.timestamp!.getTime()
    );
  }

  async addChatMessage(message: InsertChatMessage): Promise<ChatMessage> {
    const id = randomUUID();
    const chatMessage: ChatMessage = {
      ...message,
      id,
      timestamp: new Date(),
      metadata: message.metadata || null,
    };
    this.chatMessages.set(id, chatMessage);
    return chatMessage;
  }

  async getLasFiles(): Promise<LasFile[]> {
    return Array.from(this.lasFiles.values()).sort(
      (a, b) => b.createdAt!.getTime() - a.createdAt!.getTime()
    );
  }

  async addLasFile(file: InsertLasFile): Promise<LasFile> {
    const id = randomUUID();
    const lasFile: LasFile = {
      ...file,
      id,
      createdAt: new Date(),
      source: file.source || "manual",
      size: file.size || null,
      processed: file.processed || false,
    };
    this.lasFiles.set(id, lasFile);
    return lasFile;
  }

  async updateLasFile(id: string, updates: Partial<LasFile>): Promise<LasFile | undefined> {
    const existing = this.lasFiles.get(id);
    if (!existing) return undefined;
    
    const updated = { ...existing, ...updates };
    this.lasFiles.set(id, updated);
    return updated;
  }

  async getOutputFiles(): Promise<OutputFile[]> {
    return Array.from(this.outputFiles.values()).sort(
      (a, b) => b.createdAt!.getTime() - a.createdAt!.getTime()
    );
  }

  async addOutputFile(file: InsertOutputFile): Promise<OutputFile> {
    const id = randomUUID();
    const outputFile: OutputFile = {
      ...file,
      id,
      createdAt: new Date(),
      relatedLasFile: file.relatedLasFile || null,
    };
    this.outputFiles.set(id, outputFile);
    return outputFile;
  }

  async getEmails(): Promise<Email[]> {
    return Array.from(this.emails.values()).sort(
      (a, b) => b.createdAt!.getTime() - a.createdAt!.getTime()
    );
  }

  async addEmail(email: InsertEmail): Promise<Email> {
    const id = randomUUID();
    const emailRecord: Email = {
      ...email,
      id,
      createdAt: new Date(),
      body: email.body || "",
      attachments: email.attachments || [],
      replyStatus: email.replyStatus || "pending",
    };
    this.emails.set(id, emailRecord);
    return emailRecord;
  }

  async deleteEmail(id: string): Promise<boolean> {
    return this.emails.delete(id);
  }

  async updateEmailStatus(id: string, status: string): Promise<boolean> {
    const email = this.emails.get(id);
    if (!email) return false;
    
    email.replyStatus = status;
    this.emails.set(id, email);
    return true;
  }

  async getEmailMonitorStatus(): Promise<EmailMonitorStatus | undefined> {
    return this.emailMonitorStatus;
  }

  async updateEmailMonitorStatus(status: InsertEmailMonitorStatus): Promise<EmailMonitorStatus> {
    this.emailMonitorStatus = {
      ...this.emailMonitorStatus!,
      ...status,
      updatedAt: new Date(),
    };
    return this.emailMonitorStatus;
  }

}

// JSON File Storage Implementation
export class JsonStorage implements IStorage {
  private dataDir: string;
  private agentConfigFile: string;
  private chatMessagesFile: string;
  private lasFilesFile: string;
  private outputFilesFile: string;
  private emailsFile: string;
  private emailMonitorStatusFile: string;

  constructor() {
    this.dataDir = path.join(process.cwd(), "data", "json-storage");
    this.agentConfigFile = path.join(this.dataDir, "agent-config.json");
    this.chatMessagesFile = path.join(this.dataDir, "chat-messages.json");
    this.lasFilesFile = path.join(this.dataDir, "las-files.json");
    this.outputFilesFile = path.join(this.dataDir, "output-files.json");
    this.emailsFile = path.join(this.dataDir, "emails.json");
    this.emailMonitorStatusFile = path.join(this.dataDir, "email-monitor-status.json");
    
    // Ensure data directory exists
    this.ensureDataDir();
  }

  private ensureDataDir(): void {
    if (!fs.existsSync(this.dataDir)) {
      fs.mkdirSync(this.dataDir, { recursive: true });
    }
  }

  private readJsonFile<T>(filePath: string, defaultValue: T): T {
    try {
      if (!fs.existsSync(filePath)) {
        return defaultValue;
      }
      const data = fs.readFileSync(filePath, 'utf8');
      return JSON.parse(data, (key, value) => {
        // Convert ISO date strings back to Date objects
        if (typeof value === 'string' && /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(value)) {
          return new Date(value);
        }
        return value;
      });
    } catch (error) {
      console.error(`Error reading JSON file ${filePath}:`, error);
      return defaultValue;
    }
  }

  private writeJsonFile<T>(filePath: string, data: T): void {
    try {
      fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
    } catch (error) {
      console.error(`Error writing JSON file ${filePath}:`, error);
    }
  }

  async getAgentConfig(): Promise<AgentConfig | undefined> {
    const config = this.readJsonFile<AgentConfig | undefined>(this.agentConfigFile, undefined);
    if (!config) {
      // Initialize with default config
      const defaultConfig: AgentConfig = {
        id: randomUUID(),
        provider: "ollama",
        model: "qwen:1.8b",
        endpointUrl: "",
        isConnected: false,
        lastTested: null,
        createdAt: new Date(),
      };
      this.writeJsonFile(this.agentConfigFile, defaultConfig);
      return defaultConfig;
    }
    return config;
  }

  async updateAgentConfig(config: InsertAgentConfig): Promise<AgentConfig> {
    const existing = await this.getAgentConfig();
    const updated: AgentConfig = {
      ...existing!,
      ...config,
      lastTested: new Date(),
    };
    this.writeJsonFile(this.agentConfigFile, updated);
    return updated;
  }

  async getChatMessages(): Promise<ChatMessage[]> {
    const messages = this.readJsonFile<ChatMessage[]>(this.chatMessagesFile, []);
    return messages.sort((a, b) => a.timestamp!.getTime() - b.timestamp!.getTime());
  }

  async addChatMessage(message: InsertChatMessage): Promise<ChatMessage> {
    const messages = await this.getChatMessages();
    const chatMessage: ChatMessage = {
      ...message,
      id: randomUUID(),
      timestamp: new Date(),
      metadata: message.metadata || null,
    };
    messages.push(chatMessage);
    this.writeJsonFile(this.chatMessagesFile, messages);
    return chatMessage;
  }

  async getLasFiles(): Promise<LasFile[]> {
    const files = this.readJsonFile<LasFile[]>(this.lasFilesFile, []);
    return files.sort((a, b) => b.createdAt!.getTime() - a.createdAt!.getTime());
  }

  async addLasFile(file: InsertLasFile): Promise<LasFile> {
    const files = await this.getLasFiles();
    
    // Check for duplicates by filename and filepath
    const existingFile = files.find(f => f.filename === file.filename && f.filepath === file.filepath);
    if (existingFile) {
      return existingFile;
    }
    
    const lasFile: LasFile = {
      ...file,
      id: randomUUID(),
      createdAt: new Date(),
      source: file.source || "manual",
      size: file.size || null,
      processed: file.processed || false,
    };
    files.push(lasFile);
    this.writeJsonFile(this.lasFilesFile, files);
    return lasFile;
  }

  async updateLasFile(id: string, updates: Partial<LasFile>): Promise<LasFile | undefined> {
    const files = await this.getLasFiles();
    const index = files.findIndex(f => f.id === id);
    if (index === -1) return undefined;
    
    files[index] = { ...files[index], ...updates };
    this.writeJsonFile(this.lasFilesFile, files);
    return files[index];
  }

  async getOutputFiles(): Promise<OutputFile[]> {
    const files = this.readJsonFile<OutputFile[]>(this.outputFilesFile, []);
    return files.sort((a, b) => b.createdAt!.getTime() - a.createdAt!.getTime());
  }

  async addOutputFile(file: InsertOutputFile): Promise<OutputFile> {
    const files = await this.getOutputFiles();
    
    // Check for duplicates by filename and filepath
    const existingFile = files.find(f => f.filename === file.filename && f.filepath === file.filepath);
    if (existingFile) {
      return existingFile;
    }
    
    const outputFile: OutputFile = {
      ...file,
      id: randomUUID(),
      createdAt: new Date(),
      relatedLasFile: file.relatedLasFile || null,
    };
    files.push(outputFile);
    this.writeJsonFile(this.outputFilesFile, files);
    return outputFile;
  }

  async getEmails(): Promise<Email[]> {
    const emails = this.readJsonFile<Email[]>(this.emailsFile, []);
    return emails.sort((a, b) => b.createdAt!.getTime() - a.createdAt!.getTime());
  }

  async addEmail(email: InsertEmail): Promise<Email> {
    const emails = await this.getEmails();
    const emailRecord: Email = {
      ...email,
      id: randomUUID(),
      createdAt: new Date(),
      body: email.body || "",
      attachments: email.attachments || [],
      replyStatus: email.replyStatus || "pending",
    };
    emails.push(emailRecord);
    this.writeJsonFile(this.emailsFile, emails);
    return emailRecord;
  }

  async deleteEmail(id: string): Promise<boolean> {
    const emails = await this.getEmails();
    const index = emails.findIndex(e => e.id === id);
    if (index === -1) return false;
    
    emails.splice(index, 1);
    this.writeJsonFile(this.emailsFile, emails);
    return true;
  }

  async updateEmailStatus(id: string, status: string): Promise<boolean> {
    const emails = await this.getEmails();
    const email = emails.find(e => e.id === id);
    if (!email) return false;
    
    email.replyStatus = status;
    this.writeJsonFile(this.emailsFile, emails);
    return true;
  }

  async getEmailMonitorStatus(): Promise<EmailMonitorStatus | undefined> {
    const status = this.readJsonFile<EmailMonitorStatus | undefined>(this.emailMonitorStatusFile, undefined);
    if (!status) {
      // Initialize with default status
      const defaultStatus: EmailMonitorStatus = {
        id: randomUUID(),
        isRunning: false,
        lastStarted: null,
        lastStopped: null,
        lastError: null,
        emailsProcessed: "0",
        updatedAt: new Date(),
      };
      this.writeJsonFile(this.emailMonitorStatusFile, defaultStatus);
      return defaultStatus;
    }
    return status;
  }

  async updateEmailMonitorStatus(status: InsertEmailMonitorStatus): Promise<EmailMonitorStatus> {
    const existing = await this.getEmailMonitorStatus();
    const updated: EmailMonitorStatus = {
      ...existing!,
      ...status,
      updatedAt: new Date(),
    };
    this.writeJsonFile(this.emailMonitorStatusFile, updated);
    return updated;
  }
}

// Using JSON file storage instead of database
export const storage = new JsonStorage();
