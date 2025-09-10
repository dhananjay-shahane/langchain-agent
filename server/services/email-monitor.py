#!/usr/bin/env python3
"""
Real-Time Email Monitor using IMAP IDLE for instant email notifications
Based on: https://community.latenode.com/t/setting-up-real-time-email-monitoring-with-python-imaplib-and-idle-command-for-gmail/30611
"""
import os
import logging
import threading
import time
import json
import uuid
import requests
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
WEBHOOK_URL = 'http://localhost:5000/api/emails/webhook'

# Directory to save email JSON files
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

class RealTimeEmailMonitor:
    def __init__(self):
        self.imap_server = IMAP_SERVER
        self.username = EMAIL_USER
        self.password = EMAIL_PASS
        self.server = None
        self.running = False
        
        if not self.username or not self.password:
            logger.warning("Email credentials not found in environment variables")
            logger.warning("Set EMAIL_USER and EMAIL_PASS to enable real-time email monitoring")
        
        if IMAPClient is None:
            logger.error("IMAPClient not available - cannot start real-time monitoring")
    
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
    
    def process_new_email(self, uid, email_message):
        """Process a newly received email and save to JSON file"""
        try:
            # Extract email details
            sender = self.decode_header_value(email_message.get('From', 'Unknown'))
            subject = self.decode_header_value(email_message.get('Subject', 'No Subject'))
            body = self.extract_email_body(email_message)
            attachments = self.get_attachments_info(email_message)
            date_header = email_message.get('Date', '')
            
            # Generate unique email ID
            email_id = str(uuid.uuid4())
            
            logger.info(f"📧 NEW REAL-TIME EMAIL:")
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
    
    def handle_new_message(self, uid):
        """Handle a new message notification from IDLE"""
        try:
            # Fetch the email message
            if self.server:
                response = self.server.fetch([uid], ['RFC822'])
            else:
                logger.error("Server connection not available")
                return
            if uid not in response:
                logger.warning(f"Could not fetch email with UID {uid}")
                return
            
            email_data = response[uid][b'RFC822']
            if isinstance(email_data, bytes):
                email_message = email.message_from_bytes(email_data)
            else:
                email_message = email.message_from_string(str(email_data))
            
            # Process the email
            self.process_new_email(uid, email_message)
            
        except Exception as e:
            logger.error(f"Error handling new message {uid}: {e}")
    
    def idle_loop(self):
        """Main IDLE loop for real-time email monitoring"""
        logger.info("🚀 Starting IMAP IDLE real-time email monitoring...")
        
        try:
            # Connect to IMAP server
            if IMAPClient is None:
                logger.error("IMAPClient not available")
                return
                
            self.server = IMAPClient(self.imap_server)
            self.server.login(self.username, self.password)
            self.server.select_folder('INBOX')
            
            logger.info(f"✅ Connected to {self.imap_server} as {self.username}")
            logger.info("🎯 Real-time email monitoring started!")
            logger.info("⏳ Entering IDLE mode - waiting for new emails...")
            
            while self.running:
                try:
                    # Start IDLE
                    self.server.idle()
                    
                    # Wait for responses (with timeout to handle Gmail's 29-minute limit)
                    responses = self.server.idle_check(timeout=1740)  # 29 minutes
                    
                    if responses:
                        for response in responses:
                            if response[1] == b'EXISTS':
                                # New message arrived
                                logger.info("🔔 New email detected via IDLE!")
                                
                                try:
                                    # Get the latest message UID
                                    messages = self.server.search('UNSEEN')
                                    logger.info(f"📬 Found {len(messages)} unseen messages after IDLE detection")
                                    
                                    if messages:
                                        latest_uid = max(messages)
                                        logger.info(f"🎯 Processing latest email UID: {latest_uid}")
                                        self.handle_new_message(latest_uid)
                                    else:
                                        logger.warning("⚠️ IDLE detected new email but no UNSEEN messages found")
                                        
                                        # Alternative: get the highest UID and process it regardless
                                        all_messages = self.server.search('ALL')
                                        if all_messages:
                                            latest_uid = max(all_messages)
                                            logger.info(f"🔄 Fallback: Processing latest message UID: {latest_uid}")
                                            self.handle_new_message(latest_uid)
                                            
                                except Exception as e:
                                    logger.error(f"❌ Error processing IDLE detection: {e}")
                                    import traceback
                                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    
                    # Stop IDLE to prevent timeout
                    self.server.idle_done()
                    
                    # Small delay before re-entering IDLE
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error in IDLE loop: {e}")
                    # Try to recover
                    try:
                        self.server.idle_done()
                    except:
                        pass
                    time.sleep(5)  # Wait before retrying
                    
        except Exception as e:
            logger.error(f"Failed to connect or maintain IDLE connection: {e}")
        finally:
            if self.server:
                try:
                    self.server.logout()
                except:
                    pass
            logger.info("🔌 IMAP connection closed")
    
    def start_monitoring(self):
        """Start the real-time email monitoring"""
        if not self.username or not self.password:
            logger.error("Cannot start monitoring: Email credentials not configured")
            return False
        
        if IMAPClient is None:
            logger.error("IMAPClient not available - cannot start monitoring")
            return False
        
        if self.running:
            logger.warning("Email monitoring is already running")
            return True
        
        self.running = True
        
        # Start IDLE monitoring in a separate thread
        monitor_thread = threading.Thread(target=self.idle_loop, daemon=True)
        monitor_thread.start()
        
        return True
    
    def stop_monitoring(self):
        """Stop the real-time email monitoring"""
        self.running = False
        logger.info("🛑 Stopping real-time email monitoring...")
    
    def fetch_unseen_emails_individually(self):
        """Fetch and process unseen emails one by one (only recent ones)"""
        if not self.username or not self.password:
            logger.error("Cannot fetch emails: Email credentials not configured")
            return
        
        if IMAPClient is None:
            logger.error("IMAPClient not available")
            return
            
        try:
            # Connect to IMAP server if not already connected
            if not self.server or not hasattr(self.server, 'folder'):
                self.server = IMAPClient(self.imap_server)
                self.server.login(self.username, self.password)
                self.server.select_folder('INBOX')
                logger.info(f"✅ Connected to {self.imap_server} as {self.username}")
            
            # Search for recent unseen emails (from last 7 days)
            from datetime import datetime, timedelta
            since_date = (datetime.now() - timedelta(days=7)).date()
            unseen_uids = self.server.search('UNSEEN')
            
            if not unseen_uids:
                logger.info("📭 No recent unseen emails found (last 7 days)")
                return
            
            logger.info(f"📬 Found {len(unseen_uids)} recent unseen emails. Processing one by one...")
            
            # Process each unseen email individually (limit to 50 for performance)
            for i, uid in enumerate(unseen_uids[:50], 1):
                logger.info(f"🔍 Processing unseen email {i}/{min(len(unseen_uids), 50)} (UID: {uid})")
                
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
                    self.process_new_email(uid, email_message)
                    
                    # Small delay between processing emails
                    time.sleep(0.1)  # Reduced delay for better performance
                    
                except Exception as e:
                    logger.error(f"Error processing email {uid}: {e}")
                    continue
            
            logger.info(f"✅ Finished processing {min(len(unseen_uids), 50)} recent unseen emails")
            
        except Exception as e:
            logger.error(f"Failed to fetch unseen emails: {e}")
        finally:
            # Keep connection open for IDLE monitoring
            pass

    def mark_old_emails_as_seen(self):
        """Mark all old emails (older than 7 days) as seen to prevent processing"""
        if not self.username or not self.password:
            logger.error("Cannot mark emails as seen: Email credentials not configured")
            return
        
        if IMAPClient is None:
            logger.error("IMAPClient not available")
            return
            
        try:
            # Connect to IMAP server if not already connected
            if not self.server or not hasattr(self.server, 'folder'):
                self.server = IMAPClient(self.imap_server)
                self.server.login(self.username, self.password)
                self.server.select_folder('INBOX')
                logger.info(f"✅ Connected to {self.imap_server} as {self.username}")
            
            # Search for old unseen emails (older than 7 days)
            from datetime import datetime, timedelta
            before_date = (datetime.now() - timedelta(days=7)).date()
            old_unseen_uids = self.server.search('UNSEEN')
            
            if not old_unseen_uids:
                logger.info("📭 No old unseen emails to mark as seen")
                return
            
            logger.info(f"🏷️ Marking {len(old_unseen_uids)} old emails as seen...")
            
            # Mark old emails as seen in batches
            batch_size = 1000
            for i in range(0, len(old_unseen_uids), batch_size):
                batch = old_unseen_uids[i:i + batch_size]
                self.server.add_flags(batch, ['\\Seen'])
                logger.info(f"🏷️ Marked batch {i//batch_size + 1} ({len(batch)} emails) as seen")
            
            logger.info(f"✅ Finished marking {len(old_unseen_uids)} old emails as seen")
            
        except Exception as e:
            logger.error(f"Failed to mark old emails as seen: {e}")

