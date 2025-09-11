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



export type AgentConfig = typeof agentConfigs.$inferSelect;
export type ChatMessage = typeof chatMessages.$inferSelect;
export type LasFile = typeof lasFiles.$inferSelect;
export type OutputFile = typeof outputFiles.$inferSelect;

export type InsertAgentConfig = z.infer<typeof insertAgentConfigSchema>;
export type InsertChatMessage = z.infer<typeof insertChatMessageSchema>;
export type InsertLasFile = z.infer<typeof insertLasFileSchema>;
export type InsertOutputFile = z.infer<typeof insertOutputFileSchema>;
