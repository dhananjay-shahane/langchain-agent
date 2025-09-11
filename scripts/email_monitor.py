#!/usr/bin/env python3
"""
IMAP Email Monitor with IDLE support for instant email notifications.
This script monitors an email account for new emails and processes attachments.
"""

import os
import imaplib
import email
import json
import time
import threading
import logging
import signal
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests
from pathlib import Path

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

class EmailMonitor:
    def __init__(self):
        """Initialize the email monitor with credentials from environment variables."""
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.imap_host = os.getenv('IMAP_HOST', 'imap.gmail.com')
        self.imap_port = int(os.getenv('IMAP_PORT', '993'))
        self.api_base_url = os.getenv('API_BASE_URL', 'http://localhost:5000')
        
        if not self.email_user or not self.email_password:
            raise ValueError("EMAIL_USER and EMAIL_PASSWORD environment variables are required")
        
        self.mail = None
        self.running = False
        self.idle_timeout = 300  # 5 minutes
        
        # Create directories
        os.makedirs('data/emails', exist_ok=True)
        os.makedirs('data/attachments', exist_ok=True)
        
        logger.info(f"Email monitor initialized for {self.email_user}")

    def connect(self) -> bool:
        """Connect to the IMAP server."""
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            self.mail.login(self.email_user, self.email_password)
            self.mail.select('INBOX')
            logger.info(f"Connected to {self.imap_host}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {e}")
            return False

    def disconnect(self):
        """Disconnect from the IMAP server."""
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
                logger.info("Disconnected from IMAP server")
            except:
                pass
            self.mail = None

    def decode_header_value(self, value: str) -> str:
        """Decode email header values."""
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

    def extract_attachments(self, email_message: email.message.Message, email_uid: str) -> List[Dict[str, Any]]:
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
                        logger.info(f"Saved attachment: {filename}")
                        
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
                                    logger.info(f"Added LAS file to database: {filename}")
                                else:
                                    logger.error(f"Failed to add LAS file to database: {response.status_code}")
                                    
                            except Exception as e:
                                logger.error(f"Error adding LAS file to database: {e}")
                        
                    except Exception as e:
                        logger.error(f"Error saving attachment {filename}: {e}")
        
        return attachments

    def process_email(self, email_uid: str, email_message: email.message.Message) -> Dict[str, Any]:
        """Process and extract email data."""
        try:
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
            
            # Create email data
            email_data = {
                'uid': email_uid,
                'sender': sender,
                'subject': subject,
                'body': body,
                'hasAttachments': len(attachments) > 0,
                'attachments': attachments,
                'processed': False,
                'receivedAt': received_at.isoformat()
            }
            
            # Save email as JSON
            email_file = Path(f'data/emails/{email_uid}.json')
            with open(email_file, 'w', encoding='utf-8') as f:
                json.dump(email_data, f, indent=2, default=str)
            
            logger.info(f"Processed email: {subject} from {sender}")
            return email_data
            
        except Exception as e:
            logger.error(f"Error processing email {email_uid}: {e}")
            return None

    def send_to_api(self, email_data: Dict[str, Any]) -> bool:
        """Send email data to the backend API."""
        try:
            response = requests.post(
                f"{self.api_base_url}/api/emails",
                json=email_data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                logger.info(f"Sent email to API: {email_data['subject']}")
                return True
            else:
                logger.error(f"Failed to send email to API: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email to API: {e}")
            return False

    def check_new_emails(self):
        """Check for new emails using search."""
        try:
            # Search for unseen emails
            status, messages = self.mail.search(None, 'UNSEEN')
            
            if status == 'OK' and messages[0]:
                email_ids = messages[0].split()
                logger.info(f"Found {len(email_ids)} new emails")
                
                for email_id in email_ids:
                    try:
                        # Fetch email
                        status, msg_data = self.mail.fetch(email_id, '(RFC822)')
                        
                        if status == 'OK':
                            email_message = email.message_from_bytes(msg_data[0][1])
                            email_uid = email_id.decode()
                            
                            # Process email
                            email_data = self.process_email(email_uid, email_message)
                            
                            if email_data:
                                # Send to API
                                self.send_to_api(email_data)
                                
                    except Exception as e:
                        logger.error(f"Error processing email {email_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error checking new emails: {e}")

    def idle_monitor(self):
        """Monitor emails using IMAP IDLE for instant notifications."""
        logger.info("Starting IDLE monitoring...")
        
        while self.running:
            try:
                # Send IDLE command
                tag = self.mail._new_tag()
                self.mail.send(f'{tag} IDLE\r\n'.encode())
                
                # Wait for response or timeout
                start_time = time.time()
                while self.running and time.time() - start_time < self.idle_timeout:
                    try:
                        response = self.mail.readline()
                        if response:
                            response_str = response.decode('utf-8', errors='ignore')
                            
                            # Check if it's a new message notification
                            if 'EXISTS' in response_str or 'FETCH' in response_str:
                                logger.info("New email detected via IDLE")
                                break
                                
                    except Exception as e:
                        if self.running:
                            logger.error(f"Error in IDLE loop: {e}")
                        break
                
                # Send DONE to exit IDLE
                try:
                    self.mail.send(b'DONE\r\n')
                    self.mail.readline()  # Read completion response
                except:
                    pass
                
                # Check for new emails
                if self.running:
                    self.check_new_emails()
                    
            except Exception as e:
                if self.running:
                    logger.error(f"Error in IDLE monitoring: {e}")
                    time.sleep(10)  # Wait before retrying

    def polling_monitor(self):
        """Fallback polling method if IDLE is not supported."""
        logger.info("Starting polling monitoring...")
        
        while self.running:
            try:
                self.check_new_emails()
                time.sleep(30)  # Poll every 30 seconds
                
            except Exception as e:
                if self.running:
                    logger.error(f"Error in polling: {e}")
                    time.sleep(60)

    def start_monitoring(self):
        """Start the email monitoring process."""
        if not self.connect():
            return False
        
        self.running = True
        
        # Check for existing emails first
        self.check_new_emails()
        
        # Try IDLE monitoring first, fallback to polling
        try:
            # Test if IDLE is supported
            self.mail._simple_command('IDLE')
            self.mail.send(b'DONE\r\n')
            self.mail.readline()
            
            logger.info("IDLE supported, using IDLE monitoring")
            self.idle_monitor()
            
        except Exception as e:
            logger.warning(f"IDLE not supported, falling back to polling: {e}")
            self.polling_monitor()
        
        return True

    def stop_monitoring(self):
        """Stop the email monitoring process."""
        logger.info("Stopping email monitoring...")
        self.running = False
        self.disconnect()

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("Shutdown signal received")
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
        monitor = EmailMonitor()
        
        logger.info("Starting email monitoring service...")
        monitor.start_monitoring()
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        if 'monitor' in globals():
            monitor.stop_monitoring()

if __name__ == "__main__":
    main()