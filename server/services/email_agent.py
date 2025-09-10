#!/usr/bin/env python3
"""
Email Agent Service with LangChain Integration
Monitors emails, extracts data, processes with AI, and saves as JSON
"""

import imaplib
import email
from email.header import decode_header
import json
import smtplib
from email.mime.text import MIMEText
import time
import os
import sys
import logging
import requests
from datetime import datetime
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import LangChain components
try:
    from langchain_openai import OpenAI
    from langchain_anthropic import Anthropic
    from langchain_ollama import OllamaLLM
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    from langchain.schema import HumanMessage
except ImportError as e:
    print(f"LangChain import error: {e}")
    print("Please install required packages: pip install langchain-openai langchain-anthropic langchain-ollama")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/email_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EmailFetcher:
    """Handles IMAP email fetching operations"""
    
    def __init__(self, host, user, password, port=993):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.mail = None
        self.processed_uids = set()
        self._load_processed_uids()

    def _load_processed_uids(self):
        """Load previously processed email UIDs from file"""
        try:
            uid_file = Path('data/processed_email_uids.json')
            if uid_file.exists():
                with open(uid_file, 'r') as f:
                    self.processed_uids = set(json.load(f))
        except Exception as e:
            logger.warning(f"Could not load processed UIDs: {e}")
            self.processed_uids = set()

    def _save_processed_uids(self):
        """Save processed email UIDs to file"""
        try:
            Path('data').mkdir(exist_ok=True)
            with open('data/processed_email_uids.json', 'w') as f:
                json.dump(list(self.processed_uids), f)
        except Exception as e:
            logger.error(f"Could not save processed UIDs: {e}")

    def connect(self):
        """Establish IMAP connection"""
        try:
            if self.mail is not None:
                try:
                    self.mail.logout()
                except:
                    pass
            
            self.mail = imaplib.IMAP4_SSL(self.host, self.port)
            self.mail.login(self.user, self.password)
            self.mail.select("inbox")
            logger.info("Successfully connected to IMAP server")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {e}")
            return False

    def fetch_unseen_emails(self):
        """Fetch new unseen emails that haven't been processed"""
        emails = []
        try:
            # Search for unseen emails
            status, messages = self.mail.search(None, 'UNSEEN')
            if status != "OK":
                return emails

            email_ids = messages[0].split()
            logger.info(f"Found {len(email_ids)} unseen emails")

            for e_id in email_ids:
                try:
                    # Get email UID for tracking
                    status, uid_data = self.mail.fetch(e_id, '(UID)')
                    if status != "OK":
                        continue
                    
                    uid = uid_data[0].decode().split()[2].rstrip(')')
                    
                    # Skip if already processed
                    if uid in self.processed_uids:
                        continue

                    # Fetch email content
                    status, msg_data = self.mail.fetch(e_id, '(RFC822)')
                    if status != "OK":
                        continue

                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            # Extract email data
                            email_data = self._extract_email_data(msg, uid)
                            if email_data:
                                emails.append(email_data)
                                self.processed_uids.add(uid)
                                logger.info(f"Processed email UID: {uid} from {email_data['sender']}")

                except Exception as e:
                    logger.error(f"Error processing email {e_id}: {e}")
                    continue

            # Save processed UIDs
            self._save_processed_uids()

        except Exception as e:
            logger.error(f"Error fetching unseen emails: {e}")

        return emails

    def _extract_email_data(self, msg, uid):
        """Extract structured data from email message"""
        try:
            # Decode sender
            sender = msg['From'] or "Unknown"
            
            # Decode subject
            subject_data = decode_header(msg['Subject'] or "No Subject")[0]
            subject = subject_data[0]
            if isinstance(subject, bytes):
                encoding = subject_data[1] or 'utf-8'
                subject = subject.decode(encoding, errors='ignore')

            # Extract body and attachments
            body = ""
            attachments = []
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_disposition = part.get("Content-Disposition", "")
                    content_type = part.get_content_type()
                    
                    # Extract text body
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                charset = part.get_content_charset() or 'utf-8'
                                body += payload.decode(charset, errors='ignore')
                        except Exception as e:
                            logger.warning(f"Could not decode email body part: {e}")
                    
                    # Track attachments
                    elif "attachment" in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            attachments.append({
                                "filename": filename,
                                "content_type": content_type,
                                "size": len(part.get_payload(decode=True) or b"")
                            })
            else:
                # Single part message
                try:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        charset = msg.get_content_charset() or 'utf-8'
                        body = payload.decode(charset, errors='ignore')
                except Exception as e:
                    logger.warning(f"Could not decode email body: {e}")

            return {
                "uid": uid,
                "sender": sender,
                "subject": subject,
                "body": body.strip(),
                "attachments": attachments,
                "received_at": datetime.now().isoformat(),
                "processed": False,
                "has_attachments": len(attachments) > 0
            }

        except Exception as e:
            logger.error(f"Error extracting email data: {e}")
            return None

    def disconnect(self):
        """Close IMAP connection"""
        try:
            if self.mail:
                self.mail.logout()
                self.mail = None
        except Exception as e:
            logger.warning(f"Error disconnecting from IMAP: {e}")


