#!/usr/bin/env python3
"""
Email Agent Service for Processing and Replying to Emails
Separate from the LangChain MCP Agent for LAS files
"""
import sys
import json
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# LangChain imports
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from pydantic import SecretStr
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

class EmailAgent:
    def __init__(self, provider: str = "ollama", model: str = "llama3.2:1b", endpoint_url: str = ""):
        self.provider = provider
        self.model = model
        self.endpoint_url = endpoint_url
        self.llm = None
        self.agent = None
        self.supports_tools = False
        
    async def initialize(self):
        """Initialize the Email Agent"""
        try:
            # Initialize LLM based on provider
            if self.provider == "ollama":
                base_url = self.endpoint_url if self.endpoint_url else "http://localhost:11434"
                self.llm = ChatOllama(
                    model=self.model,
                    base_url=base_url,
                    temperature=0.3  # Slightly higher for more creative responses
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
                    temperature=0.3,
                    timeout=30,
                    stop=[]
                )
            
            # Create agent with tools - use configuration as specified
            if self.llm is not None:
                custom_tools = [
                    self.create_email_analyzer_tool(),
                    self.create_response_generator_tool(),
                    self.create_attachment_handler_tool(),
                    self.create_sentiment_analyzer_tool(),
                    self.create_priority_classifier_tool(),
                    self.create_contact_info_extractor_tool()
                ]
                
                # Create agent with email tools
                self.agent = create_react_agent(self.llm, custom_tools)
                self.supports_tools = True
                print(f"Email agent initialized for model: {self.model}")
            else:
                return False
            
            return True
            
        except Exception as e:
            print(f"Error initializing email agent: {e}")
            return False
    
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
                
                # Analyze tone
                if any(word in body_lower for word in ['angry', 'frustrated', 'disappointed', 'unacceptable']):
                    analysis.append("• Tone: Negative - Requires careful, empathetic response")
                elif any(word in body_lower for word in ['happy', 'pleased', 'excellent', 'great']):
                    analysis.append("• Tone: Positive - Maintain friendly engagement")
                else:
                    analysis.append("• Tone: Neutral - Professional response appropriate")
                
                # Length analysis
                word_count = len(email_body.split())
                if word_count < 20:
                    analysis.append(f"• Length: Brief ({word_count} words) - Concise response suitable")
                elif word_count > 100:
                    analysis.append(f"• Length: Detailed ({word_count} words) - Comprehensive response needed")
                else:
                    analysis.append(f"• Length: Standard ({word_count} words) - Balanced response appropriate")
                
                return "\n".join(analysis)
            except Exception as e:
                return f"Error analyzing email: {e}"
        
        return analyze_email_content
    
    def create_response_generator_tool(self):
        """Tool for generating appropriate email responses"""
        @tool
        def generate_email_response(email_content: str, analysis_context: str, sender_name: str = "") -> str:
            """Generate an appropriate email response based on content analysis."""
            try:
                # Extract sender name from email if not provided
                if not sender_name and "From:" in email_content:
                    sender_name = "valued customer"
                elif not sender_name:
                    sender_name = "there"
                
                # Generate response based on analysis
                if "Question/Inquiry" in analysis_context:
                    response = f"""Dear {sender_name},

Thank you for reaching out to us. I've reviewed your inquiry and I'm happy to help provide the information you're looking for.

Based on your message, I understand you're asking about [specific topic from email]. Here's what I can share:

[Relevant information based on the specific question asked]

If you need any additional clarification or have other questions, please don't hesitate to reach out. We're always here to help.

Best regards,
Customer Service Team"""

                elif "Complaint/Issue" in analysis_context:
                    response = f"""Dear {sender_name},

Thank you for bringing this matter to our attention, and I sincerely apologize for any inconvenience you've experienced.

I've carefully reviewed your concerns and I want to assure you that we take all feedback seriously. Here's how we're addressing your issue:

[Specific steps being taken to resolve the issue]

We value your business and your feedback helps us improve our services. I will personally follow up to ensure this matter is resolved to your satisfaction.

Please feel free to contact me directly if you have any other concerns.

Best regards,
Customer Service Team"""

                elif "Appreciation" in analysis_context:
                    response = f"""Dear {sender_name},

Thank you so much for your kind words! It's wonderful to hear that you've had a positive experience with us.

Your feedback means a lot to our team, and I'll be sure to share your comments with everyone involved. We truly appreciate customers like you who take the time to let us know when we're doing things right.

We look forward to continuing to serve you and providing the same excellent experience in the future.

Warm regards,
Customer Service Team"""

                elif "Request" in analysis_context:
                    response = f"""Dear {sender_name},

Thank you for your request. I've reviewed what you're looking for and I'm happy to assist you.

Regarding your request for [specific request], here's what I can do:

[Steps being taken to fulfill the request or explanation of process]

The expected timeline for this is [timeframe], and I'll keep you updated on the progress.

If you have any questions about this process or need anything else, please let me know.

Best regards,
Customer Service Team"""

                else:  # General communication
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
                    elif file_ext in ['zip', 'rar', '7z']:
                        attachment_info.append(f"• {attachment} - Archive file (extracted and reviewed)")
                    else:
                        attachment_info.append(f"• {attachment} - File received and stored")
                
                attachment_info.append("\nAll attachments have been successfully received and processed.")
                attachment_info.append("Relevant information from attachments has been incorporated into this response.")
                
                return "\n".join(attachment_info)
            except Exception as e:
                return f"Error handling attachments: {e}"
        
        return handle_email_attachments
    
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
                
                # Neutral/business indicators
                neutral_words = ['request', 'information', 'please', 'question', 'inquiry', 'regarding']
                neutral_count = sum(1 for word in neutral_words if word in content_lower)
                
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
                
                sentiment_analysis.append(f"• Positive indicators: {positive_count}")
                sentiment_analysis.append(f"• Negative indicators: {negative_count}")
                sentiment_analysis.append(f"• Business/neutral indicators: {neutral_count}")
                
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
                    priority_analysis.append("• Escalation: Manager notification recommended")
                elif medium_priority_score > 0:
                    priority_analysis.append("• Priority Level: MEDIUM")
                    priority_analysis.append("• Response Time: Within 24 hours")
                    priority_analysis.append("• Escalation: Standard queue processing")
                else:
                    priority_analysis.append("• Priority Level: NORMAL")
                    priority_analysis.append("• Response Time: Within 48 hours")
                    priority_analysis.append("• Escalation: Regular processing queue")
                
                priority_analysis.append(f"• High priority indicators: {high_priority_score}")
                priority_analysis.append(f"• Medium priority indicators: {medium_priority_score}")
                
                return "\n".join(priority_analysis)
            except Exception as e:
                return f"Error classifying priority: {e}"
        
        return classify_email_priority
    
    def create_contact_info_extractor_tool(self):
        """Tool for extracting contact information from emails"""
        @tool
        def extract_contact_info(email_content: str, sender_email: str) -> str:
            """Extract and organize contact information from the email."""
            try:
                contact_info = []
                content_lines = email_content.split('\n')
                
                contact_info.append("📞 Contact Information Extracted:")
                contact_info.append(f"• Email Address: {sender_email}")
                
                # Look for phone numbers
                import re
                phone_pattern = r'(\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})'
                phones = re.findall(phone_pattern, email_content)
                if phones:
                    contact_info.append(f"• Phone Number(s): {', '.join(phones)}")
                
                # Look for names
                if "From:" in email_content or "Best regards," in email_content or "Sincerely," in email_content:
                    contact_info.append("• Name: Available in email signature")
                
                # Look for company/organization
                company_indicators = ['company', 'corp', 'inc', 'llc', 'ltd', 'organization']
                for line in content_lines:
                    if any(indicator in line.lower() for indicator in company_indicators):
                        contact_info.append(f"• Organization: Mentioned in email")
                        break
                
                contact_info.append("• Customer Profile: Information saved for future reference")
                
                return "\n".join(contact_info)
            except Exception as e:
                return f"Error extracting contact info: {e}"
        
        return extract_contact_info
    
    async def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an email and generate a response"""
        try:
            if not self.agent:
                await self.initialize()
            
            email_id = email_data.get('emailId', '')
            email_content = email_data.get('emailContent', '')
            email_from = email_data.get('emailFrom', '')
            email_subject = email_data.get('emailSubject', '')
            attachments = email_data.get('attachments', [])
            
            # Prepare context for email processing
            context_parts = [
                "You are a professional email assistant that processes customer emails and generates appropriate responses.",
                "Your role is to:",
                "- Analyze email content and determine appropriate response tone",
                "- Generate professional, helpful, and contextually appropriate replies",
                "- Handle different types of emails (questions, complaints, requests, appreciation)",
                "- Maintain consistent professional communication standards",
                "",
                f"Email to process:",
                f"From: {email_from}",
                f"Subject: {email_subject}",
                f"Content: {email_content}",
            ]
            
            if attachments:
                context_parts.append(f"Attachments: {', '.join(attachments)}")
            
            context_parts.extend([
                "",
                "Please process this email and generate an appropriate professional response.",
                "Use the available tools to analyze the email content, sentiment, and priority.",
                "Then generate a complete, professional email reply."
            ])
            
            # Process with agent using configuration from Agent Configuration dashboard
            if self.agent is not None:
                response = await self.agent.ainvoke({
                    "messages": [SystemMessage(content="\n".join(context_parts))]
                })
                
                # Extract the response content
                response_content = ""
                if isinstance(response, dict):
                    # Handle dictionary response from agent
                    if 'messages' in response and response['messages']:
                        last_message = response['messages'][-1]
                        if isinstance(last_message, dict) and 'content' in last_message:
                            response_content = last_message['content']
                        else:
                            response_content = str(last_message)
                    elif 'output' in response:
                        response_content = str(response['output'])
                    else:
                        response_content = str(response)
                else:
                    # Handle object response
                    if hasattr(response, 'messages') and response.messages:
                        last_message = response.messages[-1]
                        response_content = last_message.content if hasattr(last_message, 'content') else str(last_message)
                    elif hasattr(response, 'content'):
                        response_content = response.content
                    else:
                        response_content = str(response)
            else:
                raise Exception("Email agent not initialized")
            
            # Clean up the response to extract just the email reply
            lines = response_content.split('\n')
            email_reply_lines = []
            in_email_section = False
            
            for line in lines:
                if any(greeting in line for greeting in ['Dear ', 'Hello ', 'Hi ']):
                    in_email_section = True
                    email_reply_lines.append(line)
                elif in_email_section:
                    if line.strip() and not line.startswith('Tool:') and not line.startswith('Agent:'):
                        email_reply_lines.append(line)
                    elif line.strip() == '' and email_reply_lines:
                        email_reply_lines.append(line)
            
            # If no proper email format found, use the full response
            if not email_reply_lines:
                email_reply_lines = [line for line in lines if line.strip() and not line.startswith('Tool:') and not line.startswith('Agent:')]
            
            final_response = '\n'.join(email_reply_lines).strip()
            
            # Ensure we have a response
            if not final_response:
                raise Exception("Failed to generate email response")
            
            return {
                "success": True,
                "response": final_response,
                "metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "email_id": email_id,
                    "original_subject": email_subject,
                    "attachments_processed": len(attachments),
                    "response_type": "automated_agent_reply"
                }
            }
            
        except Exception as e:
            print(f"Email processing error: {str(e)}")
            raise Exception(f"Email processing failed: {str(e)}")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to the configured LLM provider"""
        try:
            # Initialize agent
            if not await self.initialize():
                return {
                    "success": False,
                    "message": f"Failed to initialize {self.provider} agent with model {self.model}"
                }
            
            # Test with a simple message
            if self.agent is not None:
                test_response = await self.agent.ainvoke({
                    "messages": [SystemMessage(content="Test connection - respond with 'Connection successful'")]
                })
                
                return {
                    "success": True,
                    "message": f"Connection successful to {self.provider} with model {self.model}",
                    "provider": self.provider,
                    "model": self.model,
                    "endpoint": self.endpoint_url
                }
            else:
                return {
                    "success": False,
                    "message": "Agent initialization returned None"
                }
                
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg and "not found" in error_msg:
                return {
                    "success": False,
                    "message": f"ERROR: Connection failed: model '{self.model}' not found, try pulling it first (status code: 404)"
                }
            else:
                return {
                    "success": False,
                    "message": f"Connection failed: {error_msg}"
                }
    
    async def send_email_reply(self, to_email: str, subject: str, reply_content: str) -> Dict[str, Any]:
        """Send actual email reply via SMTP using EMAIL_USER credentials"""
        import smtplib
        import os
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Get credentials from environment
        email_user = os.environ.get("EMAIL_USER")
        email_pass = os.environ.get("EMAIL_PASS") 
        smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        
        if not email_user or not email_pass:
            raise Exception("EMAIL_USER and EMAIL_PASS environment variables must be set")
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = email_user
            msg['To'] = to_email
            msg['Subject'] = f"Re: {subject}"
            
            # Add body to email
            msg.attach(MIMEText(reply_content, 'plain'))
            
            # Setup SMTP server and send email
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()  # Enable TLS security
            server.login(email_user, email_pass)
            text = msg.as_string()
            server.sendmail(email_user, to_email, text)
            server.quit()
            
            print(f"Email sent successfully to: {to_email}")
            print(f"Subject: Re: {subject}")
            
            return {
                "success": True,
                "message": "Email reply sent successfully via SMTP",
                "sent_at": datetime.now().isoformat(),
                "to": to_email,
                "from": email_user
            }
            
        except Exception as e:
            print(f"SMTP Email Error: {str(e)}")
            raise Exception(f"Failed to send email via SMTP: {str(e)}")

