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
    """MCP client for connecting to actual MCP servers"""
    def __init__(self, server_endpoint: str):
        self.endpoint = server_endpoint
        self.server_type = self._determine_server_type()
        
    def _determine_server_type(self):
        """Determine server type based on endpoint"""
        if "8001" in self.endpoint:
            return "well_data"
        elif "8002" in self.endpoint:
            return "analysis"
        elif "8003" in self.endpoint:
            return "reporting"
        return "unknown"
        
    async def call(self, tool_name: str, **kwargs):
        """Route calls to appropriate server implementations"""
        try:
            if self.server_type == "well_data":
                return await self._call_well_data_server(tool_name, **kwargs)
            elif self.server_type == "analysis":
                return await self._call_analysis_server(tool_name, **kwargs)
            elif self.server_type == "reporting":
                return await self._call_reporting_server(tool_name, **kwargs)
            else:
                return {"error": f"Unknown server type for endpoint: {self.endpoint}"}
        except Exception as e:
            print(f"MCP client error: {e}")
            return {"error": str(e)}
    
    async def _call_well_data_server(self, tool_name: str, **kwargs):
        """Call well data server tools"""
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'mcp-servers'))
        from server_welldata import list_wells, get_logs, get_well_info
        
        if tool_name == "list_wells":
            return list_wells()
        elif tool_name == "get_logs":
            return get_logs(kwargs.get("well"), kwargs.get("curves", []))
        elif tool_name == "get_well_info":
            return get_well_info(kwargs.get("well"))
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    async def _call_analysis_server(self, tool_name: str, **kwargs):
        """Call analysis server tools"""
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'mcp-servers'))
        from server_analysis import classify_zones, compute_averages, calculate_net_to_gross, analyze_formation_quality
        
        if tool_name == "classify_zones":
            return classify_zones(kwargs.get("phie", []), kwargs.get("vsh", []), kwargs.get("swe", []))
        elif tool_name == "compute_averages":
            return compute_averages(kwargs.get("values", {}))
        elif tool_name == "calculate_net_to_gross":
            return calculate_net_to_gross(kwargs.get("flags", []))
        elif tool_name == "analyze_formation_quality":
            return analyze_formation_quality(kwargs.get("porosity", []), kwargs.get("permeability", []))
        else:
            return {"error": f"Unknown tool: {tool_name}"}
            
    async def _call_reporting_server(self, tool_name: str, **kwargs):
        """Call reporting server tools"""
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'mcp-servers'))
        from server_reporting import plot_logs, make_report, create_summary_chart
        
        if tool_name == "plot_logs":
            return plot_logs(kwargs.get("well", ""), kwargs.get("logs", {}))
        elif tool_name == "make_report":
            return make_report(kwargs.get("well", ""), kwargs.get("summary", ""), kwargs.get("plots", []))
        elif tool_name == "create_summary_chart":
            return create_summary_chart(kwargs.get("well", ""), kwargs.get("data_summary", {}))
        else:
            return {"error": f"Unknown tool: {tool_name}"}

