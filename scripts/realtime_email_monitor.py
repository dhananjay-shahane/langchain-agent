#!/usr/bin/env python3
"""
Real-time Gmail Monitor using IMAPClient with IMAP IDLE for instant email notifications.
This replaces the flaky custom IMAP implementation with a proven professional library.
"""

import os
import json
import time
import threading
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
from email import message_from_bytes
from email.header import decode_header
from imapclient import IMAPClient
from imapclient.exceptions import IMAPClientError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/email_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RealTimeEmailMonitor:
    def __init__(self):
        """Initialize the real-time email monitor with IMAPClient."""
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.imap_host = os.getenv('IMAP_HOST', 'imap.gmail.com')
        self.api_base_url = os.getenv('API_BASE_URL', 'http://localhost:5000')
        
        if not self.email_user or not self.email_password:
            raise ValueError("EMAIL_USER and EMAIL_PASSWORD environment variables are required")
        
        self.server = None
        self.running = False
        self.reconnect_delay = 30  # seconds
        self.idle_timeout = 600    # 10 minutes
        
        # Create directories
        os.makedirs('data/emails', exist_ok=True)
        os.makedirs('data/attachments', exist_ok=True)
        
        logger.info(f"Real-time email monitor initialized for {self.email_user}")

    def connect(self) -> bool:
        """Connect to Gmail using IMAPClient with proper SSL."""
        try:
            self.server = IMAPClient(self.imap_host, use_uid=True, ssl=True)
            self.server.login(self.email_user, self.email_password)
            self.server.select_folder("INBOX")
            logger.info(f"✅ Connected to {self.imap_host} with IMAPClient")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            return False

    def disconnect(self):
        """Clean disconnect from IMAP server."""
        if self.server:
            try:
                if self.server.has_capability('IDLE'):
                    self.server.idle_done()
                self.server.logout()
                logger.info("📡 Disconnected from IMAP server")
            except:
                pass
            self.server = None

    def decode_header_value(self, value: str) -> str:
        """Decode email header values properly."""
        if not value:
            return ""
        
        decoded_parts = decode_header(value)
        header_value = ""
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                if encoding:
                    try:
                        header_value += part.decode(encoding)
                    except:
                        header_value += part.decode('utf-8', errors='ignore')
                else:
                    header_value += part.decode('utf-8', errors='ignore')
            else:
                header_value += str(part)
        
        return header_value.strip()

    def extract_attachments(self, email_message, email_uid: str) -> List[Dict[str, Any]]:
        """Extract and save attachments from email."""
        attachments = []
        
        for part in email_message.walk():
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if filename:
                    filename = self.decode_header_value(filename)
                    
                    # Save attachment
                    attachment_dir = Path(f'data/attachments/{email_uid}')
                    attachment_dir.mkdir(parents=True, exist_ok=True)
                    
                    attachment_path = attachment_dir / filename
                    
                    try:
                        with open(attachment_path, 'wb') as f:
                            f.write(part.get_payload(decode=True))
                        
                        # Check if it's a LAS file
                        is_las_file = filename.lower().endswith('.las')
                        
                        attachment_info = {
                            'filename': filename,
                            'filepath': str(attachment_path),
                            'size': os.path.getsize(attachment_path),
                            'is_las_file': is_las_file,
                            'content_type': part.get_content_type()
                        }
                        
                        attachments.append(attachment_info)
                        logger.info(f"📎 Saved attachment: {filename}")
                        
                        # If it's a LAS file, copy to data directory and add to database
                        if is_las_file:
                            las_path = Path(f'data/{filename}')
                            import shutil
                            shutil.copy2(attachment_path, las_path)
                            
                            # Add to LAS files via API
                            try:
                                las_data = {
                                    'filename': filename,
                                    'filepath': str(las_path),
                                    'size': str(os.path.getsize(las_path)),
                                    'source': 'email',
                                    'processed': False
                                }
                                
                                response = requests.post(
                                    f"{self.api_base_url}/api/files/las",
                                    json=las_data,
                                    headers={'Content-Type': 'application/json'}
                                )
                                
                                if response.status_code == 200:
                                    logger.info(f"🎯 Added LAS file to database: {filename}")
                                else:
                                    logger.error(f"❌ Failed to add LAS file to database: {response.status_code}")
                                    
                            except Exception as e:
                                logger.error(f"❌ Error adding LAS file to database: {e}")
                        
                    except Exception as e:
                        logger.error(f"❌ Error saving attachment {filename}: {e}")
        
        return attachments

    def process_email(self, email_uid: str, email_data: bytes) -> Dict[str, Any]:
        """Process email and extract all relevant data."""
        try:
            email_message = message_from_bytes(email_data)
            
            # Extract email headers
            sender = self.decode_header_value(email_message.get('From', ''))
            subject = self.decode_header_value(email_message.get('Subject', ''))
            date_str = email_message.get('Date', '')
            
            # Parse date
            received_at = datetime.now()
            if date_str:
                try:
                    from email.utils import parsedate_to_datetime
                    received_at = parsedate_to_datetime(date_str)
                except:
                    pass
            
            # Extract body
            body = ""
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                        except:
                            pass
            else:
                try:
                    body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    body = str(email_message.get_payload())
            
            # Extract attachments
            attachments = self.extract_attachments(email_message, email_uid)
            
            # Create email data matching the API schema
            email_data = {
                'uid': email_uid,
                'sender': sender,
                'subject': subject,
                'body': body,
                'hasAttachments': len(attachments) > 0,
                'attachments': attachments,
                'processed': False,
                'receivedAt': received_at.isoformat() if received_at else datetime.now().isoformat()
            }
            
            # Save email as JSON
            email_file = Path(f'data/emails/{email_uid}.json')
            with open(email_file, 'w', encoding='utf-8') as f:
                json.dump(email_data, f, indent=2, default=str)
            
            logger.info(f"✉️  Processed: '{subject}' from {sender}")
            return email_data
            
        except Exception as e:
            logger.error(f"❌ Error processing email {email_uid}: {e}")
            return None

    def send_to_api(self, email_data: Dict[str, Any]) -> bool:
        """Send email data to the backend API."""
        try:
            response = requests.post(
                f"{self.api_base_url}/api/emails",
                json=email_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"🚀 Sent to API: {email_data['subject']}")
                return True
            else:
                logger.error(f"❌ API error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending to API: {e}")
            return False

    def fetch_new_messages(self):
        """Fetch and process newly arrived messages WITHOUT marking them as seen."""
        try:
            # Get ALL recent messages (not just unseen) to catch new ones
            messages = self.server.search(['ALL'])
            
            if messages:
                recent_messages = messages[-10:]  # Check last 10 messages for new ones
                logger.info(f"📬 Checking {len(recent_messages)} recent messages for new emails")
                
                for msg_id in recent_messages:
                    try:
                        # Fetch email WITHOUT marking as seen using BODY.PEEK[]
                        msg_data = self.server.fetch([msg_id], ['BODY.PEEK[]', 'FLAGS'])
                        
                        if msg_id in msg_data:
                            # Check if we've already processed this email
                            email_uid = str(msg_id)
                            email_file = Path(f'data/emails/{email_uid}.json')
                            
                            if not email_file.exists():
                                # This is a new email - process it
                                logger.info(f"🆕 Processing NEW email ID: {email_uid}")
                                email_data = self.process_email(email_uid, msg_data[msg_id][b'BODY[]'])
                                
                                if email_data:
                                    # Send to API
                                    self.send_to_api(email_data)
                            
                    except Exception as e:
                        logger.error(f"❌ Error processing message {msg_id}: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error fetching messages: {e}")

    def handle_idle_responses(self, responses):
        """Handle IMAP IDLE notifications."""
        for response in responses:
            if b'EXISTS' in response:
                logger.info("🔔 NEW EMAIL DETECTED! Processing immediately...")
                self.fetch_new_messages()
            elif b'EXPUNGE' in response:
                logger.info("🗑️  Email deleted")

    def start_realtime_monitoring(self):
        """Start real-time monitoring with automatic reconnection."""
        logger.info("🚀 Starting REAL-TIME email monitoring...")
        
        while self.running:
            try:
                if not self.connect():
                    logger.error(f"⏳ Reconnecting in {self.reconnect_delay} seconds...")
                    time.sleep(self.reconnect_delay)
                    continue
                
                # Check for existing unseen emails first
                self.fetch_new_messages()
                
                # Start IDLE mode for instant notifications
                self.server.idle()
                logger.info("👁️  IDLE mode activated - listening for instant notifications...")
                
                while self.running:
                    try:
                        # Wait for notifications with timeout
                        responses = self.server.idle_check(timeout=self.idle_timeout)
                        
                        if responses:
                            self.handle_idle_responses(responses)
                        else:
                            # Refresh IDLE to keep connection alive
                            logger.info("🔄 Refreshing IDLE connection...")
                            self.server.idle_done()
                            self.server.idle()
                            
                    except IMAPClientError as e:
                        logger.error(f"❌ IMAP error: {e}")
                        break
                    except Exception as e:
                        logger.error(f"❌ Unexpected error in IDLE loop: {e}")
                        break
                
            except KeyboardInterrupt:
                logger.info("⏹️  Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Connection error: {e}")
                time.sleep(self.reconnect_delay)
            finally:
                self.disconnect()

    def start_monitoring(self):
        """Public method to start monitoring."""
        self.running = True
        return self.start_realtime_monitoring()

    def stop_monitoring(self):
        """Stop the email monitoring process."""
        logger.info("⏹️  Stopping email monitoring...")
        self.running = False
        self.disconnect()

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("📡 Shutdown signal received")
    if 'monitor' in globals():
        monitor.stop_monitoring()
    sys.exit(0)

def main():
    """Main entry point."""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create and start email monitor
        global monitor
        monitor = RealTimeEmailMonitor()
        
        logger.info("🚀 Starting REAL-TIME Email Monitoring Service...")
        logger.info("📧 Will detect new emails INSTANTLY using IMAP IDLE")
        monitor.start_monitoring()
        
    except KeyboardInterrupt:
        logger.info("⌨️  Keyboard interrupt received")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
    finally:
        if 'monitor' in globals():
            monitor.stop_monitoring()

if __name__ == "__main__":
    main()