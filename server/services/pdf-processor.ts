import pdf from "pdf-parse";
import { RecursiveCharacterTextSplitter } from "langchain/text_splitter";
import { storage } from "../storage";
import fs from "fs";
import path from "path";

export interface PdfProcessingResult {
  text: string;
  pageCount: number;
  chunks: Array<{
    content: string;
    chunkIndex: number;
    metadata: any;
  }>;
}

export class PdfProcessor {
  private textSplitter: RecursiveCharacterTextSplitter;

  constructor() {
    this.textSplitter = new RecursiveCharacterTextSplitter({
      chunkSize: 1000,
      chunkOverlap: 200,
      separators: ["\n\n", "\n", " ", ""],
    });
  }

  async processPdfFile(filePath: string, documentId: string): Promise<PdfProcessingResult> {
    try {
      // Read the PDF file
      const pdfBuffer = fs.readFileSync(filePath);
      
      // Extract text from PDF
      const pdfData = await pdf(pdfBuffer);
      const text = pdfData.text;
      const pageCount = pdfData.numpages;

      console.log(`Extracted ${text.length} characters from PDF with ${pageCount} pages`);

      // Split text into chunks
      const documents = await this.textSplitter.createDocuments([text]);
      
      // Create chunks with metadata
      const chunks = documents.map((doc, index) => ({
        content: doc.pageContent,
        chunkIndex: index,
        metadata: {
          pageNumbers: this.estimatePageNumbers(doc.pageContent, text, pageCount),
          characterCount: doc.pageContent.length,
          wordCount: doc.pageContent.split(/\s+/).length,
        },
      }));

      console.log(`Created ${chunks.length} chunks for document ${documentId}`);

      // Store chunks in database
      for (const chunk of chunks) {
        await storage.addDocumentChunk({
          documentId,
          content: chunk.content,
          chunkIndex: chunk.chunkIndex.toString(),
          embedding: null, // Will be populated by the RAG service
          metadata: chunk.metadata,
        });
      }

      // Update document as processed
      await storage.updatePdfDocument(documentId, {
        processed: true,
        pageCount: pageCount.toString(),
      });

      return {
        text,
        pageCount,
        chunks,
      };
    } catch (error) {
      console.error("PDF processing error:", error);
      throw new Error(`Failed to process PDF: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private estimatePageNumbers(chunkContent: string, fullText: string, totalPages: number): number[] {
    // Simple heuristic to estimate which pages a chunk might come from
    const chunkStart = fullText.indexOf(chunkContent);
    const chunkEnd = chunkStart + chunkContent.length;
    
    const avgCharsPerPage = fullText.length / totalPages;
    const startPage = Math.max(1, Math.floor(chunkStart / avgCharsPerPage) + 1);
    const endPage = Math.min(totalPages, Math.ceil(chunkEnd / avgCharsPerPage) + 1);
    
    const pages = [];
    for (let i = startPage; i <= endPage; i++) {
      pages.push(i);
    }
    
    return pages.length > 0 ? pages : [1];
  }

  async getDocumentChunks(documentId: string) {
    return await storage.getDocumentChunks(documentId);
  }

  async searchChunks(documentId: string, query: string) {
    // For now, use simple text search
    // This will be enhanced with vector similarity search when Ollama embeddings are integrated
    return await storage.searchDocumentChunks(documentId, query);
  }
}

export const pdfProcessor = new PdfProcessor();