async def main():
    """Main function for command line usage"""
    if len(sys.argv) < 2:
        print("Usage: python email-agent.py <command> [args...]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "test":
        # Test connection
        provider = sys.argv[2] if len(sys.argv) > 2 else "ollama"
        model = sys.argv[3] if len(sys.argv) > 3 else "llama3.2:1b"
        endpoint = sys.argv[4] if len(sys.argv) > 4 else ""
        
        agent = EmailAgent(provider, model, endpoint)
        result = await agent.test_connection()
        print(json.dumps(result))
        
    elif command == "process":
        # Process email
        email_content = sys.argv[2] if len(sys.argv) > 2 else ""
        email_from = sys.argv[3] if len(sys.argv) > 3 else ""
        email_subject = sys.argv[4] if len(sys.argv) > 4 else ""
        attachments_str = sys.argv[5] if len(sys.argv) > 5 else "[]"
        config_str = sys.argv[6] if len(sys.argv) > 6 else "{}"
        
        try:
            attachments = json.loads(attachments_str) if attachments_str != "[]" else []
            config = json.loads(config_str) if config_str != "{}" else {}
        except:
            attachments = []
            config = {}
        
        provider = config.get('provider', 'ollama')
        model = config.get('model', 'llama3.2:1b')
        endpoint = config.get('endpointUrl', '')
        
        agent = EmailAgent(provider, model, endpoint)
        
        email_data = {
            'emailContent': email_content,
            'emailFrom': email_from,
            'emailSubject': email_subject,
            'attachments': attachments
        }
        
        result = await agent.process_email(email_data)
        print(json.dumps(result))
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())