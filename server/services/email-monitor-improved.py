#!/usr/bin/env python3
"""
Improved Real-Time Email Monitor - Detects ALL emails (not just unseen)
Tracks processed emails to avoid duplicates
"""
import os
import logging
import threading
import time
import json
import uuid
import requests
from datetime import datetime, timedelta
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
WEBHOOK_URL = 'http://localhost:5000/api/emails/webhook'

# Directory to save email JSON files and tracking
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# File to track processed emails
PROCESSED_EMAILS_FILE = os.path.join(DATA_DIR, 'processed_emails.json')

class ImprovedEmailMonitor:
    def __init__(self):
        self.imap_server = IMAP_SERVER
        self.username = EMAIL_USER
        self.password = EMAIL_PASS
        self.server = None
        self.running = False
        self.processed_uids = set()
        self.last_check_time = datetime.now() - timedelta(hours=1)  # Check last hour initially
        
        # Load previously processed emails
        self.load_processed_emails()
        
        if not self.username or not self.password:
            logger.warning("Email credentials not found in environment variables")
            logger.warning("Set EMAIL_USER and EMAIL_PASS to enable email monitoring")
        
        if IMAPClient is None:
            logger.error("IMAPClient not available - cannot start monitoring")
    
    def load_processed_emails(self):
        """Load previously processed email UIDs"""
        try:
            if os.path.exists(PROCESSED_EMAILS_FILE):
                with open(PROCESSED_EMAILS_FILE, 'r') as f:
                    data = json.load(f)
                    self.processed_uids = set(data.get('processed_uids', []))
                    last_check_str = data.get('last_check_time')
                    if last_check_str:
                        self.last_check_time = datetime.fromisoformat(last_check_str)
                logger.info(f"📂 Loaded {len(self.processed_uids)} processed email UIDs")
        except Exception as e:
            logger.warning(f"Could not load processed emails: {e}")
            self.processed_uids = set()
    
    def save_processed_emails(self):
        """Save processed email UIDs to file"""
        try:
            data = {
                'processed_uids': list(self.processed_uids),
                'last_check_time': self.last_check_time.isoformat(),
                'last_updated': datetime.now().isoformat()
            }
            with open(PROCESSED_EMAILS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save processed emails: {e}")
    
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
    
    def get_attachments_info(self, email_message):
        """Get information about email attachments"""
        attachments = []
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_disposition() == 'attachment':
                        filename = part.get_filename()
                        if filename:
                            attachments.append({
                                'filename': filename,
                                'size': len(part.get_payload(decode=True)) if part.get_payload(decode=True) else 0
                            })
        except Exception as e:
            logger.warning(f"Error getting attachment info: {e}")
        
        return attachments
    
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
            attachments = self.get_attachments_info(email_message)
            date_header = email_message.get('Date', '')
            
            # Generate unique email ID
            email_id = str(uuid.uuid4())
            
            logger.info(f"📧 NEW EMAIL DETECTED:")
            logger.info(f"   Email ID: {email_id}")
            logger.info(f"   UID: {uid}")
            logger.info(f"   From: {sender}")
            logger.info(f"   Subject: {subject}")
            logger.info(f"   Body preview: {body[:100]}..." if body else "   No body")
            logger.info(f"   Attachments: {len(attachments)}")
            
            # Create email data structure
            email_data = {
                'email_id': email_id,
                'uid': str(uid),
                'sender': sender,
                'subject': subject,
                'body_content': body,
                'content': body,  # For webhook compatibility
                'hasAttachments': len(attachments) > 0,
                'attachments': attachments,
                'date_received': date_header,
                'timestamp': datetime.now().isoformat(),
                'processed_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'realTime': True
            }
            
            # Save to JSON file
            json_path = self.save_email_to_json(email_data)
            logger.info(f"💾 Email data saved to JSON: {email_id}")
            
            # Send to webhook for processing
            self.send_to_webhook(email_data)
            
            # Mark as processed
            self.processed_uids.add(uid)
            self.save_processed_emails()
            
        except Exception as e:
            logger.error(f"Error processing email {uid}: {e}")
    
    def send_to_webhook(self, email_data):
        """Send email data to webhook endpoint"""
        try:
            response = requests.post(
                WEBHOOK_URL, 
                json=email_data, 
                timeout=5,
                headers={'Content-Type': 'application/json'}
            )
            if response.status_code == 200:
                logger.info(f"🔔 Real-time email notification sent: {email_data['sender']} - {email_data['subject']}")
                logger.info(f"✅ Email data sent to webhook successfully")
            else:
                logger.warning(f"⚠️ Webhook responded with status {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ Could not reach webhook endpoint: {e}")
        except Exception as e:
            logger.error(f"❌ Error sending to webhook: {e}")
    
    def check_for_new_emails(self):
        """Check for new emails (both seen and unseen)"""
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
            
            # Search for recent emails (last 24 hours)
            since_date = (datetime.now() - timedelta(hours=24)).date()
            recent_emails = self.server.search(['SINCE', since_date])
            
            if not recent_emails:
                logger.info("📭 No recent emails found (last 24 hours)")
                return
            
            # Check for emails we haven't processed yet
            new_emails = [uid for uid in recent_emails if uid not in self.processed_uids]
            
            if new_emails:
                logger.info(f"📬 Found {len(new_emails)} NEW emails to process (out of {len(recent_emails)} recent)")
                
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
                        
                        time.sleep(0.5)  # Small delay between processing
                        
                    except Exception as e:
                        logger.error(f"Error processing email {uid}: {e}")
                        continue
            else:
                logger.info(f"📭 No new emails found ({len(recent_emails)} recent emails already processed)")
                
            self.last_check_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Error checking for emails: {e}")
            # Reset connection on error
            self.server = None
    
    def start_monitoring(self):
        """Start monitoring emails every 10 seconds"""
        if not self.username or not self.password:
            logger.error("Cannot start monitoring: Email credentials not configured")
            return False
        
        if IMAPClient is None:
            logger.error("IMAPClient not available - cannot start monitoring")
            return False
        
        logger.info("🚀 Starting improved email monitoring (checking every 10 seconds for ALL recent emails)...")
        self.running = True
        
        # Initial check
        self.check_for_new_emails()
        
        while self.running:
            try:
                self.check_for_new_emails()
                
                # Wait 10 seconds before next check
                for i in range(10):
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
email_monitor = ImprovedEmailMonitor()

if __name__ == "__main__":
    import sys
    
    try:
        # Start monitoring
        email_monitor.start_monitoring()
    except KeyboardInterrupt:
        logger.info("🛑 Stopping email monitor...")
        email_monitor.stop_monitoring()