class EmailProcessor:
    """Processes emails using LangChain agents"""
    
    def __init__(self, agent_config):
        self.agent_config = agent_config
        self.llm = self._create_llm()
        self.chain = self._create_chain()

    def _create_llm(self):
        """Create LLM instance based on agent configuration"""
        provider = self.agent_config.get('provider', 'ollama')
        model = self.agent_config.get('model', 'llama3.2:1b')
        endpoint_url = self.agent_config.get('endpointUrl', 'http://localhost:11434')

        try:
            if provider == 'openai':
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    raise ValueError("OPENAI_API_KEY environment variable required for OpenAI provider")
                return OpenAI(api_key=api_key, model=model, temperature=0.3)
            
            elif provider == 'anthropic':
                api_key = os.getenv('ANTHROPIC_API_KEY')
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY environment variable required for Anthropic provider")
                return Anthropic(api_key=api_key, model=model, temperature=0.3)
            
            elif provider == 'ollama':
                return OllamaLLM(
                    base_url=endpoint_url,
                    model=model,
                    temperature=0.3
                )
            
            else:
                raise ValueError(f"Unsupported provider: {provider}")

        except Exception as e:
            logger.error(f"Failed to create LLM: {e}")
            raise

    def _create_chain(self):
        """Create LangChain processing chain"""
        template = """You are an intelligent email analysis agent. Analyze the following email and extract key information:

Email Details:
- From: {sender}
- Subject: {subject}
- Body: {body}
- Attachments: {attachments}

Please provide a structured analysis including:
1. Email category/type (business, personal, support, etc.)
2. Key topics or subjects mentioned
3. Sentiment analysis (positive, negative, neutral)
4. Any action items or requests mentioned
5. Priority level (high, medium, low)
6. Brief summary (2-3 sentences)

Respond in JSON format with the above fields."""

        prompt = PromptTemplate(
            input_variables=["sender", "subject", "body", "attachments"],
            template=template
        )
        
        return LLMChain(llm=self.llm, prompt=prompt)

    def process_email(self, email_data):
        """Process email with LangChain agent"""
        try:
            # Format attachments for prompt
            attachments_str = ", ".join([att["filename"] for att in email_data.get("attachments", [])])
            if not attachments_str:
                attachments_str = "None"

            # Run LangChain analysis
            analysis = self.chain.run(
                sender=email_data["sender"],
                subject=email_data["subject"],
                body=email_data["body"][:2000],  # Limit body length
                attachments=attachments_str
            )

            # Try to parse JSON response
            try:
                analysis_data = json.loads(analysis)
            except json.JSONDecodeError:
                # If not valid JSON, create structured response
                analysis_data = {
                    "category": "unknown",
                    "topics": [],
                    "sentiment": "neutral",
                    "action_items": [],
                    "priority": "medium",
                    "summary": analysis[:200] + "..." if len(analysis) > 200 else analysis
                }

            # Add analysis to email data
            email_data["ai_analysis"] = analysis_data
            email_data["processed"] = True
            email_data["processed_at"] = datetime.now().isoformat()

            logger.info(f"Successfully processed email from {email_data['sender']}")
            return email_data

        except Exception as e:
            logger.error(f"Error processing email with LangChain: {e}")
            email_data["ai_analysis"] = {"error": str(e)}
            email_data["processed"] = False
            return email_data


