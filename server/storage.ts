import { type AgentConfig, type ChatMessage, type LasFile, type OutputFile, type Email, type EmailMonitorStatus, type InsertAgentConfig, type InsertChatMessage, type InsertLasFile, type InsertOutputFile, type InsertEmail, type InsertEmailMonitorStatus, agentConfigs, chatMessages, lasFiles, outputFiles, emails, emailMonitorStatus } from "@shared/schema";
import { randomUUID } from "crypto";
import { db } from "./db";
import { eq, desc } from "drizzle-orm";

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

// Database Storage Implementation
export class DbStorage implements IStorage {
  async getAgentConfig(): Promise<AgentConfig | undefined> {
    const result = await db.select().from(agentConfigs).limit(1);
    return result[0];
  }

  async updateAgentConfig(config: InsertAgentConfig): Promise<AgentConfig> {
    const existing = await this.getAgentConfig();
    
    if (existing) {
      const [updated] = await db.update(agentConfigs)
        .set({ ...config, lastTested: new Date() })
        .where(eq(agentConfigs.id, existing.id))
        .returning();
      return updated;
    } else {
      const [created] = await db.insert(agentConfigs)
        .values({ ...config, lastTested: new Date() })
        .returning();
      return created;
    }
  }

  async getChatMessages(): Promise<ChatMessage[]> {
    return db.select().from(chatMessages).orderBy(chatMessages.timestamp);
  }

  async addChatMessage(message: InsertChatMessage): Promise<ChatMessage> {
    const [created] = await db.insert(chatMessages)
      .values(message)
      .returning();
    return created;
  }

  async getLasFiles(): Promise<LasFile[]> {
    return db.select().from(lasFiles).orderBy(desc(lasFiles.createdAt));
  }

  async addLasFile(file: InsertLasFile): Promise<LasFile> {
    const [created] = await db.insert(lasFiles)
      .values(file)
      .returning();
    return created;
  }

  async updateLasFile(id: string, updates: Partial<LasFile>): Promise<LasFile | undefined> {
    const [updated] = await db.update(lasFiles)
      .set(updates)
      .where(eq(lasFiles.id, id))
      .returning();
    return updated;
  }

  async getOutputFiles(): Promise<OutputFile[]> {
    return db.select().from(outputFiles).orderBy(desc(outputFiles.createdAt));
  }

  async addOutputFile(file: InsertOutputFile): Promise<OutputFile> {
    const [created] = await db.insert(outputFiles)
      .values(file)
      .returning();
    return created;
  }

  async getEmails(): Promise<Email[]> {
    return db.select().from(emails).orderBy(desc(emails.createdAt));
  }

  async addEmail(email: InsertEmail): Promise<Email> {
    const [created] = await db.insert(emails)
      .values(email)
      .returning();
    return created;
  }

  async deleteEmail(id: string): Promise<boolean> {
    const result = await db.delete(emails)
      .where(eq(emails.id, id))
      .returning();
    return result.length > 0;
  }

  async updateEmailStatus(id: string, status: string): Promise<boolean> {
    try {
      const result = await db.update(emails)
        .set({ replyStatus: status })
        .where(eq(emails.id, id))
        .returning();
      return result.length > 0;
    } catch (error) {
      console.error("Error updating email status:", error);
      return false;
    }
  }

  async getEmailMonitorStatus(): Promise<EmailMonitorStatus | undefined> {
    const result = await db.select().from(emailMonitorStatus).limit(1);
    return result[0];
  }

  async updateEmailMonitorStatus(status: InsertEmailMonitorStatus): Promise<EmailMonitorStatus> {
    const existing = await this.getEmailMonitorStatus();
    
    if (existing) {
      const [updated] = await db.update(emailMonitorStatus)
        .set({ ...status, updatedAt: new Date() })
        .where(eq(emailMonitorStatus.id, existing.id))
        .returning();
      return updated;
    } else {
      const [created] = await db.insert(emailMonitorStatus)
        .values({ ...status, updatedAt: new Date() })
        .returning();
      return created;
    }
  }

}

// Database is now provisioned, using PostgreSQL storage
export const storage = new DbStorage();
