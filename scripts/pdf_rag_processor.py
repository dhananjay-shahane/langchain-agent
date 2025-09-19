#!/usr/bin/env python3
"""
PDF RAG (Retrieval-Augmented Generation) Processor

This script provides a LangChain-based RAG implementation for PDF processing
using Ollama LLM and embeddings. No fallback code or mock data - real RAG only.
"""

import os
import json
import sys
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

# LangChain imports
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFRagProcessor:
    """
    LangChain-based PDF RAG processor using Ollama
    """
    
    def __init__(self, ollama_base_url: str = "https://0cbede116e5b.ngrok-free.app"):
        """
        Initialize the PDF RAG processor
        
        Args:
            ollama_base_url: The Ollama API endpoint URL
        """
        self.ollama_base_url = ollama_base_url
        self.llm = None
        self.embeddings = None
        self.vector_stores = {}
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Initialize Ollama components
        self._initialize_ollama()
    
    def _initialize_ollama(self):
        """Initialize Ollama LLM and embeddings"""
        try:
            logger.info(f"Initializing Ollama with base URL: {self.ollama_base_url}")
            
            # Initialize LLM
            self.llm = OllamaLLM(
                model="llama3.2:1b",
                base_url=self.ollama_base_url,
                temperature=0.2
            )
            
            # Initialize embeddings
            self.embeddings = OllamaEmbeddings(
                model="nomic-embed-text",
                base_url=self.ollama_base_url
            )
            
            logger.info("Ollama components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Ollama components: {e}")
            raise RuntimeError(f"Ollama initialization failed: {e}")
    
    def test_ollama_connection(self) -> bool:
        """
        Test connection to Ollama service
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            # Test LLM connection
            response = self.llm.invoke("Hello, are you working?")
            logger.info(f"Ollama LLM test response: {response[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Ollama connection test failed: {e}")
            return False
    
    def process_pdf_document(self, pdf_path: str, document_id: str) -> Dict[str, Any]:
        """
        Process a PDF document: extract text, create chunks, and build vector store
        
        Args:
            pdf_path: Path to the PDF file
            document_id: Unique identifier for the document
            
        Returns:
            Dict containing processing results
        """
        try:
            logger.info(f"Processing PDF document: {pdf_path}")
            
            # Load PDF document
            loader = PyPDFLoader(pdf_path)
            documents = loader.load()
            
            logger.info(f"Loaded {len(documents)} pages from PDF")
            
            # Split documents into chunks
            chunks = self.text_splitter.split_documents(documents)
            logger.info(f"Split document into {len(chunks)} chunks")
            
            # Create vector store with embeddings
            logger.info("Creating vector store with Ollama embeddings...")
            vector_store = FAISS.from_documents(chunks, self.embeddings)
            
            # Cache vector store
            self.vector_stores[document_id] = vector_store
            
            # Save vector store to disk for persistence
            vector_store_path = f"data/vector_stores/{document_id}"
            os.makedirs(os.path.dirname(vector_store_path), exist_ok=True)
            vector_store.save_local(vector_store_path)
            
            logger.info(f"PDF processing completed for document {document_id}")
            
            return {
                "document_id": document_id,
                "pages": len(documents),
                "chunks": len(chunks),
                "vector_store_path": vector_store_path,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"PDF processing failed for {pdf_path}: {e}")
            raise RuntimeError(f"PDF processing failed: {e}")
    
    def load_vector_store(self, document_id: str) -> Optional[FAISS]:
        """
        Load vector store for a document
        
        Args:
            document_id: Document identifier
            
        Returns:
            FAISS vector store or None if not found
        """
        # Check if already cached
        if document_id in self.vector_stores:
            return self.vector_stores[document_id]
        
        # Try to load from disk
        vector_store_path = f"data/vector_stores/{document_id}"
        if os.path.exists(vector_store_path):
            try:
                vector_store = FAISS.load_local(vector_store_path, self.embeddings)
                self.vector_stores[document_id] = vector_store
                logger.info(f"Loaded vector store for document {document_id}")
                return vector_store
            except Exception as e:
                logger.error(f"Failed to load vector store for {document_id}: {e}")
        
        return None
    
    def chat_with_document(self, document_id: str, question: str, context_size: int = 4) -> Dict[str, Any]:
        """
        Chat with a document using RAG
        
        Args:
            document_id: Document identifier
            question: User question
            context_size: Number of relevant chunks to retrieve
            
        Returns:
            Dict containing response and metadata
        """
        try:
            logger.info(f"Processing question for document {document_id}: {question[:100]}...")
            
            # Load vector store
            vector_store = self.load_vector_store(document_id)
            if not vector_store:
                raise ValueError(f"No vector store found for document {document_id}")
            
            # Create retriever
            retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": context_size}
            )
            
            # Define RAG prompt template
            prompt_template = """