class EmailAgent:
    """Main email agent orchestrator"""
    
    def __init__(self):
        self.fetcher = None
        self.processor = None
        self.running = False
        self.config = self._load_config()

    def _load_config(self):
        """Load configuration from API and environment"""
        config = {
            # Default configuration
            'imap_host': 'imap.gmail.com',
            'smtp_host': 'smtp.gmail.com',
            'email_address': None,
            'email_password': None,
            'imap_port': 993,
            'provider': 'ollama',
            'model': 'llama3.2:1b',
            'endpointUrl': 'http://localhost:11434',
            'poll_interval': 20,
            'max_emails_per_batch': 10
        }
        
        # Try to load email config from API
        try:
            response = requests.get('http://localhost:5000/api/email/config', timeout=5)
            if response.status_code == 200:
                email_config = response.json()
                if email_config:
                    config.update({
                        'imap_host': email_config.get('imapHost', 'imap.gmail.com'),
                        'smtp_host': email_config.get('smtpHost', 'smtp.gmail.com'),
                        'email_address': email_config.get('emailAddress'),
                        'email_password': email_config.get('emailPassword'),
                        'imap_port': int(email_config.get('imapPort', '993')),
                        'poll_interval': int(email_config.get('pollInterval', '20'))
                    })
                    logger.info("Loaded email configuration from API")
        except Exception as e:
            logger.warning(f"Could not load email config from API: {e}")
        
        # Try to load agent config from API
        try:
            response = requests.get('http://localhost:5000/api/agent/config', timeout=5)
            if response.status_code == 200:
                agent_config = response.json()
                if agent_config:
                    config.update({
                        'provider': agent_config.get('provider', 'ollama'),
                        'model': agent_config.get('model', 'llama3.2:1b'),
                        'endpointUrl': agent_config.get('endpointUrl', 'http://localhost:11434')
                    })
                    logger.info("Loaded agent configuration from API")
        except Exception as e:
            logger.warning(f"Could not load agent config from API: {e}")
        
        # Override with environment variables if present
        if os.getenv('EMAIL_ADDRESS'):
            config['email_address'] = os.getenv('EMAIL_ADDRESS')
        if os.getenv('EMAIL_PASSWORD'):
            config['email_password'] = os.getenv('EMAIL_PASSWORD')
        if os.getenv('EMAIL_IMAP_HOST'):
            config['imap_host'] = os.getenv('EMAIL_IMAP_HOST')
        if os.getenv('EMAIL_SMTP_HOST'):
            config['smtp_host'] = os.getenv('EMAIL_SMTP_HOST')
        if os.getenv('EMAIL_IMAP_PORT'):
            config['imap_port'] = int(os.getenv('EMAIL_IMAP_PORT'))
        if os.getenv('EMAIL_POLL_INTERVAL'):
            config['poll_interval'] = int(os.getenv('EMAIL_POLL_INTERVAL'))
        if os.getenv('MAX_EMAILS_PER_BATCH'):
            config['max_emails_per_batch'] = int(os.getenv('MAX_EMAILS_PER_BATCH'))
            
        return config

    def initialize(self):
        """Initialize email agent components"""
        try:
            # Validate email configuration
            if not self.config['email_address'] or not self.config['email_password']:
                raise ValueError("EMAIL_ADDRESS and EMAIL_PASSWORD environment variables are required")

            # Initialize fetcher
            self.fetcher = EmailFetcher(
                self.config['imap_host'],
                self.config['email_address'],
                self.config['email_password'],
                self.config['imap_port']
            )

            # Initialize processor
            self.processor = EmailProcessor(self.config)

            # Test connection
            if not self.fetcher.connect():
                raise ConnectionError("Failed to connect to email server")

            logger.info("Email agent initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize email agent: {e}")
            return False

    def save_email_as_json(self, email_data):
        """Save processed email data as JSON file"""
        try:
            # Create emails directory
            emails_dir = Path('data/emails')
            emails_dir.mkdir(exist_ok=True)

            # Create safe filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_subject = email_data['subject'][:50].replace(" ", "_")
            safe_subject = "".join(c for c in safe_subject if c.isalnum() or c in ("_", "-"))
            filename = f"{emails_dir}/email_{timestamp}_{safe_subject}.json"

            # Save email data
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(email_data, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"Saved email to {filename}")
            return filename

        except Exception as e:
            logger.error(f"Error saving email JSON: {e}")
            return None

    def process_emails(self):
        """Process new emails once"""
        try:
            if not self.fetcher.connect():
                logger.error("Could not connect to email server")
                return []

            # Fetch new emails
            new_emails = self.fetcher.fetch_unseen_emails()
            processed_emails = []

            if new_emails:
                logger.info(f"Processing {len(new_emails)} new emails")
                
                for email_data in new_emails[:self.config['max_emails_per_batch']]:
                    try:
                        # Process with LangChain
                        processed_email = self.processor.process_email(email_data)
                        
                        # Save as JSON
                        json_file = self.save_email_as_json(processed_email)
                        if json_file:
                            processed_email['json_file'] = json_file

                        processed_emails.append(processed_email)

                    except Exception as e:
                        logger.error(f"Error processing individual email: {e}")
                        continue

            self.fetcher.disconnect()
            return processed_emails

        except Exception as e:
            logger.error(f"Error in process_emails: {e}")
            return []

    def run_continuous(self):
        """Run email monitoring continuously"""
        self.running = True
        logger.info(f"Starting continuous email monitoring (polling every {self.config['poll_interval']} seconds)")

        while self.running:
            try:
                processed_emails = self.process_emails()
                if processed_emails:
                    logger.info(f"Processed {len(processed_emails)} emails in this cycle")

            except Exception as e:
                logger.error(f"Error in monitoring cycle: {e}")

            # Wait before next poll
            time.sleep(self.config['poll_interval'])

    def stop(self):
        """Stop continuous monitoring"""
        self.running = False
        if self.fetcher:
            self.fetcher.disconnect()
        logger.info("Email agent stopped")


def main():
    """Main entry point"""
    agent = EmailAgent()
    
    if not agent.initialize():
        logger.error("Failed to initialize email agent")
        sys.exit(1)

    try:
        # Check if running in single-shot mode
        if len(sys.argv) > 1 and sys.argv[1] == '--once':
            processed_emails = agent.process_emails()
            print(f"Processed {len(processed_emails)} emails")
        else:
            # Run continuously
            agent.run_continuous()
    
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, stopping...")
        agent.stop()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        agent.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()