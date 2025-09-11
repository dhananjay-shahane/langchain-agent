import { sql } from "drizzle-orm";
import { pgTable, text, varchar, timestamp, jsonb, boolean } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const agentConfigs = pgTable("agent_configs", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  provider: text("provider").notNull().default("ollama"),
  model: text("model").notNull().default("qwen:1.8b"),
  endpointUrl: text("endpoint_url").notNull().default(""),
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
  source: text("source").default("manual"), // 'manual' | 'upload'
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
  from: text("from").notNull(),
  subject: text("subject").notNull(),
  body: text("body").default(""),
  attachments: text("attachments").array().default([]),
  replyStatus: text("reply_status").default("pending"),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`),
});

export const emailMonitorStatus = pgTable("email_monitor_status", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  isRunning: boolean("is_running").default(false),
  lastStarted: timestamp("last_started"),
  lastStopped: timestamp("last_stopped"),
  lastError: text("last_error"),
  emailsProcessed: text("emails_processed").default("0"),
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

export const insertEmailMonitorStatusSchema = createInsertSchema(emailMonitorStatus).omit({
  id: true,
  updatedAt: true,
});




export type AgentConfig = typeof agentConfigs.$inferSelect;
export type ChatMessage = typeof chatMessages.$inferSelect;
export type LasFile = typeof lasFiles.$inferSelect;
export type OutputFile = typeof outputFiles.$inferSelect;
export type Email = typeof emails.$inferSelect;
export type EmailMonitorStatus = typeof emailMonitorStatus.$inferSelect;

export type InsertAgentConfig = z.infer<typeof insertAgentConfigSchema>;
export type InsertChatMessage = z.infer<typeof insertChatMessageSchema>;
export type InsertLasFile = z.infer<typeof insertLasFileSchema>;
export type InsertOutputFile = z.infer<typeof insertOutputFileSchema>;
export type InsertEmail = z.infer<typeof insertEmailSchema>;
export type InsertEmailMonitorStatus = z.infer<typeof insertEmailMonitorStatusSchema>;
