#!/usr/bin/env python3
"""
LangChain Agent with MCP Integration for LAS File Processing
"""
import sys
import json
import re
import asyncio
import os
import subprocess
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


# Define plotting tools using existing working log_plotter.py
@tool
def create_gamma_ray_plot(las_filename: str) -> str:
    """Create a gamma ray depth plot from LAS file.
    
    Args:
        las_filename: Name of the LAS file to process
        
    Returns:
        Result message with output filename
    """
    try:
        result = subprocess.run([
            'C:\\Users\\Dhananjay\\Documents\\GitHub\\langchain-agent\\.venv\\Scripts\\python.exe', 'server/services/mcp-tools/log_plotter.py', 'gamma', las_filename
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            output = result.stdout.strip()
            # Parse JSON response and extract filename
            try:
                response_data = json.loads(output)
                if response_data.get('success'):
                    return f"Gamma Ray Plot Created: {response_data.get('output_file')}"
                else:
                    return f"Error: {response_data.get('error')}"
            except json.JSONDecodeError:
                return output
        else:
            return f"Error creating gamma ray plot: {result.stderr.strip()}"
    except Exception as e:
        return f"Error executing gamma ray plot script: {str(e)}"


@tool
def create_porosity_plot(las_filename: str) -> str:
    """Create a porosity depth plot from LAS file.
    
    Args:
        las_filename: Name of the LAS file to process
        
    Returns:
        Result message with output filename
    """
    try:
        result = subprocess.run([
            'C:\\Users\\Dhananjay\\Documents\\GitHub\\langchain-agent\\.venv\\Scripts\\python.exe', 'server/services/mcp-tools/log_plotter.py', 'porosity', las_filename
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            output = result.stdout.strip()
            # Parse JSON response and extract filename
            try:
                response_data = json.loads(output)
                if response_data.get('success'):
                    return f"Porosity Plot Created: {response_data.get('output_file')}"
                else:
                    return f"Error: {response_data.get('error')}"
            except json.JSONDecodeError:
                return output
        else:
            return f"Error creating porosity plot: {result.stderr.strip()}"
    except Exception as e:
        return f"Error executing porosity plot script: {str(e)}"


@tool
def create_resistivity_plot(las_filename: str) -> str:
    """Create a resistivity depth plot from LAS file.
    
    Args:
        las_filename: Name of the LAS file to process
        
    Returns:
        Result message with output filename
    """
    try:
        result = subprocess.run([
            'C:\\Users\\Dhananjay\\Documents\\GitHub\\langchain-agent\\.venv\\Scripts\\python.exe', 'server/services/mcp-tools/log_plotter.py', 'resistivity', las_filename
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            output = result.stdout.strip()
            # Parse JSON response and extract filename
            try:
                response_data = json.loads(output)
                if response_data.get('success'):
                    return f"Resistivity Plot Created: {response_data.get('output_file')}"
                else:
                    return f"Error: {response_data.get('error')}"
            except json.JSONDecodeError:
                return output
        else:
            return f"Error creating resistivity plot: {result.stderr.strip()}"
    except Exception as e:
        return f"Error executing resistivity plot script: {str(e)}"


@tool
def create_density_plot(las_filename: str) -> str:
    """Create a density depth plot from LAS file.
    
    Args:
        las_filename: Name of the LAS file to process
        
    Returns:
        Result message with output filename
    """
    try:
        result = subprocess.run([
            'C:\\Users\\Dhananjay\\Documents\\GitHub\\langchain-agent\\.venv\\Scripts\\python.exe', 'server/services/mcp-tools/log_plotter.py', 'density', las_filename
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            output = result.stdout.strip()
            # Parse JSON response and extract filename
            try:
                response_data = json.loads(output)
                if response_data.get('success'):
                    return f"Density Plot Created: {response_data.get('output_file')}"
                else:
                    return f"Error: {response_data.get('error')}"
            except json.JSONDecodeError:
                return output
        else:
            return f"Error creating density plot: {result.stderr.strip()}"
    except Exception as e:
        return f"Error executing density plot script: {str(e)}"


@tool
def create_composite_log_plot(las_filename: str) -> str:
    """Create a composite log plot with multiple curves from LAS file.
    
    Args:
        las_filename: Name of the LAS file to process
        
    Returns:
        Result message with output filename
    """
    try:
        result = subprocess.run([
            'C:\\Users\\Dhananjay\\Documents\\GitHub\\langchain-agent\\.venv\\Scripts\\python.exe', 'server/services/mcp-tools/log_plotter.py', 'composite', las_filename
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            output = result.stdout.strip()
            # Parse JSON response and extract filename
            try:
                response_data = json.loads(output)
                if response_data.get('success'):
                    return f"Composite Log Plot Created: {response_data.get('output_file')}"
                else:
                    return f"Error: {response_data.get('error')}"
            except json.JSONDecodeError:
                return output
        else:
            return f"Error creating composite log plot: {result.stderr.strip()}"
    except Exception as e:
        return f"Error executing composite log plot script: {str(e)}"


class LangChainMCPAgent:

    def __init__(self,
                 provider: str = "ollama",
                 model: str = "llama3.2:1b",
                 endpoint_url: str = ""):
        self.provider = provider
        self.model = model
        self.endpoint_url = endpoint_url
        self.llm = None
        self.agent = None
        self.mcp_client = None

    @staticmethod
    def extract_filename_from_tool_output(tool_output: str) -> str:
        """Extract filename from MCP tool output message.
        
        Args:
            tool_output: Tool response message like "✅ Gamma Ray Plot Created: filename.png"
            
        Returns:
            Extracted filename or original tool_output if parsing fails
        """
        try:
            # First try to parse as JSON and look for output_file
            try:
                data = json.loads(tool_output)
                if "output_file" in data:
                    return os.path.basename(data["output_file"])
            except json.JSONDecodeError:
                pass

            # Use regex to extract filename pattern from common tool responses
            filename_pattern = r'([A-Za-z0-9_./\\-]+\.(?:png|jpg|jpeg|svg|pdf|json|txt|las))'
            matches = re.findall(filename_pattern, tool_output, re.IGNORECASE)

            if matches:
                # Get the last match (most likely to be the actual filename)
                filename = matches[-1]
                return os.path.basename(filename)

            # Fallback: strip common prefixes if no filename pattern found
            prefixes_to_strip = [
                "✅ Gamma Ray Plot Created: ", "✅ Porosity Plot Created: ",
                "✅ Resistivity Plot Created: ", "Plot saved as ",
                "created successfully: ", "SUCCESS: "
            ]

            result = tool_output
            for prefix in prefixes_to_strip:
                if result.startswith(prefix):
                    result = result[len(prefix):]
                    break

            # Clean up any trailing description after newlines
            result = result.split('\n')[0].strip()

            # If result looks like a filename, return basename, otherwise return original
            if re.match(
                    r'^[A-Za-z0-9_.-]+\.(png|jpg|jpeg|svg|pdf|json|txt|las)$',
                    result, re.IGNORECASE):
                return os.path.basename(result)

            return tool_output

        except Exception as e:
            print(f"Error extracting filename from tool output: {e}")
            return tool_output

    async def initialize(self):
        """Initialize the LangChain agent"""
        try:
            # Initialize LLM based on provider
            if self.provider == "ollama":
                base_url = self.endpoint_url if self.endpoint_url else "http://localhost:11434"
                self.llm = ChatOllama(
                    model=self.model,
                    base_url=base_url,
                    temperature=0.1,
                    timeout=120  # Extended timeout for llama3.2:1b model
                )
            elif self.provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    return False
                self.llm = ChatOpenAI(model=self.model, api_key=api_key)
            elif self.provider == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    return False
                self.llm = ChatAnthropic(model_name=self.model,
                                         api_key=api_key,
                                         timeout=30,
                                         stop=[])

            # Create comprehensive MCP tools for LAS analysis
            custom_tools = [
                create_gamma_ray_plot,
                create_porosity_plot,
                create_resistivity_plot,
                create_density_plot,
                create_composite_log_plot
            ]

            # Create agent with custom tools
            self.agent = create_react_agent(self.llm, custom_tools)

            return True

        except Exception as e:
            print(f"Error initializing agent: {e}")
            return False

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to the LLM provider"""
        try:
            # Initialize only the LLM, not the full agent with MCP
            if self.provider == "ollama":
                base_url = self.endpoint_url if self.endpoint_url else "http://localhost:11434"
                self.llm = ChatOllama(
                    model=self.model,
                    base_url=base_url,
                    temperature=0.1,
                    timeout=120  # Extended timeout for llama3.2:1b model
                )
            elif self.provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    return {
                        "success": False,
                        "message": "OpenAI API key not configured"
                    }
                self.llm = ChatOpenAI(model=self.model, api_key=api_key)
            elif self.provider == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    return {
                        "success": False,
                        "message": "Anthropic API key not configured"
                    }
                self.llm = ChatAnthropic(model_name=self.model,
                                         api_key=api_key,
                                         timeout=30,
                                         stop=[])

            # Test with a simple message with timeout
            import asyncio
            try:
                response = await asyncio.wait_for(
                    self.llm.ainvoke([
                        SystemMessage(content="You are a helpful assistant."),
                        HumanMessage(
                            content=
                            "Hello, can you respond with 'Connection successful'?"
                        )
                    ]),
                    timeout=60.0  # 60 second timeout for connection test
                )
            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "message": "Connection timeout - server not responding"
                }

            response_content = response.content if hasattr(
                response, 'content') else str(response)
            if "successful" in str(response_content).lower():
                return {"success": True, "message": "Connection successful"}
            else:
                return {
                    "success": False,
                    "message": "Unexpected response from model"
                }

        except Exception as e:
            error_msg = str(e)
            if "connection" in error_msg.lower() and self.provider == "ollama":
                return {
                    "success":
                    False,
                    "message":
                    "Ollama server not running. Please start Ollama or change provider."
                }
            elif "api key" in error_msg.lower():
                return {
                    "success":
                    False,
                    "message":
                    f"{self.provider.title()} API key invalid or missing"
                }
            else:
                return {
                    "success": False,
                    "message": f"Connection failed: {error_msg}"
                }

    async def process_message(self,
                              content: str,
                              selected_las_file: str = "") -> Dict[str, Any]:
        """Process a user message and return agent response with thinking steps"""
        if not self.agent:
            await self.initialize()

        # Prepare context message
        context_parts = [
            "You are a specialized LAS file analysis agent. You can:"
        ]
        context_parts.append("- Analyze well log data from LAS files")
        context_parts.append("- Generate plots and visualizations")
        context_parts.append("- Extract formation information")
        context_parts.append("- Create custom reports")

        if selected_las_file:
            context_parts.append(
                f"\nUser has selected LAS file: {selected_las_file}")

        context_parts.append(f"\nUser request: {content}")

        # Invoke agent
        response = await self.agent.ainvoke({
            "messages": [
                SystemMessage(content="\n".join(context_parts)),
                HumanMessage(content=content)
            ]
        })

        # Extract thinking steps from all messages
        thinking_steps = []
        final_response = ""
        generated_files = []

        messages = response.get("messages", [])
        ai_messages = []

        for i, message in enumerate(messages):
            # Skip the initial system and human messages
            if i < 2:
                continue

            if hasattr(message, 'type'):
                if message.type == 'ai':
                    ai_messages.append(message)

                    # Check if this is a thinking step (contains reasoning) or tool call
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        # This is an Action step
                        for tool_call in message.tool_calls:
                            thinking_steps.append({
                                "type":
                                "action",
                                "tool_name":
                                tool_call.get("name", "unknown_tool"),
                                "tool_input":
                                tool_call.get("args", {}),
                                "content":
                                f"Using tool: {tool_call.get('name', 'unknown_tool')}"
                            })
                    elif hasattr(message, 'content'
                                 ) and message.content and not final_response:
                        # Check if this looks like a thought based on reasoning keywords
                        content_text = str(message.content)
                        if any(keyword in content_text.lower() for keyword in [
                                'think', 'need to', 'should', 'let me',
                                'i will', 'analyze', 'consider', 'plan'
                        ]):
                            thinking_steps.append({
                                "type": "thought",
                                "content": content_text
                            })

                elif message.type == 'tool':
                    # This is a tool response (Action Input result)
                    tool_content = str(message.content)
                    thinking_steps.append({
                        "type":
                        "action_result",
                        "content":
                        tool_content,
                        "tool_name":
                        getattr(message, 'name', 'unknown_tool')
                    })

                    # Check if this tool result contains a generated file
                    tool_name = getattr(message, 'name', 'unknown_tool')
                    if any(keyword in tool_name.lower() for keyword in ['plot', 'create', 'generate']) and \
                       any(keyword in tool_content.lower() for keyword in ['created', 'saved', 'success']):
                        extracted_filename = self.extract_filename_from_tool_output(
                            tool_content)
                        # Only add to generated_files if we successfully extracted a proper filename
                        if extracted_filename != tool_content and extracted_filename.lower(
                        ).endswith(('.png', '.jpg', '.jpeg', '.svg')):
                            generated_files.append({
                                "filename":
                                extracted_filename,
                                "filepath":
                                f"output/{extracted_filename}",
                                "type":
                                "plot",
                                "relatedLasFile":
                                selected_las_file
                            })

        # Find the final response - use the last AI message without tool calls
        for message in reversed(ai_messages):
            if hasattr(message, 'content') and message.content and not (
                    hasattr(message, 'tool_calls') and message.tool_calls):
                final_response = str(message.content)
                break

        # Fallback: if no final response found, use the last AI message content
        if not final_response and ai_messages:
            last_ai_message = ai_messages[-1]
            if hasattr(last_ai_message, 'content') and last_ai_message.content:
                final_response = str(last_ai_message.content)

        # Note: Generated files are now detected and processed from tool responses above

        return {
            "content": final_response,
            "thinking_steps": thinking_steps,
            "metadata": {
                "tool_usage": True,
                "selected_file": selected_las_file,
                "processing_time": datetime.now().isoformat()
            },
            "generated_files": generated_files
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
            print(
                "Usage: python langchain-agent.py test <provider> <model> <endpoint_url>"
            )
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
            print(
                "Usage: python langchain-agent.py process <content> <selected_file> <config_json>"
            )
            sys.exit(1)

        content = sys.argv[2]
        selected_file = sys.argv[3]
        config_json = sys.argv[4]

        try:
            config = json.loads(config_json)
            agent = LangChainMCPAgent(config.get("provider", "ollama"),
                                      config.get("model", "llama3.2:1b"),
                                      config.get("endpointUrl", ""))

            result = await agent.process_message(content, selected_file)
            await agent.cleanup()

            print(json.dumps(result))
        except Exception as e:
            error_result = {
                "content": f"Processing error: {str(e)}",
                "metadata": {
                    "error": True
                }
            }
            print(json.dumps(error_result))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
