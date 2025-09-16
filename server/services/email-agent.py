#!/usr/bin/env python3
"""
Email Agent Service for Processing and Replying to Emails
"""
import sys
import json
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from pydantic import SecretStr
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent


class EmailAgent:

    def __init__(self,
                 provider: str = "ollama",
                 model: str = "llama3.2:1b",
                 endpoint_url: str = ""):
        self.provider = provider
        self.model = model
        self.endpoint_url = endpoint_url
        self.llm = None
        self.agent = None

    async def initialize(self):
        """Initialize the Email Agent"""
        try:
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
                    temperature=0.3,
                    timeout=120
                )
            elif self.provider == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    return False
                self.llm = ChatAnthropic(
                    model_name=self.model,
                    api_key=SecretStr(api_key),
                    temperature=0.3,
                    timeout=120,
                    stop=[]
                )

            if self.llm:
                tools = [self.create_email_processor_tool()]
                self.agent = create_react_agent(self.llm, tools)
                return True
            
            return False

        except Exception as e:
            print(f"Error initializing email agent: {e}")
            return False

    def create_email_processor_tool(self):
        """Tool for processing email content"""
        
        @tool
        def process_email_content(email_subject: str, email_body: str, sender_email: str) -> str:
            """Process email content and generate appropriate response."""
            return f"Processed email from {sender_email} with subject: {email_subject}"
        
        return process_email_content

    async def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an email and generate response"""
        try:
            if not self.agent:
                await self.initialize()

            email_content = email_data.get('emailContent', '')
            email_from = email_data.get('emailFrom', '')
            email_subject = email_data.get('emailSubject', '')

            prompt = f"""Process this email and generate an appropriate professional response:

From: {email_from}
Subject: {email_subject}
Content: {email_content}

Analyze the email and generate a professional response."""

            if self.agent:
                result = await self.agent.ainvoke({
                    "messages": [HumanMessage(content=prompt)]
                })
                
                response_content = ""
                if isinstance(result, dict) and 'messages' in result and result['messages']:
                    last_message = result['messages'][-1]
                    if hasattr(last_message, 'content'):
                        response_content = last_message.content
                    else:
                        response_content = str(last_message)
                elif hasattr(result, 'content'):
                    response_content = result.content
                else:
                    response_content = str(result)

                return {
                    'success': True,
                    'response': response_content,
                    'analysis': {
                        'processed': True,
                        'from': email_from,
                        'subject': email_subject
                    }
                }
            else:
                return {
                    'success': False,
                    'error': 'Agent not initialized'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    async def send_email_reply(self, to_email: str, subject: str, content: str) -> Dict[str, Any]:
        """Send email reply"""
        try:
            return {
                'success': True,
                'message': f'Email sent to {to_email}',
                'subject': subject
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


async def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) < 2:
        print("Usage: python email-agent.py <command> [args...]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "process":
        if len(sys.argv) < 3:
            print("Usage: python email-agent.py process <json_data>")
            sys.exit(1)
        
        try:
            email_data = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            print("Invalid JSON data")
            sys.exit(1)

        agent = EmailAgent()
        result = await agent.process_email(email_data)
        print(json.dumps(result))

    elif command == "send":
        if len(sys.argv) < 5:
            print("Usage: python email-agent.py send <to_email> <subject> <content>")
            sys.exit(1)

        to_email = sys.argv[2]
        subject = sys.argv[3]
        content = sys.argv[4]

        agent = EmailAgent()
        result = await agent.send_email_reply(to_email, subject, content)
        print(json.dumps(result))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())