import { sql } from "drizzle-orm";
import { pgTable, text, varchar, timestamp, jsonb, boolean } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const agentConfigs = pgTable("agent_configs", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  provider: text("provider").notNull().default("ollama"),
  model: text("model").notNull().default("llama3.2:1b"),
  endpointUrl: text("endpoint_url").notNull().default("https://cee75955aab6.ngrok-free.app"),
  isConnected: boolean("is_connected").default(false),
  lastTested: timestamp("last_tested"),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`),
});

export const chatMessages = pgTable("chat_messages", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  role: text("role").notNull(), // 'user' | 'agent' | 'system'
  content: text("content").notNull(),
  metadata: jsonb("metadata"), // For tool usage, file references, etc.
  timestamp: timestamp("timestamp").default(sql`CURRENT_TIMESTAMP`),
});

export const lasFiles = pgTable("las_files", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  filename: text("filename").notNull(),
  filepath: text("filepath").notNull(),
  size: text("size"),
  source: text("source").default("manual"), // 'email' | 'manual' | 'upload'
  processed: boolean("processed").default(false),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`),
});

export const outputFiles = pgTable("output_files", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  filename: text("filename").notNull(),
  filepath: text("filepath").notNull(),
  type: text("type").notNull(), // 'plot' | 'report' | 'analysis'
  relatedLasFile: varchar("related_las_file").references(() => lasFiles.id),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`),
});

export const emails = pgTable("emails", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  uid: text("uid").notNull().unique(),
  sender: text("sender").notNull(),
  subject: text("subject").notNull(),
  body: text("body"),
  hasAttachments: boolean("has_attachments").default(false),
  attachments: jsonb("attachments"), // JSON array of attachment data
  processed: boolean("processed").default(false),
  aiAnalysis: jsonb("ai_analysis"), // LangChain analysis results
  jsonFile: text("json_file"), // Path to saved JSON file
  receivedAt: timestamp("received_at").default(sql`CURRENT_TIMESTAMP`),
  processedAt: timestamp("processed_at"),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`),
});

export const emailConfigs = pgTable("email_configs", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  emailAddress: text("email_address").notNull(),
  emailPassword: text("email_password").notNull(),
  imapHost: text("imap_host").notNull().default("imap.gmail.com"),
  smtpHost: text("smtp_host").notNull().default("smtp.gmail.com"),
  imapPort: text("imap_port").default("993"),
  smtpPort: text("smtp_port").default("587"),
  pollInterval: text("poll_interval").default("20"),
  isEnabled: boolean("is_enabled").default(true),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`),
  updatedAt: timestamp("updated_at").default(sql`CURRENT_TIMESTAMP`),
});


export const insertAgentConfigSchema = createInsertSchema(agentConfigs).omit({
  id: true,
  createdAt: true,
});

export const insertChatMessageSchema = createInsertSchema(chatMessages).omit({
  id: true,
  timestamp: true,
});

export const insertLasFileSchema = createInsertSchema(lasFiles).omit({
  id: true,
  createdAt: true,
});

export const insertOutputFileSchema = createInsertSchema(outputFiles).omit({
  id: true,
  createdAt: true,
});

export const insertEmailSchema = createInsertSchema(emails).omit({
  id: true,
  createdAt: true,
});

export const insertEmailConfigSchema = createInsertSchema(emailConfigs).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});


export type AgentConfig = typeof agentConfigs.$inferSelect;
export type ChatMessage = typeof chatMessages.$inferSelect;
export type LasFile = typeof lasFiles.$inferSelect;
export type OutputFile = typeof outputFiles.$inferSelect;
export type Email = typeof emails.$inferSelect;
export type EmailConfig = typeof emailConfigs.$inferSelect;

export type InsertAgentConfig = z.infer<typeof insertAgentConfigSchema>;
export type InsertChatMessage = z.infer<typeof insertChatMessageSchema>;
export type InsertLasFile = z.infer<typeof insertLasFileSchema>;
export type InsertOutputFile = z.infer<typeof insertOutputFileSchema>;
export type InsertEmail = z.infer<typeof insertEmailSchema>;
export type InsertEmailConfig = z.infer<typeof insertEmailConfigSchema>;
