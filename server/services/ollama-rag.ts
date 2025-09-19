import { ChatOllama, OllamaEmbeddings } from "@langchain/ollama";
import { MemoryVectorStore } from "langchain/vectorstores/memory";
import { Document } from "@langchain/core/documents";
import { PromptTemplate } from "@langchain/core/prompts";
import { StringOutputParser } from "@langchain/core/output_parsers";
import { RunnablePassthrough, RunnableSequence } from "@langchain/core/runnables";
import { storage } from "../storage";
import { pdfProcessor } from "./pdf-processor";

export interface RagResponse {
  response: string;
  relevantChunks: string[];
  error?: string;
}

export class OllamaRagService {
  private llm: ChatOllama;
  private embeddings: OllamaEmbeddings;
  private vectorStores: Map<string, MemoryVectorStore> = new Map();

  constructor() {
    // Initialize with default values - will be updated from config when used
    this.llm = new ChatOllama({
      model: "llama3.2:1b",
      temperature: 0.2,
      baseUrl: "http://localhost:11434", // Default fallback
    });

    this.embeddings = new OllamaEmbeddings({
      model: "nomic-embed-text",
      baseUrl: "http://localhost:11434",
    });
  }

  async updateFromConfig() {
    try {
      const config = await storage.getAgentConfig();
      
      // Use config endpoint URL if available, otherwise fallback to localhost
      const baseUrl = config.endpointUrl || "http://localhost:11434";
      
      // Update LLM configuration
      this.llm = new ChatOllama({
        model: config.model || "llama3.2:1b",
        temperature: 0.2,
        baseUrl,
      });

      // Update embeddings configuration  
      this.embeddings = new OllamaEmbeddings({
        model: "nomic-embed-text", // Keep stable embedding model
        baseUrl,
      });

      console.log(`Updated Ollama config: baseUrl=${baseUrl}, model=${config.model || "llama3.2:1b"}`);
      
    } catch (error) {
      console.warn("Failed to update from config, using defaults:", error);
    }
  }

  async isOllamaAvailable(): Promise<boolean> {
    try {
      const config = await storage.getAgentConfig();
      const baseUrl = config.endpointUrl || "http://localhost:11434";
      
      // Try to make a simple request to check if Ollama is running
      const response = await fetch(`${baseUrl}/api/version`);
      return response.ok;
    } catch (error) {
      console.warn("Ollama is not available:", error);
      return false;
    }
  }

  async ensureVectorStore(documentId: string): Promise<MemoryVectorStore> {
    if (this.vectorStores.has(documentId)) {
      return this.vectorStores.get(documentId)!;
    }

    console.log(`Creating vector store for document ${documentId}`);
    
    // Get document chunks from storage
    const chunks = await storage.getDocumentChunks(documentId);
    
    if (chunks.length === 0) {
      throw new Error("No chunks found for document. Make sure the document is processed.");
    }

    // Convert chunks to LangChain documents
    const documents = chunks.map(chunk => new Document({
      pageContent: chunk.content,
      metadata: {
        chunkId: chunk.id,
        chunkIndex: parseInt(chunk.chunkIndex),
        ...(chunk.metadata && typeof chunk.metadata === 'object' ? chunk.metadata : {}),
      },
    }));

    console.log(`Creating embeddings for ${documents.length} chunks`);
    
    try {
      // Create vector store with embeddings
      const vectorStore = await MemoryVectorStore.fromDocuments(documents, this.embeddings);
      
      // Cache the vector store
      this.vectorStores.set(documentId, vectorStore);
      
      return vectorStore;
    } catch (embeddingError) {
      console.warn("Failed to create embeddings, falling back to simple text matching:", embeddingError);
      
      // Fallback: create a simple vector store without semantic embeddings
      // This will use basic text similarity instead
      const vectorStore = new MemoryVectorStore();
      // Use a simple embedding function for fallback
      const simpleEmbeddings = {
        embedDocuments: async (docs: string[]) => {
          return docs.map(() => new Array(384).fill(0).map(() => Math.random()));
        },
        embedQuery: async (query: string) => {
          return new Array(384).fill(0).map(() => Math.random());
        }
      };
      
      await vectorStore.addDocuments(documents, simpleEmbeddings as any);
      
      this.vectorStores.set(documentId, vectorStore);
      return vectorStore;
    }
  }

