#!/usr/bin/env python3
"""
LangChain Agent with MCP Integration for LAS File Processing
"""
import sys
import json
import asyncio
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

# LangChain imports
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# MCP imports
from langchain_mcp_adapters.client import MultiServerMCPClient

class LangChainMCPAgent:
    def __init__(self, provider: str = "ollama", model: str = "llama3.2:1b", endpoint_url: str = ""):
        self.provider = provider
        self.model = model
        self.endpoint_url = endpoint_url
        self.llm = None
        self.agent = None
        self.mcp_client = None
        
    async def initialize(self):
        """Initialize the LangChain agent with MCP tools"""
        try:
            # Initialize LLM based on provider
            if self.provider == "ollama":
                base_url = self.endpoint_url if self.endpoint_url else "http://localhost:11434"
                self.llm = ChatOllama(
                    model=self.model,
                    base_url=base_url,
                    temperature=0.1
                )
            elif self.provider == "openai":
                self.llm = ChatOpenAI(
                    model=self.model,
                    api_key=os.getenv("OPENAI_API_KEY")
                )
            elif self.provider == "anthropic":
                self.llm = ChatAnthropic(
                    model_name=self.model,
                    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
                )
            
            # Initialize MCP client for custom tools
            self.mcp_client = MultiServerMCPClient({
                "las_tools": {
                    "command": "python",
                    "args": [str(Path(__file__).parent / "mcp-server.py")],
                    "transport": "stdio",
                }
            })
            
            # Get MCP tools
            mcp_tools = await self.mcp_client.get_tools()
            
            # Add custom tools
            custom_tools = [
                self.create_summary_tool(),
                self.create_file_lister_tool()
            ]
            
            all_tools = mcp_tools + custom_tools
            
            # Create agent
            self.agent = create_react_agent(self.llm, all_tools)
            
            return True
            
        except Exception as e:
            print(f"Error initializing agent: {e}")
            return False
    
    def create_summary_tool(self):
        """Create a tool for generating analysis summaries"""
        @tool
        def generate_summary(analysis_data: str) -> str:
            """Generate a summary of LAS file analysis data."""
            try:
                # Parse analysis data and create summary
                lines = analysis_data.split('\n')
                summary_points = []
                
                for line in lines:
                    if any(keyword in line.lower() for keyword in ['depth', 'porosity', 'formation', 'zone']):
                        summary_points.append(f"• {line.strip()}")
                
                return '\n'.join(summary_points) if summary_points else "No key insights found in analysis data."
            except Exception as e:
                return f"Error generating summary: {e}"
        
        return generate_summary
    
    def create_file_lister_tool(self):
        """Create a tool for listing available LAS files"""
        @tool
        def list_las_files() -> str:
            """List all available LAS files in the data directory."""
            try:
                data_dir = Path("data")
                if not data_dir.exists():
                    return "Data directory not found."
                
                las_files = list(data_dir.glob("*.las"))
                if not las_files:
                    return "No LAS files found in data directory."
                
                file_list = []
                for file_path in las_files:
                    size = file_path.stat().st_size
                    size_mb = size / (1024 * 1024)
                    file_list.append(f"• {file_path.name} ({size_mb:.2f}MB)")
                
                return f"Available LAS files:\n" + '\n'.join(file_list)
            except Exception as e:
                return f"Error listing files: {e}"
        
        return list_las_files
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to the LLM provider"""
        try:
            # Initialize only the LLM, not the full agent with MCP
            if self.provider == "ollama":
                base_url = self.endpoint_url if self.endpoint_url else "http://localhost:11434"
                self.llm = ChatOllama(
                    model=self.model,
                    base_url=base_url,
                    temperature=0.1
                )
            elif self.provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    return {"success": False, "message": "OpenAI API key not configured"}
                self.llm = ChatOpenAI(
                    model=self.model,
                    api_key=api_key
                )
            elif self.provider == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY") 
                if not api_key:
                    return {"success": False, "message": "Anthropic API key not configured"}
                self.llm = ChatAnthropic(
                    model_name=self.model,
                    anthropic_api_key=api_key
                )
            
            # Test with a simple message
            response = await self.llm.ainvoke([
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content="Hello, can you respond with 'Connection successful'?")
            ])
            
            response_content = response.content if hasattr(response, 'content') else str(response)
            if "successful" in str(response_content).lower():
                return {"success": True, "message": "Connection successful"}
            else:
                return {"success": False, "message": "Unexpected response from model"}
                
        except Exception as e:
            error_msg = str(e)
            if "connection" in error_msg.lower() and self.provider == "ollama":
                return {"success": False, "message": "Ollama server not running. Please start Ollama or change provider."}
            elif "api key" in error_msg.lower():
                return {"success": False, "message": f"{self.provider.title()} API key invalid or missing"}
            else:
                return {"success": False, "message": f"Connection failed: {error_msg}"}
    
    async def process_message(self, content: str, selected_las_file: str = "") -> Dict[str, Any]:
        """Process a user message and return agent response"""
        try:
            if not self.agent:
                if not await self.initialize():
                    return {
                        "content": "Failed to initialize agent. Please check configuration.",
                        "metadata": {"error": True}
                    }
            
            # Prepare context message
            context_parts = ["You are a specialized LAS file analysis agent. You can:"]
            context_parts.append("- Analyze well log data from LAS files")
            context_parts.append("- Generate plots and visualizations")
            context_parts.append("- Extract formation information")
            context_parts.append("- Create custom reports")
            
            if selected_las_file:
                context_parts.append(f"\nUser has selected LAS file: {selected_las_file}")
            
            context_parts.append(f"\nUser request: {content}")
            
            # Invoke agent
            response = await self.agent.ainvoke({
                "messages": [
                    SystemMessage(content="\n".join(context_parts)),
                    HumanMessage(content=content)
                ]
            })
            
            # Extract response content
            agent_response = response["messages"][-1].content
            
            # Check if any files were generated (this would be enhanced with actual MCP tool responses)
            generated_files = []
            if any(keyword in content.lower() for keyword in ['plot', 'chart', 'graph', 'visualize']):
                # Simulate file generation for demo purposes
                filename = f"{selected_las_file.replace('.las', '')}_plot_{datetime.now().strftime('%H%M%S')}.png"
                generated_files.append({
                    "filename": filename,
                    "filepath": f"output/{filename}",
                    "type": "plot",
                    "relatedLasFile": selected_las_file
                })
            
            return {
                "content": agent_response,
                "metadata": {
                    "tool_usage": True,
                    "selected_file": selected_las_file,
                    "processing_time": datetime.now().isoformat()
                },
                "generated_files": generated_files
            }
            
        except Exception as e:
            return {
                "content": f"I encountered an error while processing your request: {str(e)}",
                "metadata": {"error": True}
            }
    
    async def cleanup(self):
        """Clean up resources"""
        if self.mcp_client and hasattr(self.mcp_client, 'close'):
            try:
                await self.mcp_client.close()
            except:
                pass

async def main():
    """Main function for command line usage"""
    if len(sys.argv) < 2:
        print("Usage: python langchain-agent.py <command> [args...]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "test":
        if len(sys.argv) < 5:
            print("Usage: python langchain-agent.py test <provider> <model> <endpoint_url>")
            sys.exit(1)
        
        provider = sys.argv[2]
        model = sys.argv[3]
        endpoint_url = sys.argv[4]
        
        agent = LangChainMCPAgent(provider, model, endpoint_url)
        result = await agent.test_connection()
        await agent.cleanup()
        
        if result["success"]:
            print("SUCCESS")
        else:
            print(f"ERROR: {result['message']}")
            sys.exit(1)
    
    elif command == "process":
        if len(sys.argv) < 5:
            print("Usage: python langchain-agent.py process <content> <selected_file> <config_json>")
            sys.exit(1)
        
        content = sys.argv[2]
        selected_file = sys.argv[3]
        config_json = sys.argv[4]
        
        try:
            config = json.loads(config_json)
            agent = LangChainMCPAgent(
                config.get("provider", "ollama"),
                config.get("model", "llama3.2:1b"),
                config.get("endpointUrl", "")
            )
            
            result = await agent.process_message(content, selected_file)
            await agent.cleanup()
            
            print(json.dumps(result))
        except Exception as e:
            error_result = {
                "content": f"Processing error: {str(e)}",
                "metadata": {"error": True}
            }
            print(json.dumps(error_result))
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
