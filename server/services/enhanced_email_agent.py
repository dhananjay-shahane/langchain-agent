#!/usr/bin/env python3
"""
Enhanced Email Agent with Plot Generation and Reply Functionality
Processes emails, generates plots from LAS data, and sends replies with PNG attachments
"""

import asyncio
import json
import os
import smtplib
import email
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
import subprocess
import sys

# LangChain imports
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from pydantic import SecretStr
from langchain_core.messages import HumanMessage, SystemMessage

class EnhancedEmailAgent:
    """Enhanced email agent with plot generation and email reply capabilities"""
    
    def __init__(self, provider: str = "ollama", model: str = "llama3.2:1b", endpoint_url: str = ""):
        self.provider = provider
        self.model = model
        self.endpoint_url = endpoint_url
        self.llm = None
        self.output_dir = Path("output")
        self.data_dir = Path("data")
        self.output_dir.mkdir(exist_ok=True)
        
        # Email configuration
        self.smtp_server = None
        self.smtp_port = 587
        self.email_user = os.getenv("EMAIL_USER")
        self.email_pass = os.getenv("EMAIL_PASS")
        
    async def initialize(self):
        """Initialize the enhanced email agent"""
        try:
            # Initialize LLM
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
                print(f"Enhanced Email Agent initialized with {self.provider}:{self.model}")
                return True
            return False
            
        except Exception as e:
            print(f"Error initializing enhanced email agent: {e}")
            return False
    
    def log_processing_step(self, step: str, details: str = "", status: str = "completed"):
        """Log processing steps for user visibility"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "step": step,
            "details": details,
            "status": status
        }
        
        log_file = self.output_dir / "email_processing_log.json"
        
        # Load existing logs
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            except:
                logs = []
        else:
            logs = []
        
        logs.append(log_entry)
        
        # Keep only last 50 entries
        if len(logs) > 50:
            logs = logs[-50:]
        
        # Save updated logs
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
        
        print(f"✓ {step}: {details}")
    
    async def call_mcp_plotting_server(self, tool_name: str, **kwargs) -> Any:
        """Call the MCP plotting server tools"""
        try:
            # Import the plotting server directly
            sys.path.append(str(Path(__file__).parent / "mcp-servers"))
            
            if tool_name == "parse_email_query":
                from server_plotting import parse_email_query
                return parse_email_query(kwargs.get("email_content", ""), kwargs.get("subject", ""))
            elif tool_name == "create_las_plot":
                from server_plotting import create_las_plot
                return create_las_plot(
                    kwargs.get("filename", ""),
                    kwargs.get("curve_type", "porosity"),
                    kwargs.get("output_prefix", "email")
                )
            elif tool_name == "create_multi_curve_plot":
                from server_plotting import create_multi_curve_plot
                return create_multi_curve_plot(
                    kwargs.get("filename", ""),
                    kwargs.get("curve_types", ["porosity"]),
                    kwargs.get("output_prefix", "email")
                )
            elif tool_name == "list_available_las_files":
                from server_plotting import list_available_las_files
                return list_available_las_files()
            elif tool_name == "get_processing_steps":
                from server_plotting import get_processing_steps
                return get_processing_steps(kwargs.get("limit", 20))
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            return {"error": f"MCP server error: {str(e)}"}
    
    async def process_email_with_plots(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process email, generate plots, and prepare response"""
        try:
            email_id = email_data.get('id', 'unknown')
            email_content = email_data.get('body', '')
            email_subject = email_data.get('subject', '')
            sender_email = email_data.get('from', '')
            attachments = email_data.get('attachments', [])
            
            self.log_processing_step("Email Received", f"From: {sender_email}, Subject: {email_subject}")
            
            # Step 1: Parse email query using MCP plotting server
            self.log_processing_step("Parsing Email Query", "Analyzing email content for plot requirements")
            query_analysis = await self.call_mcp_plotting_server(
                "parse_email_query",
                email_content=email_content,
                subject=email_subject
            )
            
            if "error" in query_analysis:
                self.log_processing_step("Query Parsing Failed", query_analysis["error"], "error")
                return {"success": False, "error": query_analysis["error"]}
            
            self.log_processing_step("Query Analysis Complete", 
                                   f"Plot types: {query_analysis.get('plot_types', [])}, "
                                   f"Urgency: {query_analysis.get('urgency', 'normal')}")
            
            # Step 2: Get available LAS files
            self.log_processing_step("Scanning Available Files", "Checking for LAS files in data directories")
            available_files = await self.call_mcp_plotting_server("list_available_las_files")
            
            if not available_files:
                self.log_processing_step("No Files Available", "No LAS files found for plotting", "warning")
                return {
                    "success": False,
                    "error": "No LAS files available for plotting",
                    "response": "I apologize, but no well log data files are currently available for analysis and plotting."
                }
            
            self.log_processing_step("Files Found", f"Available files: {', '.join(available_files[:3])}{'...' if len(available_files) > 3 else ''}")
            
            # Step 3: Determine which files to use
            target_files = []
            if query_analysis.get('las_files'):
                # Use files mentioned in email
                for mentioned_file in query_analysis['las_files']:
                    if mentioned_file in available_files:
                        target_files.append(mentioned_file)
            
            # If no specific files mentioned or found, use available files
            if not target_files:
                target_files = available_files[:2]  # Use first 2 files
            
            self.log_processing_step("Target Files Selected", f"Will process: {', '.join(target_files)}")
            
            # Step 4: Generate plots based on query analysis
            generated_plots = []
            plot_types = query_analysis.get('plot_types', ['porosity'])
            
            for filename in target_files:
                self.log_processing_step(f"Processing File: {filename}", "Starting plot generation")
                
                if len(plot_types) > 1:
                    # Create multi-curve plot
                    plot_result = await self.call_mcp_plotting_server(
                        "create_multi_curve_plot",
                        filename=filename,
                        curve_types=plot_types,
                        output_prefix="email"
                    )
                    
                    if plot_result and not plot_result.startswith("Error"):
                        generated_plots.append(plot_result)
                        self.log_processing_step("Multi-Curve Plot Created", f"Generated: {plot_result}")
                    else:
                        self.log_processing_step("Plot Generation Failed", plot_result, "error")
                else:
                    # Create individual plots for each type
                    for plot_type in plot_types:
                        plot_result = await self.call_mcp_plotting_server(
                            "create_las_plot",
                            filename=filename,
                            curve_type=plot_type,
                            output_prefix="email"
                        )
                        
                        if plot_result and not plot_result.startswith("Error"):
                            generated_plots.append(plot_result)
                            self.log_processing_step(f"{plot_type.title()} Plot Created", f"Generated: {plot_result}")
                        else:
                            self.log_processing_step(f"{plot_type.title()} Plot Failed", plot_result, "error")
            
            if not generated_plots:
                self.log_processing_step("No Plots Generated", "Failed to create any plots", "error")
                return {
                    "success": False,
                    "error": "Failed to generate any plots from the available data"
                }
            
            # Step 5: Generate intelligent response using LLM
            self.log_processing_step("Generating Response", "Creating professional email response")
            
            response_prompt = f"""
            You are a professional well log analyst responding to an email request for data analysis and visualization.
            
            Email received:
            From: {sender_email}
            Subject: {email_subject}
            Content: {email_content}
            
            Analysis performed:
            - Query analysis: {json.dumps(query_analysis, indent=2)}
            - Files processed: {', '.join(target_files)}
            - Plots generated: {', '.join(generated_plots)}
            
            Create a professional email response that:
            1. Acknowledges their request
            2. Explains what analysis was performed
            3. References the attached plots
            4. Provides brief insights based on the requested analysis
            5. Offers to provide additional analysis if needed
            
            Keep the tone professional but friendly. Do not use placeholder data or make up specific numbers.
            """
            
            response = await self.llm.ainvoke([
                SystemMessage(content="You are a senior petrophysicist and well log analyst with expertise in data visualization and formation evaluation."),
                HumanMessage(content=response_prompt)
            ])
            
            response_content = response.content if hasattr(response, 'content') else str(response)
            
            # Step 6: Format final response
            final_response = f"""{response_content}

            Generated Visualizations:
            {chr(10).join(f'• {plot}' for plot in generated_plots)}
            
            Best regards,
            Well Log Analysis Team
            """
            
            self.log_processing_step("Response Generated", f"Email response prepared with {len(generated_plots)} attachments")
            
            return {
                "success": True,
                "response": final_response,
                "generated_plots": generated_plots,
                "target_files": target_files,
                "query_analysis": query_analysis,
                "sender_email": sender_email,
                "original_subject": email_subject
            }
            
        except Exception as e:
            error_msg = f"Error processing email with plots: {str(e)}"
            self.log_processing_step("Processing Failed", error_msg, "error")
            return {"success": False, "error": error_msg}
    
    def send_email_reply(self, original_email: str, subject: str, response_body: str, 
                        plot_files: List[str], sender_name: str = "Well Log Analysis Team") -> bool:
        """Send email reply with plot attachments"""
        try:
            if not self.email_user or not self.email_pass:
                self.log_processing_step("Email Configuration Missing", 
                                       "EMAIL_USER and EMAIL_PASS environment variables required", "warning")
                return False
            
            self.log_processing_step("Preparing Email Reply", f"To: {original_email}, Attachments: {len(plot_files)}")
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = original_email
            msg['Subject'] = f"Re: {subject}"
            
            # Add body
            msg.attach(MIMEText(response_body, 'plain'))
            
            # Add plot attachments
            for plot_file in plot_files:
                plot_path = self.output_dir / plot_file
                if plot_path.exists():
                    with open(plot_path, 'rb') as f:
                        img_data = f.read()
                    
                    img_attachment = MIMEImage(img_data)
                    img_attachment.add_header('Content-Disposition', f'attachment; filename="{plot_file}"')
                    msg.attach(img_attachment)
                    
                    self.log_processing_step("Attachment Added", f"Attached: {plot_file}")
                else:
                    self.log_processing_step("Attachment Missing", f"File not found: {plot_file}", "warning")
            
            # Send email
            # Note: In production, would use actual SMTP configuration
            # For now, log the email details
            self.log_processing_step("Email Reply Prepared", 
                                   f"Ready to send to {original_email} with {len(plot_files)} attachments")
            
            # Save email to file for testing/demonstration
            email_log = {
                "timestamp": datetime.now().isoformat(),
                "to": original_email,
                "subject": msg['Subject'],
                "body": response_body,
                "attachments": plot_files
            }
            
            email_log_file = self.output_dir / f"email_reply_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(email_log_file, 'w') as f:
                json.dump(email_log, f, indent=2)
            
            self.log_processing_step("Email Reply Saved", f"Email details saved to {email_log_file.name}")
            return True
            
        except Exception as e:
            self.log_processing_step("Email Send Failed", f"Error: {str(e)}", "error")
            return False
    
    async def process_and_reply_to_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete email processing workflow: analyze, generate plots, and reply"""
        try:
            # Process email and generate plots
            processing_result = await self.process_email_with_plots(email_data)
            
            if not processing_result.get("success"):
                return processing_result
            
            # Send reply with attachments
            reply_sent = self.send_email_reply(
                original_email=processing_result["sender_email"],
                subject=processing_result["original_subject"],
                response_body=processing_result["response"],
                plot_files=processing_result["generated_plots"]
            )
            
            # Get processing steps for user visibility
            steps_result = await self.call_mcp_plotting_server("get_processing_steps", limit=20)
            
            return {
                "success": True,
                "response": processing_result["response"],
                "generated_plots": processing_result["generated_plots"],
                "reply_sent": reply_sent,
                "processing_steps": steps_result.get("steps", []),
                "query_analysis": processing_result["query_analysis"]
            }
            
        except Exception as e:
            error_msg = f"Error in complete email workflow: {str(e)}"
            self.log_processing_step("Workflow Failed", error_msg, "error")
            return {"success": False, "error": error_msg}

# Global agent instance
enhanced_email_agent = None

async def get_enhanced_email_agent():
    """Get or create enhanced email agent instance"""
    global enhanced_email_agent
    if enhanced_email_agent is None:
        # Load configuration
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
        
        enhanced_email_agent = EnhancedEmailAgent(provider, model, endpoint)
        await enhanced_email_agent.initialize()
    
    return enhanced_email_agent

async def process_email_with_enhanced_agent(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """Main function to process email with enhanced plotting capabilities"""
    agent = await get_enhanced_email_agent()
    result = await agent.process_and_reply_to_email(email_data)
    return result

async def main():
    """CLI interface for enhanced email processing"""
    import sys
    
    if len(sys.argv) < 3:
        print(json.dumps({
            "success": False,
            "error": "Usage: python enhanced_email_agent.py process_email <email_json>"
        }))
        return
    
    command = sys.argv[1]
    
    if command == "process_email":
        try:
            email_json = sys.argv[2]
            email_data = json.loads(email_json)
            
            # Process the email with enhanced capabilities
            result = await process_email_with_enhanced_agent(email_data)
            
            # Output JSON result
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        except json.JSONDecodeError as e:
            error_result = {
                "success": False,
                "error": f"Invalid JSON: {e}"
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