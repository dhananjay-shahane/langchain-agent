import { type AgentConfig, type ChatMessage, type LasFile, type OutputFile, type Email, type InsertAgentConfig, type InsertChatMessage, type InsertLasFile, type InsertOutputFile, type InsertEmail, agentConfigs, chatMessages, lasFiles, outputFiles, emails } from "@shared/schema";
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
  getEmails(limit?: number): Promise<Email[]>;
  addEmail(email: InsertEmail): Promise<Email>;
  updateEmail(id: string, updates: Partial<Email>): Promise<Email | undefined>;
  getEmailByUid(uid: string): Promise<Email | undefined>;
}

export class MemStorage implements IStorage {
  private agentConfig: AgentConfig | undefined;
  private chatMessages: Map<string, ChatMessage>;
  private lasFiles: Map<string, LasFile>;
  private outputFiles: Map<string, OutputFile>;
  private emails: Map<string, Email>;

  constructor() {
    this.chatMessages = new Map();
    this.lasFiles = new Map();
    this.outputFiles = new Map();
    this.emails = new Map();
    
    // Initialize with default config
    this.agentConfig = {
      id: randomUUID(),
      provider: "ollama",
      model: "llama3.2:1b",
      endpointUrl: "https://cee75955aab6.ngrok-free.app",
      isConnected: false,
      lastTested: null,
      createdAt: new Date(),
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

  async getEmails(limit?: number): Promise<Email[]> {
    const emails = Array.from(this.emails.values()).sort(
      (a, b) => b.receivedAt!.getTime() - a.receivedAt!.getTime()
    );
    return limit ? emails.slice(0, limit) : emails;
  }

  async addEmail(email: InsertEmail): Promise<Email> {
    const id = randomUUID();
    const emailRecord: Email = {
      ...email,
      id,
      createdAt: new Date(),
      receivedAt: email.receivedAt || new Date(),
      processedAt: email.processedAt || null,
      attachments: email.attachments || null,
      aiAnalysis: email.aiAnalysis || null,
      jsonFile: email.jsonFile || null,
      processed: email.processed || false,
      hasAttachments: email.hasAttachments || false,
    };
    this.emails.set(id, emailRecord);
    return emailRecord;
  }

  async updateEmail(id: string, updates: Partial<Email>): Promise<Email | undefined> {
    const existing = this.emails.get(id);
    if (!existing) return undefined;
    
    const updated = { ...existing, ...updates };
    this.emails.set(id, updated);
    return updated;
  }

  async getEmailByUid(uid: string): Promise<Email | undefined> {
    return Array.from(this.emails.values()).find(email => email.uid === uid);
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

  async getEmails(limit?: number): Promise<Email[]> {
    const query = db.select().from(emails).orderBy(desc(emails.receivedAt));
    const result = limit ? await query.limit(limit) : await query;
    return result;
  }

  async addEmail(email: InsertEmail): Promise<Email> {
    const [created] = await db.insert(emails)
      .values(email)
      .returning();
    return created;
  }

  async updateEmail(id: string, updates: Partial<Email>): Promise<Email | undefined> {
    const [updated] = await db.update(emails)
      .set(updates)
      .where(eq(emails.id, id))
      .returning();
    return updated;
  }

  async getEmailByUid(uid: string): Promise<Email | undefined> {
    const result = await db.select().from(emails).where(eq(emails.uid, uid)).limit(1);
    return result[0];
  }

}

// Use MemStorage for now since database is not provisioned yet
// To use database storage, provision a PostgreSQL database and switch to:
// export const storage = new DbStorage();
export const storage = new MemStorage();
