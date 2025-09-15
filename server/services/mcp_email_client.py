#!/usr/bin/env python3
"""
MCP Email Client Agent
Integrates LLM with MCP servers for intelligent email processing and response generation
"""

import asyncio
import json
import os
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

# LangChain imports
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from pydantic import SecretStr
from langchain_core.messages import HumanMessage, SystemMessage

# MCP client imports (placeholder - would use actual MCP client library)
class MCPClient:
    """Simplified MCP client for connecting to servers"""
    def __init__(self, server_endpoint: str):
        self.endpoint = server_endpoint
        
    async def call(self, tool_name: str, **kwargs):
        """Simulate MCP tool call - replace with actual MCP client implementation"""
        # In real implementation, this would make actual MCP calls
        if "email" in self.endpoint:
            return await self._mock_email_server_call(tool_name, **kwargs)
        elif "document" in self.endpoint:
            return await self._mock_document_server_call(tool_name, **kwargs)
        return {"error": "Unknown server"}
    
    async def _mock_email_server_call(self, tool_name: str, **kwargs):
        """Mock email server responses for development"""
        if tool_name == "analyze_email_intent":
            return {
                "intent": "data_analysis_request",
                "confidence": 0.9,
                "entities": ["well_data", "report_generation"],
                "requires_documents": True,
                "urgency": "normal",
                "response_strategy": {
                    "include_analysis": True,
                    "include_plots": True,
                    "include_report": True,
                    "response_tone": "professional"
                }
            }
        elif tool_name == "prepare_email_context":
            return {
                "email_id": kwargs.get("email_data", {}).get("id", ""),
                "sender": kwargs.get("email_data", {}).get("from", ""),
                "subject": kwargs.get("email_data", {}).get("subject", ""),
                "content": kwargs.get("email_data", {}).get("body", ""),
                "attachments": kwargs.get("email_data", {}).get("attachments", []),
                "metadata": {"word_count": 50, "has_attachments": True}
            }
        return {}
    
    async def _mock_document_server_call(self, tool_name: str, **kwargs):
        """Mock document server responses for development"""
        if tool_name == "create_analysis_plot":
            return f"analysis_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        elif tool_name == "generate_analysis_report":
            return f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        elif tool_name == "create_summary_visualization":
            return f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        return {}

