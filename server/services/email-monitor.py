#!/usr/bin/env python3
"""
Simple Email Monitor - Checks emails every 20 seconds and creates JSON files
"""
import os
import logging
import time
import json
import uuid
from datetime import datetime
try:
    from imapclient import IMAPClient
except ImportError:
    print("imapclient library not found. Install with: pip install imapclient")
    IMAPClient = None
import email
from email.header import decode_header

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Email configuration
IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.gmail.com')
EMAIL_USER = os.getenv('EMAIL_USER', '')
EMAIL_PASS = os.getenv('EMAIL_PASS', '')

# Directory to save email JSON files
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

class SimpleEmailMonitor:
    def __init__(self):
        self.imap_server = IMAP_SERVER
        self.username = EMAIL_USER
        self.password = EMAIL_PASS
        self.server = None
        self.running = False
        self.processed_uids = set()
        
        if not self.username or not self.password:
            logger.warning("Email credentials not found in environment variables")
            logger.warning("Set EMAIL_USER and EMAIL_PASS to enable email monitoring")
        
        if IMAPClient is None:
            logger.error("IMAPClient not available - cannot start monitoring")
    
    def decode_header_value(self, value):
        """Decode email header values that might be encoded"""
        if not value:
            return ""
        
        try:
            decoded_parts = decode_header(value)
            decoded_value = ""
            for part, charset in decoded_parts:
                if isinstance(part, bytes):
                    if charset:
                        decoded_value += part.decode(charset, errors='ignore')
                    else:
                        decoded_value += part.decode('utf-8', errors='ignore')
                else:
                    decoded_value += str(part)
            return decoded_value
        except Exception as e:
            logger.warning(f"Error decoding header: {e}")
            return str(value)
    
    def extract_email_body(self, email_message):
        """Extract plain text body from email message"""
        body = ""
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if isinstance(payload, bytes):
                            body = payload.decode('utf-8', errors='ignore')
                        else:
                            body = str(payload)
                        break
            else:
                payload = email_message.get_payload(decode=True)
                if isinstance(payload, bytes):
                    body = payload.decode('utf-8', errors='ignore')
                else:
                    body = str(payload)
        except Exception as e:
            logger.warning(f"Error extracting email body: {e}")
        
        return body.strip()
    
    def save_email_to_json(self, email_data):
        """Save email data to JSON file"""
        try:
            # Create filename with timestamp and email ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"email_{timestamp}_{email_data['email_id'][:8]}.json"
            filepath = os.path.join(DATA_DIR, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(email_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"📄 Email saved to JSON: {filename}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving email to JSON: {e}")
            return None
    
    def process_email(self, uid, email_message):
        """Process an email and save to JSON file"""
        try:
            # Extract email details
            sender = self.decode_header_value(email_message.get('From', 'Unknown'))
            subject = self.decode_header_value(email_message.get('Subject', 'No Subject'))
            body = self.extract_email_body(email_message)
            date_header = email_message.get('Date', '')
            
            # Generate unique email ID
            email_id = str(uuid.uuid4())
            
            # Create email data structure
            email_data = {
                'email_id': email_id,
                'uid': str(uid),
                'sender': sender,
                'subject': subject,
                'body_content': body,
                'date_received': date_header,
                'timestamp': datetime.now().isoformat(),
                'processed_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            logger.info(f"📧 NEW EMAIL RECEIVED:")
            logger.info(f"   Email ID: {email_id}")
            logger.info(f"   From: {sender}")
            logger.info(f"   Subject: {subject}")
            logger.info(f"   Body Length: {len(body)} characters")
            
            # Save to JSON file
            self.save_email_to_json(email_data)
            
            # Mark as processed
            self.processed_uids.add(uid)
            
        except Exception as e:
            logger.error(f"Error processing email {uid}: {e}")
    
    def check_for_new_emails(self):
        """Check for new emails and process them"""
        try:
            if not self.server:
                # Connect to IMAP server
                if IMAPClient is None:
                    logger.error("IMAPClient not available")
                    return
                    
                self.server = IMAPClient(self.imap_server)
                self.server.login(self.username, self.password)
                self.server.select_folder('INBOX')
                logger.info(f"✅ Connected to {self.imap_server} as {self.username}")
            
            # Search for unseen emails
            unseen_uids = self.server.search('UNSEEN')
            new_emails = [uid for uid in unseen_uids if uid not in self.processed_uids]
            
            if new_emails:
                logger.info(f"📬 Found {len(new_emails)} new emails to process")
                
                for uid in new_emails:
                    try:
                        # Fetch the email message
                        response = self.server.fetch([uid], ['RFC822'])
                        if uid not in response:
                            logger.warning(f"Could not fetch email with UID {uid}")
                            continue
                        
                        email_data = response[uid][b'RFC822']
                        if isinstance(email_data, bytes):
                            email_message = email.message_from_bytes(email_data)
                        else:
                            email_message = email.message_from_string(str(email_data))
                        
                        # Process the email
                        self.process_email(uid, email_message)
                        
                    except Exception as e:
                        logger.error(f"Error processing email {uid}: {e}")
                        continue
            else:
                logger.info("📭 No new emails found")
                
        except Exception as e:
            logger.error(f"Error checking for emails: {e}")
            # Reset connection on error
            self.server = None
    
    def start_monitoring(self):
        """Start monitoring emails every 20 seconds"""
        if not self.username or not self.password:
            logger.error("Cannot start monitoring: Email credentials not configured")
            return False
        
        if IMAPClient is None:
            logger.error("IMAPClient not available - cannot start monitoring")
            return False
        
        logger.info("🚀 Starting email monitoring (checking every 20 seconds)...")
        self.running = True
        
        while self.running:
            try:
                self.check_for_new_emails()
                
                # Wait 20 seconds before next check
                for i in range(20):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                logger.info("🛑 Stopping email monitor...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Wait before retrying
        
        # Cleanup
        if self.server:
            try:
                self.server.logout()
            except:
                pass
        
        logger.info("🔌 Email monitoring stopped")
    
    def stop_monitoring(self):
        """Stop the email monitoring"""
        self.running = False

# Global monitor instance
email_monitor = SimpleEmailMonitor()

if __name__ == "__main__":
    import sys
    
    try:
        # Start monitoring
        email_monitor.start_monitoring()
    except KeyboardInterrupt:
        logger.info("🛑 Stopping email monitor...")
        email_monitor.stop_monitoring()