You are a helpful AI assistant that answers questions about PDF documents. 
Use the provided context to answer the user's question accurately and concisely.

Context from the document:
{context}

Question: {question}

Instructions:
- Answer based only on the provided context
- If the context doesn't contain enough information to answer the question, say so
- Be specific and cite relevant information from the context
- Keep your answer concise but comprehensive
- If you mention specific details, indicate which part of the document they come from

Answer:"""

            prompt = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"]
            )
            
            # Create RetrievalQA chain
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                chain_type_kwargs={"prompt": prompt},
                return_source_documents=True
            )
            
            # Get response
            logger.info("Generating RAG response...")
            result = qa_chain.invoke({"query": question})
            
            # Extract relevant chunk information
            relevant_chunks = []
            for doc in result["source_documents"]:
                relevant_chunks.append({
                    "content": doc.page_content[:200] + "...",  # Truncate for brevity
                    "metadata": doc.metadata
                })
            
            response_data = {
                "response": result["result"],
                "relevant_chunks": relevant_chunks,
                "document_id": document_id,
                "question": question,
                "status": "success"
            }
            
            logger.info(f"Generated response: {result['result'][:100]}...")
            return response_data
            
        except Exception as e:
            logger.error(f"RAG chat processing failed: {e}")
            raise RuntimeError(f"RAG chat processing failed: {e}")
    
    def list_processed_documents(self) -> List[str]:
        """
        List all processed documents (with vector stores)
        
        Returns:
            List of document IDs
        """
        vector_store_dir = Path("data/vector_stores")
        if not vector_store_dir.exists():
            return []
        
        return [d.name for d in vector_store_dir.iterdir() if d.is_dir()]


def main():
    """
    Main function for command-line usage
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="PDF RAG Processor using LangChain and Ollama")
    parser.add_argument("command", choices=["process", "chat", "test"], help="Command to execute")
    parser.add_argument("--pdf", help="Path to PDF file (for process command)")
    parser.add_argument("--document-id", help="Document ID")
    parser.add_argument("--question", help="Question to ask (for chat command)")
    parser.add_argument("--ollama-url", default="https://0cbede116e5b.ngrok-free.app", 
                       help="Ollama base URL")
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = PDFRagProcessor(ollama_base_url=args.ollama_url)
    
    if args.command == "test":
        print("Testing Ollama connection...")
        success = processor.test_ollama_connection()
        if success:
            print("✓ Ollama connection successful")
        else:
            print("✗ Ollama connection failed")
            sys.exit(1)
    
    elif args.command == "process":
        if not args.pdf or not args.document_id:
            print("Error: --pdf and --document-id required for process command")
            sys.exit(1)
        
        try:
            result = processor.process_pdf_document(args.pdf, args.document_id)
            print(f"✓ PDF processed successfully:")
            print(f"  Document ID: {result['document_id']}")
            print(f"  Pages: {result['pages']}")
            print(f"  Chunks: {result['chunks']}")
            print(f"  Vector store: {result['vector_store_path']}")
        except Exception as e:
            print(f"✗ PDF processing failed: {e}")
            sys.exit(1)
    
    elif args.command == "chat":
        if not args.document_id or not args.question:
            print("Error: --document-id and --question required for chat command")
            sys.exit(1)
        
        try:
            result = processor.chat_with_document(args.document_id, args.question)
            print(f"Question: {result['question']}")
            print(f"Answer: {result['response']}")
            print(f"Sources: {len(result['relevant_chunks'])} relevant chunks")
        except Exception as e:
            print(f"✗ Chat processing failed: {e}")
            sys.exit(1)
    
    else:
        print("Unknown command")
        sys.exit(1)


if __name__ == "__main__":
    main()