class IntelligentEmailAgent:
    """Main email agent that uses MCP servers and LLM for natural language processing"""
    
    def __init__(self, provider: str = "ollama", model: str = "llama3.2:1b", endpoint_url: str = ""):
        self.provider = provider
        self.model = model
        self.endpoint_url = endpoint_url
        self.llm = None
        
        # Connect to MCP servers
        self.email_server = MCPClient("ws://localhost:8001")  # Email processing server
        self.document_server = MCPClient("ws://localhost:8002")  # Document generation server
        
    async def initialize(self):
        """Initialize the LLM and MCP connections"""
        try:
            # Initialize LLM based on provider
            if self.provider == "ollama":
                base_url = self.endpoint_url if self.endpoint_url else "http://localhost:11434"
                self.llm = ChatOllama(
                    model=self.model,
                    base_url=base_url,
                    temperature=0.3
                )
            elif self.provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    return False
                self.llm = ChatOpenAI(
                    model=self.model,
                    api_key=SecretStr(api_key),
                    temperature=0.3
                )
            elif self.provider == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    return False
                self.llm = ChatAnthropic(
                    model_name=self.model,
                    api_key=SecretStr(api_key),
                    temperature=0.3
                )
            
            if self.llm:
                print(f"Intelligent Email Agent initialized with {self.provider}:{self.model}")
                return True
            return False
            
        except Exception as e:
            print(f"Error initializing agent: {e}")
            return False
    
    async def process_email_intelligently(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process email using natural language understanding and generate intelligent response"""
        try:
            print(f"Processing email intelligently: {email_data.get('subject', 'No Subject')}")
            
            # Step 1: Analyze email intent using MCP email server
            intent_analysis = await self.email_server.call(
                "analyze_email_intent",
                email_content=email_data.get("body", ""),
                subject=email_data.get("subject", "")
            )
            
            print(f"Intent analysis: {intent_analysis}")
            
            # Step 2: Prepare email context
            email_context = await self.email_server.call(
                "prepare_email_context",
                email_data=email_data
            )
            
            # Step 3: Use LLM to understand and generate response strategy
            llm_prompt = f"""
            You are an intelligent email assistant that processes emails about well log analysis and oil & gas data.
            
            Email Details:
            From: {email_data.get('from', '')}
            Subject: {email_data.get('subject', '')}
            Content: {email_data.get('body', '')}
            Attachments: {', '.join(email_data.get('attachments', []))}
            
            Intent Analysis: {json.dumps(intent_analysis, indent=2)}
            
            Based on this email, provide:
            1. A professional response that addresses the sender's needs
            2. Specify what documents/visualizations should be created
            3. Explain the analysis approach for any attached data
            
            Generate a comprehensive, professional email response that demonstrates expertise in petrophysics and well log analysis.
            """
            
            response = await self.llm.ainvoke([
                SystemMessage(content="You are a senior petrophysicist and data analyst with expertise in well log interpretation."),
                HumanMessage(content=llm_prompt)
            ])
            
            response_content = response.content if hasattr(response, 'content') else str(response)
            
            # Step 4: Generate documents based on intent and LLM response
            generated_files = []
            
            if intent_analysis.get("requires_documents", False):
                # Create analysis plots
                if email_data.get("attachments"):
                    for attachment in email_data.get("attachments", []):
                        if attachment.endswith(('.las', '.txt', '.csv')):
                            plot_file = await self.document_server.call(
                                "create_analysis_plot",
                                data_file=attachment,
                                plot_type="well_log"
                            )
                            generated_files.append(plot_file)
                
                # Create summary visualization
                summary_plot = await self.document_server.call(
                    "create_summary_visualization",
                    data_summary={"zones": 4, "properties": 4},
                    chart_type="summary"
                )
                generated_files.append(summary_plot)
                
                # Generate comprehensive report
                well_name = email_data.get("attachments", ["unknown_well"])[0].split('.')[0] if email_data.get("attachments") else "analysis"
                report_file = await self.document_server.call(
                    "generate_analysis_report",
                    well_name=well_name,
                    analysis_summary=response_content[:500],  # Truncate for summary
                    plot_files=generated_files
                )
                generated_files.append(report_file)
            
            # Step 5: Format final response
            formatted_response = await self.document_server.call(
                "format_email_response",
                response_content=response_content,
                attachments=generated_files
            )
            
            return {
                "success": True,
                "response": formatted_response,
                "generated_files": generated_files,
                "analysis": intent_analysis,
                "processing_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error in intelligent email processing: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback_response": "Thank you for your email. We have received your message and will respond shortly."
            }
    
    async def process_email_with_natural_language(self, email_data: Dict[str, Any]) -> str:
        """Main entry point for natural language email processing"""
        result = await self.process_email_intelligently(email_data)
        
        if result.get("success"):
            # Save generated files info for tracking
            self._save_processing_result(email_data.get("id", ""), result)
            return result["response"]["body"]
        else:
            return result.get("fallback_response", "Error processing email")
    
    def _save_processing_result(self, email_id: str, result: Dict[str, Any]):
        """Save processing result for tracking and debugging"""
        try:
            result_file = Path("data") / f"email_processing_{email_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Processing result saved to: {result_file}")
        except Exception as e:
            print(f"Error saving processing result: {e}")

# Global agent instance
email_agent = None

async def get_email_agent():
    """Get or create email agent instance"""
    global email_agent
    if email_agent is None:
        # Load configuration from agent config
        config_file = Path("data/json-storage/agent-config.json")
        if config_file.exists():
            with open(config_file) as f:
                config = json.load(f)
                provider = config.get("provider", "ollama")
                model = config.get("model", "llama3.2:1b")
                endpoint = config.get("endpointUrl", "")
        else:
            provider = "ollama"
            model = "llama3.2:1b"
            endpoint = ""
        
        email_agent = IntelligentEmailAgent(provider, model, endpoint)
        await email_agent.initialize()
    
    return email_agent

async def process_email_with_mcp(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """Main function to process email using MCP architecture"""
    agent = await get_email_agent()
    result = await agent.process_email_intelligently(email_data)
    return result

async def main():
    """Main CLI interface for MCP email processing"""
    import sys
    
    if len(sys.argv) < 3:
        print(json.dumps({
            "success": False,
            "error": "Usage: python mcp_email_client.py process_email <email_json>"
        }))
        return
    
    command = sys.argv[1]
    
    if command == "process_email":
        try:
            email_json = sys.argv[2]
            email_data = json.loads(email_json)
            
            # Process the email using MCP architecture
            result = await process_email_with_mcp(email_data)
            
            # Output JSON result for Node.js consumption
            print(json.dumps(result))
            
        except json.JSONDecodeError as e:
            print(json.dumps({
                "success": False,
                "error": f"Invalid JSON: {e}",
                "fallback_response": "Error processing email data"
            }))
        except Exception as e:
            print(json.dumps({
                "success": False,
                "error": str(e),
                "fallback_response": "Thank you for your email. We have received it and will respond shortly."
            }))
    else:
        print(json.dumps({
            "success": False,
            "error": f"Unknown command: {command}"
        }))

if __name__ == "__main__":
    asyncio.run(main())