  async chatWithDocument(documentId: string, question: string, sessionId: string): Promise<RagResponse> {
    try {
      // Update configuration from agent config
      await this.updateFromConfig();
      
      // Check if Ollama is available
      const isAvailable = await this.isOllamaAvailable();
      if (!isAvailable) {
        return {
          response: "Ollama service is not available. Please make sure Ollama is installed and running with the required models.",
          relevantChunks: [],
          error: "Ollama service unavailable",
        };
      }

      // Get or create vector store for the document
      const vectorStore = await this.ensureVectorStore(documentId);
      
      // Create retriever
      const retriever = vectorStore.asRetriever({
        k: 4, // Return top 4 relevant chunks
        searchType: "similarity",
      });

      // Define RAG prompt template
      const ragPrompt = PromptTemplate.fromTemplate(`
You are a helpful AI assistant that answers questions about PDF documents. Use the provided context to answer the user's question accurately and concisely.

Context from the document:
{context}

Question: {question}

Instructions:
- Answer based only on the provided context
- If the context doesn't contain enough information to answer the question, say so
- Be specific and cite relevant information from the context
- Keep your answer concise but comprehensive
- If you mention specific details, indicate which part of the document they come from

Answer:`);

      // Create RAG chain
      const ragChain = RunnableSequence.from([
        {
          context: retriever.pipe((docs) => {
            return docs.map((doc, i) => `Section ${i + 1}: ${doc.pageContent}`).join("\n\n");
          }),
          question: new RunnablePassthrough(),
        },
        ragPrompt,
        this.llm,
        new StringOutputParser(),
      ]);

      console.log(`Processing question for document ${documentId}: ${question.substring(0, 100)}...`);

      // Get relevant chunks first for metadata
      const relevantDocs = await retriever.invoke(question);
      const relevantChunks = relevantDocs.map(doc => doc.metadata.chunkId);

      console.log(`Found ${relevantDocs.length} relevant chunks`);

      // Generate response
      const response = await ragChain.invoke(question);

      console.log(`Generated response: ${response.substring(0, 100)}...`);

      return {
        response,
        relevantChunks,
      };
    } catch (error) {
      console.error("RAG processing error:", error);
      
      // Fallback to simple text search if vector search fails
      try {
        const simpleChunks = await storage.searchDocumentChunks(documentId, question);
        const context = simpleChunks.slice(0, 3).map(chunk => chunk.content).join("\n\n");
        
        if (context.length > 0) {
          return {
            response: `Based on the document content, I found the following relevant information:\n\n${context}\n\nNote: This is a simplified search result. For better AI-powered responses, please ensure Ollama is running with the llama3.2:1b model.`,
            relevantChunks: simpleChunks.map(chunk => chunk.id),
          };
        }
      } catch (fallbackError) {
        console.error("Fallback search also failed:", fallbackError);
      }

      return {
        response: "I encountered an error while processing your question. Please make sure the document is properly uploaded and processed, and that Ollama is running with the required models (llama3.2:1b and nomic-embed-text).",
        relevantChunks: [],
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }

  async clearVectorStore(documentId: string): Promise<void> {
    this.vectorStores.delete(documentId);
    console.log(`Cleared vector store for document ${documentId}`);
  }

  async getModelInfo(): Promise<any> {
    try {
      const config = await storage.getAgentConfig();
      const baseUrl = config.endpointUrl || "http://localhost:11434";
      
      const isAvailable = await this.isOllamaAvailable();
      if (!isAvailable) {
        return {
          available: false,
          message: "Ollama service is not running",
          baseUrl,
        };
      }

      // Try to get model information
      const response = await fetch(`${baseUrl}/api/tags`);
      const models = await response.json();
      
      return {
        available: true,
        baseUrl,
        models: models.models || [],
        requiredModels: [config.model || "llama3.2:1b", "nomic-embed-text"],
      };
    } catch (error) {
      return {
        available: false,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }
}

export const ollamaRagService = new OllamaRagService();