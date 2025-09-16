#!/usr/bin/env python3
"""
MCP Email Client Script - Bridge between Node.js routes and EmailAgent
This script provides the command-line interface expected by the routes.ts
"""
import sys
import json
import asyncio
import os
import importlib.util
from pathlib import Path

# Load the email-agent.py module
current_dir = Path(__file__).parent
email_agent_path = current_dir / "email-agent.py"

spec = importlib.util.spec_from_file_location("email_agent", email_agent_path)
email_agent_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(email_agent_module)

EmailAgent = email_agent_module.EmailAgent


async def process_email_command(email_json: str) -> None:
    """Process email using the EmailAgent and output JSON response"""
    try:
        # Parse the email data
        email_data = json.loads(email_json)
        
        # Create and initialize the EmailAgent
        agent = EmailAgent()
        result = await agent.process_email(email_data)
        
        # Output the result as JSON
        print(json.dumps(result))
        
    except json.JSONDecodeError as e:
        error_result = {
            'success': False,
            'error': f'Invalid JSON data: {str(e)}',
            'response': 'Failed to parse email data'
        }
        print(json.dumps(error_result))
        sys.exit(1)
        
    except Exception as e:
        error_result = {
            'success': False,
            'error': str(e),
            'response': 'Email processing system encountered an error'
        }
        print(json.dumps(error_result))
        sys.exit(1)


async def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) < 2:
        print(json.dumps({
            'success': False,
            'error': 'No command specified',
            'response': 'Usage: python mcp_email_client.py <command> [args...]'
        }))
        sys.exit(1)

    command = sys.argv[1]

    if command == "process_email":
        if len(sys.argv) < 3:
            print(json.dumps({
                'success': False,
                'error': 'No email data provided',
                'response': 'Usage: python mcp_email_client.py process_email <json_data>'
            }))
            sys.exit(1)
        
        email_json = sys.argv[2]
        await process_email_command(email_json)
        
    else:
        print(json.dumps({
            'success': False,
            'error': f'Unknown command: {command}',
            'response': 'Supported commands: process_email'
        }))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())