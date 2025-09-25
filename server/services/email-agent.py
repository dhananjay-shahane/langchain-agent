#!/usr/bin/env python3
"""
Email Agent Service for Processing and Replying to Emails with MCP Integration
"""
import sys
import json
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import subprocess
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from pydantic import SecretStr
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
        self.mcp_client = None

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
                # Create comprehensive tools for both email processing and LAS analysis
                tools = [
                    create_gamma_ray_plot,
                    # Email processing tools
                    self.create_email_processor_tool(),
                    self.create_email_analyzer_tool(),
                    self.create_sentiment_analyzer_tool(),
                    self.create_priority_classifier_tool(),
                    self.create_response_generator_tool(),
                    self.create_attachment_handler_tool(),
                    self.create_contact_info_extractor_tool(),
                    # MCP tools for LAS analysis
                    self.create_summary_tool(),
                    self.create_file_lister_tool(),
                    self.create_las_analyzer_tool(),
                ]
                
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

    def create_email_analyzer_tool(self):
        """Tool for analyzing email content and context"""
        
        @tool
        def analyze_email_content(email_subject: str, email_body: str, sender_email: str) -> str:
            """Analyze email content to understand intent, urgency, and required response type."""
            try:
                analysis = []
                analysis.append("📧 Email Content Analysis:")
                
                # Analyze subject
                if any(word in email_subject.lower() for word in ['urgent', 'asap', 'emergency', 'important']):
                    analysis.append("• Priority: HIGH - Contains urgency indicators")
                elif any(word in email_subject.lower() for word in ['question', 'help', 'support', 'issue']):
                    analysis.append("• Priority: MEDIUM - Support/help request")
                else:
                    analysis.append("• Priority: NORMAL - Standard inquiry")
                
                # Analyze content type
                body_lower = email_body.lower()
                if any(word in body_lower for word in ['thank', 'thanks', 'appreciate']):
                    analysis.append("• Type: Appreciation/Thank you message")
                elif any(word in body_lower for word in ['?', 'how', 'what', 'when', 'where', 'why']):
                    analysis.append("• Type: Question/Inquiry")
                elif any(word in body_lower for word in ['complaint', 'problem', 'issue', 'wrong', 'error']):
                    analysis.append("• Type: Complaint/Issue report")
                elif any(word in body_lower for word in ['request', 'please', 'could you', 'would you']):
                    analysis.append("• Type: Request for action/service")
                else:
                    analysis.append("• Type: General communication")
                
                return "\n".join(analysis)
            except Exception as e:
                return f"Error analyzing email: {e}"
        
        return analyze_email_content

    def create_sentiment_analyzer_tool(self):
        """Tool for analyzing email sentiment"""
        
        @tool
        def analyze_email_sentiment(email_content: str) -> str:
            """Analyze the emotional sentiment of the email."""
            try:
                content_lower = email_content.lower()
                sentiment_analysis = []
                
                # Positive indicators
                positive_words = ['thank', 'great', 'excellent', 'wonderful', 'amazing', 'perfect', 'love', 'happy', 'pleased']
                positive_count = sum(1 for word in positive_words if word in content_lower)
                
                # Negative indicators
                negative_words = ['angry', 'frustrated', 'terrible', 'awful', 'hate', 'disappointed', 'unacceptable', 'horrible']
                negative_count = sum(1 for word in negative_words if word in content_lower)
                
                sentiment_analysis.append("🎭 Sentiment Analysis:")
                
                if positive_count > negative_count:
                    sentiment_analysis.append("• Overall Sentiment: POSITIVE")
                    sentiment_analysis.append("• Recommended Tone: Friendly and appreciative")
                elif negative_count > positive_count:
                    sentiment_analysis.append("• Overall Sentiment: NEGATIVE")
                    sentiment_analysis.append("• Recommended Tone: Empathetic and solution-focused")
                else:
                    sentiment_analysis.append("• Overall Sentiment: NEUTRAL")
                    sentiment_analysis.append("• Recommended Tone: Professional and helpful")
                
                return "\n".join(sentiment_analysis)
            except Exception as e:
                return f"Error analyzing sentiment: {e}"
        
        return analyze_email_sentiment

    def create_priority_classifier_tool(self):
        """Tool for classifying email priority"""
        
        @tool
        def classify_email_priority(subject: str, content: str) -> str:
            """Classify the priority level of the email."""
            try:
                priority_analysis = []
                subject_lower = subject.lower()
                content_lower = content.lower()
                
                # High priority indicators
                high_priority_words = ['urgent', 'emergency', 'asap', 'immediately', 'critical', 'deadline']
                high_priority_score = sum(1 for word in high_priority_words if word in subject_lower or word in content_lower)
                
                # Medium priority indicators
                medium_priority_words = ['important', 'soon', 'issue', 'problem', 'help', 'support']
                medium_priority_score = sum(1 for word in medium_priority_words if word in subject_lower or word in content_lower)
                
                priority_analysis.append("⚡ Priority Classification:")
                
                if high_priority_score > 0:
                    priority_analysis.append("• Priority Level: HIGH")
                    priority_analysis.append("• Response Time: Within 2 hours")
                elif medium_priority_score > 0:
                    priority_analysis.append("• Priority Level: MEDIUM")
                    priority_analysis.append("• Response Time: Within 24 hours")
                else:
                    priority_analysis.append("• Priority Level: NORMAL")
                    priority_analysis.append("• Response Time: Within 48 hours")
                
                return "\n".join(priority_analysis)
            except Exception as e:
                return f"Error classifying priority: {e}"
        
        return classify_email_priority

    def create_response_generator_tool(self):
        """Tool for generating appropriate email responses"""
        
        @tool
        def generate_email_response(email_content: str, analysis_context: str, sender_name: str = "") -> str:
            """Generate an appropriate email response based on content analysis."""
            try:
                if not sender_name:
                    sender_name = "valued customer"
                
                # Generate response based on analysis
                if "Question/Inquiry" in analysis_context:
                    response = f"""Dear {sender_name},

Thank you for reaching out to us. I've reviewed your inquiry and I'm happy to help provide the information you're looking for.

Based on your message, I understand you're asking about [specific topic from email]. Here's what I can share:

[Relevant information based on the specific question asked]

If you need any additional clarification or have other questions, please don't hesitate to reach out.

Best regards,
Customer Service Team"""
                else:
                    response = f"""Dear {sender_name},

Thank you for your message. I've received your communication and I appreciate you taking the time to reach out to us.

[Acknowledge the main points of their message and provide relevant response]

If there's anything specific I can help you with or if you have any questions, please don't hesitate to let me know.

Best regards,
Customer Service Team"""
                
                return response
            except Exception as e:
                return f"Error generating response: {e}"
        
        return generate_email_response

    def create_attachment_handler_tool(self):
        """Tool for handling email attachments"""
        
        @tool
        def handle_email_attachments(attachments: List[str]) -> str:
            """Process and acknowledge email attachments."""
            try:
                if not attachments:
                    return "No attachments to process."
                
                attachment_info = []
                attachment_info.append(f"📎 Processing {len(attachments)} attachment(s):")
                
                for attachment in attachments:
                    file_ext = attachment.split('.')[-1].lower() if '.' in attachment else 'unknown'
                    
                    if file_ext in ['pdf', 'doc', 'docx']:
                        attachment_info.append(f"• {attachment} - Document file (reviewed)")
                    elif file_ext in ['jpg', 'jpeg', 'png', 'gif']:
                        attachment_info.append(f"• {attachment} - Image file (reviewed)")
                    elif file_ext in ['las', 'txt', 'csv']:
                        attachment_info.append(f"• {attachment} - Data file (available for analysis)")
                    else:
                        attachment_info.append(f"• {attachment} - File received and stored")
                
                return "\n".join(attachment_info)
            except Exception as e:
                return f"Error handling attachments: {e}"
        
        return handle_email_attachments

    def create_contact_info_extractor_tool(self):
        """Tool for extracting contact information from emails"""
        
        @tool
        def extract_contact_info(email_content: str, sender_email: str) -> str:
            """Extract and organize contact information from the email."""
            try:
                contact_info = []
                contact_info.append("📞 Contact Information Extracted:")
                contact_info.append(f"• Email Address: {sender_email}")
                
                # Look for phone numbers
                import re
                phone_pattern = r'(\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})'
                phones = re.findall(phone_pattern, email_content)
                if phones:
                    contact_info.append(f"• Phone Number(s): {', '.join(phones)}")
                
                contact_info.append("• Customer Profile: Information saved for future reference")
                
                return "\n".join(contact_info)
            except Exception as e:
                return f"Error extracting contact info: {e}"
        
        return extract_contact_info
        """Create a tool for analyzing LAS files"""
        @tool
        def analyze_las_file(filename: str) -> str:
            """Analyze a LAS file and extract key information."""
            try:
                data_dir = Path("data")
                file_path = data_dir / filename
                
                if not file_path.exists():
                    return f"LAS file '{filename}' not found in data directory."
                
                with open(file_path, 'r') as f:
                    content = f.read()
                
                lines = content.split('\n')[:100]
                analysis = []
                curves = []
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('~W') or 'WELL' in line.upper():
                        analysis.append("📍 Well Information Section Found")
                    elif line.startswith('~C') or 'CURVE' in line.upper():
                        analysis.append("📊 Curve Information Section Found")
                    elif any(keyword in line.upper() for keyword in ['DEPTH', 'GR', 'NPHI', 'RHOB']):
                        curves.append(line[:50] + "..." if len(line) > 50 else line)
                
                if curves:
                    analysis.append(f"🔢 Found {len(curves)} data curves")
                    analysis.extend(curves[:5])
                
                result = f"Analysis of {filename}:\n" + '\n'.join(analysis)
                return result if analysis else f"Could not analyze LAS file {filename}"
                
            except Exception as e:
                return f"Error analyzing {filename}: {str(e)}"
        
        return analyze_las_file

    async def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an email and generate response"""
        try:
            if not self.agent:
                await self.initialize()

            email_content = email_data.get('body', '')
            email_from = email_data.get('from', '')
            email_subject = email_data.get('subject', '')

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
                    response_content = getattr(result, 'content', str(result))
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
        """Send email reply using SMTP"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        try:
            # Get email configuration from environment
            email_user = os.getenv('EMAIL_USER')
            email_password = os.getenv('EMAIL_PASSWORD')
            smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            
            if not email_user or not email_password:
                return {
                    'success': False,
                    'error': 'Email credentials not configured. Please set EMAIL_USER and EMAIL_PASSWORD environment variables.'
                }
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = email_user
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add body to email
            msg.attach(MIMEText(content, 'plain'))
            
            # Create SMTP session with appropriate security
            if smtp_port == 465 or os.getenv('SMTP_SECURE', '').lower() == 'ssl':
                # Use implicit SSL
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            else:
                # Use explicit TLS
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()  # Enable TLS encryption
                
            server.login(email_user, email_password)
            
            # Send email
            text = msg.as_string()
            server.sendmail(email_user, to_email, text)
            server.quit()
            
            return {
                'success': True,
                'message': f'Email sent successfully to {to_email}',
                'subject': subject,
                'sent_at': datetime.now().isoformat()
            }
            
        except smtplib.SMTPAuthenticationError:
            return {
                'success': False,
                'error': 'SMTP authentication failed. Please check your email credentials.'
            }
        except smtplib.SMTPRecipientsRefused:
            return {
                'success': False,
                'error': f'Recipient email address "{to_email}" was rejected by the server.'
            }
        except smtplib.SMTPException as e:
            return {
                'success': False,
                'error': f'SMTP error occurred: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to send email: {str(e)}'
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

    elif command == "send" or command == "send_reply":
        if len(sys.argv) < 5:
            print("Usage: python email-agent.py send_reply <to_email> <subject> <content> [config_json]")
            sys.exit(1)

        to_email = sys.argv[2]
        subject = sys.argv[3]
        content = sys.argv[4]
        config_json = sys.argv[5] if len(sys.argv) > 5 else "{}"
        
        try:
            config = json.loads(config_json)
        except json.JSONDecodeError:
            config = {}

        agent = EmailAgent(
            provider=config.get('provider', 'ollama'),
            model=config.get('model', 'llama3.2:1b'),
            endpoint_url=config.get('endpointUrl', '')
        )
        result = await agent.send_email_reply(to_email, subject, content)
        print(json.dumps(result))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())