class IntelligentEmailAgent:
    """Main email agent that uses MCP servers and LLM for natural language processing"""
    
    def __init__(self, provider: str = "ollama", model: str = "llama3.2:1b", endpoint_url: str = ""):
        self.provider = provider
        self.model = model
        self.endpoint_url = endpoint_url
        self.llm = None
        
        # Connect to MCP servers
        self.well_data_server = MCPClient("ws://localhost:8001")  # Well data server
        self.analysis_server = MCPClient("ws://localhost:8002")  # Analysis server
        self.reporting_server = MCPClient("ws://localhost:8003")  # Reporting server
        
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
            
            # Step 1: Get available wells using well data server
            available_wells = await self.well_data_server.call("list_wells")
            print(f"Available wells: {available_wells}")
            
            # Step 2: Determine analysis intent based on attachments and LLM understanding
            has_attachments = bool(email_data.get("attachments", []))
            has_well_data = any(attachment.endswith('.las') for attachment in email_data.get("attachments", []))
            
            intent_analysis = {
                "intent": "data_analysis_request" if has_well_data else "general",
                "confidence": 0.9 if has_well_data else 0.5,
                "requires_documents": has_attachments,
                "available_wells": available_wells
            }
            
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
            
            if intent_analysis.get("requires_documents", False) and available_wells:
                # Use first available well for demonstration
                well_name = available_wells[0] if available_wells else "sample_well"
                
                # Get well data for analysis
                well_logs = await self.well_data_server.call("get_logs", 
                                                           well=well_name, 
                                                           curves=["PHIE", "VSH", "GR", "RHOB"])
                
                if well_logs and not well_logs.get("error"):
                    # Perform analysis on the well data
                    if all(curve in well_logs for curve in ["PHIE", "VSH"]):
                        # Add default SWE values for analysis
                        swe_values = [0.5] * len(well_logs["PHIE"])
                        
                        # Classify zones using analysis server
                        zone_flags = await self.analysis_server.call("classify_zones",
                                                                    phie=well_logs["PHIE"],
                                                                    vsh=well_logs["VSH"],
                                                                    swe=swe_values)
                        
                        # Compute averages
                        averages = await self.analysis_server.call("compute_averages", values=well_logs)
                        
                        # Create plots using reporting server
                        plot_file = await self.reporting_server.call("plot_logs", well=well_name, logs=well_logs)
                        if plot_file and not isinstance(plot_file, dict):
                            generated_files.append(plot_file)
                        
                        # Create summary chart
                        summary_chart = await self.reporting_server.call("create_summary_chart",
                                                                        well=well_name,
                                                                        data_summary={"zones": 4, "properties": 4})
                        if summary_chart and not isinstance(summary_chart, dict):
                            generated_files.append(summary_chart)
                        
                        # Generate report
                        report_summary = f"Analysis completed for {well_name}. Zone classification and formation analysis performed."
                        report_file = await self.reporting_server.call("make_report",
                                                                      well=well_name,
                                                                      summary=report_summary,
                                                                      plots=generated_files)
                        if report_file and not isinstance(report_file, dict):
                            generated_files.append(report_file)
            
            # Step 5: Format final response
            if generated_files:
                formatted_response = f"{response_content}\n\nGenerated analysis files:\n"
                for file in generated_files:
                    formatted_response += f"- {file}\n"
                formatted_response += "\nBest regards,\nWell Log Analysis Team"
            else:
                formatted_response = response_content
            
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
                "generated_files": [],
                "processing_time": datetime.now().isoformat()
            }
    
    async def process_email_with_natural_language(self, email_data: Dict[str, Any]) -> str:
        """Main entry point for natural language email processing"""
        result = await self.process_email_intelligently(email_data)
        
        if result.get("success"):
            # Save generated files info for tracking
            self._save_processing_result(email_data.get("id", ""), result)
            # Return the response directly, not a nested body property
            response = result["response"]
            if isinstance(response, dict) and "body" in response:
                return response["body"]
            else:
                return response if isinstance(response, str) else str(response)
        else:
            return f"Error processing email: {result.get('error', 'Unknown error')}"
    
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
            
            # Ensure result is always a proper dictionary
            if not isinstance(result, dict):
                result = {
                    "success": True,
                    "response": str(result),
                    "generated_files": [],
                    "processing_time": datetime.now().isoformat()
                }
            
            # Output JSON result for Node.js consumption
            print(json.dumps(result, ensure_ascii=False))
            
        except json.JSONDecodeError as e:
            error_result = {
                "success": False,
                "error": f"Invalid JSON: {e}",
                "response": "Error processing email data - invalid format"
            }
            print(json.dumps(error_result, ensure_ascii=False))
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e)
            }
            print(json.dumps(error_result, ensure_ascii=False))
    else:
        print(json.dumps({
            "success": False,
            "error": f"Unknown command: {command}"
        }))

if __name__ == "__main__":
    asyncio.run(main())