# Global monitor instance
email_monitor = RealTimeEmailMonitor()

def start_real_time_monitoring():
    """Start real-time email monitoring"""
    return email_monitor.start_monitoring()

def stop_real_time_monitoring():
    """Stop real-time email monitoring"""
    email_monitor.stop_monitoring()

def mark_old_emails_as_seen():
    """Mark old emails as seen to prevent processing"""
    return email_monitor.mark_old_emails_as_seen()

if __name__ == "__main__":
    import sys
    
    monitor = RealTimeEmailMonitor()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "fetch-unseen":
            # Just fetch unseen emails and exit
            logger.info("🔍 Fetching unseen emails...")
            monitor.fetch_unseen_emails_individually()
            logger.info("✅ Done fetching unseen emails")
            sys.exit(0)
        elif sys.argv[1] == "mark-old-seen":
            # Mark old emails as seen and exit
            logger.info("🏷️ Marking old emails as seen...")
            monitor.mark_old_emails_as_seen()
            logger.info("✅ Done marking old emails as seen")
            sys.exit(0)
    
    try:
        # First, fetch any existing unseen emails
        logger.info("🔍 Checking for existing unseen emails before starting real-time monitoring...")
        monitor.fetch_unseen_emails_individually()
        
        # Then start real-time monitoring
        monitor.start_monitoring()
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Stopping email monitor...")
        monitor.stop_monitoring()