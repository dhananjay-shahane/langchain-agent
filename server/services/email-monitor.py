#!/usr/bin/env python3
"""
Real-Time Email Monitor using IMAP IDLE for instant email notifications
Based on: https://community.latenode.com/t/setting-up-real-time-email-monitoring-with-python-imaplib-and-idle-command-for-gmail/30611
"""
import os
import logging
import threading
import time
import requests
try:
    from imapclient import IMAPClient
except ImportError:
    logger.error("imapclient library not found. Install with: pip install imapclient")
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
        
        return body
    
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
    
    def process_new_email(self, uid, email_message):
        """Process a newly received email and send to webhook"""
        try:
            # Extract email details
            sender = self.decode_header_value(email_message.get('From', 'Unknown'))
            subject = self.decode_header_value(email_message.get('Subject', 'No Subject'))
            body = self.extract_email_body(email_message)
            attachments = self.get_attachments_info(email_message)
            
            logger.info(f"📧 NEW REAL-TIME EMAIL:")
            logger.info(f"   UID: {uid}")
            logger.info(f"   From: {sender}")
            logger.info(f"   Subject: {subject}")
            logger.info(f"   Body preview: {body[:100]}..." if body else "   No body")
            logger.info(f"   Attachments: {len(attachments)}")
            
            # Prepare email data for webhook
            email_data = {
                'uid': str(uid),
                'sender': sender,
                'subject': subject,
                'content': body,
                'hasAttachments': len(attachments) > 0,
                'attachments': attachments,
                'realTime': True,
                'timestamp': time.time()
            }
            
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
            response = self.server.fetch([uid], ['RFC822'])
            if uid not in response:
                logger.warning(f"Could not fetch email with UID {uid}")
                return
            
            email_data = response[uid][b'RFC822']
            email_message = email.message_from_bytes(email_data)
            
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
            logger.info("⏳ Entering IDLE mode - waiting for new emails...")
            
            while self.running:
                try:
                    # Start IDLE
                    self.server.idle()
                    
                    # Wait for responses (with timeout)
                    responses = self.server.idle_check(timeout=300)  # 5 minutes timeout
                    
                    if responses:
                        for response in responses:
                            if response[1] == b'EXISTS':
                                # New message arrived
                                logger.info("🔔 New email detected via IDLE!")
                                
                                # Get the latest message UID
                                messages = self.server.search(['UNSEEN'])
                                if messages:
                                    latest_uid = max(messages)
                                    self.handle_new_message(latest_uid)
                    
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
        
        logger.info("🎯 Real-time email monitoring started!")
        return True
    
    def stop_monitoring(self):
        """Stop the real-time email monitoring"""
        self.running = False
        logger.info("🛑 Stopping real-time email monitoring...")

# Global monitor instance
email_monitor = RealTimeEmailMonitor()

def start_real_time_monitoring():
    """Start real-time email monitoring"""
    return email_monitor.start_monitoring()

def stop_real_time_monitoring():
    """Stop real-time email monitoring"""
    email_monitor.stop_monitoring()

if __name__ == "__main__":
    monitor = RealTimeEmailMonitor()
    
    try:
        monitor.start_monitoring()
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Stopping email monitor...")
        monitor.stop_monitoring()