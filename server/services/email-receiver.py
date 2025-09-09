#!/usr/bin/env python3
"""
Direct Email Receiver - Simplified email fetching and processing
"""
import os
import sys
import json
import requests
import logging
from pathlib import Path
from datetime import datetime, timedelta
from imap_tools import MailBox, A

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailReceiver:
    def __init__(self):
        self.server = os.getenv('IMAP_SERVER', 'imap.gmail.com')
        self.username = os.getenv('EMAIL_USER') or os.getenv('SMTP_USER')
        self.password = os.getenv('EMAIL_PASS') or os.getenv('SMTP_PASSWORD')
        
        # Parse filter emails
        filter_emails_str = os.getenv('FILTER_EMAIL', '')
        self.filter_emails = []
        if filter_emails_str:
            clean_str = filter_emails_str.strip('[]')
            self.filter_emails = [email.strip().strip('\'"') for email in clean_str.split(',') if email.strip()]
        
        logger.info(f"Email Receiver initialized")
        logger.info(f"Server: {self.server}")
        logger.info(f"Username: {self.username}")
        logger.info(f"Filter emails: {self.filter_emails}")
    
    def store_email_in_database(self, message, las_files=[]):
        """Store email in database via API"""
        try:
            email_data = {
                "uid": str(message.uid),
                "sender": str(message.from_),
                "subject": message.subject or "",
                "content": message.text or message.html or "",
                "hasAttachments": len(message.attachments) > 0,
                "processed": False,
                "autoProcessed": False,
                "relatedLasFiles": las_files,
                "relatedOutputFiles": [],
                "replyEmailSent": False,
                "receivedAt": message.date.isoformat() if message.date else datetime.now().isoformat()
            }
            
            response = requests.post('http://localhost:5000/api/emails/store', 
                                   json=email_data, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Email stored in database: {email_data['uid']}")
                return response.json().get('email_id')
            else:
                logger.error(f"❌ Failed to store email: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error storing email: {e}")
            return None
    
    def check_and_receive_emails(self):
        """Check for new emails and process them"""
        if not self.username or not self.password:
            logger.error("Missing email credentials!")
            return False
        
        try:
            logger.info(f"🔗 Connecting to {self.server}...")
            
            with MailBox(self.server).login(self.username, self.password) as mailbox:
                logger.info(f"✅ Connected successfully!")
                
                # Get emails from last 7 days
                week_ago = datetime.now() - timedelta(days=7)
                logger.info(f"📅 Fetching emails from {week_ago.date()} onwards...")
                
                # Fetch recent emails
                try:
                    messages = list(mailbox.fetch(A(date_gte=week_ago.date())))
                    logger.info(f"📧 Found {len(messages)} total emails")
                except Exception as e:
                    logger.error(f"Error fetching messages: {e}")
                    return False
                
                processed_count = 0
                filtered_count = 0
                
                # Process each email
                for i, message in enumerate(messages):
                    try:
                        sender_email = str(message.from_).lower()
                        
                        # Check if sender matches filter
                        if self.filter_emails:
                            matches_filter = any(filter_email.lower() in sender_email 
                                               for filter_email in self.filter_emails)
                            if not matches_filter:
                                continue
                        
                        filtered_count += 1
                        logger.info(f"📧 Processing email {filtered_count}:")
                        logger.info(f"   UID: {message.uid}")
                        logger.info(f"   From: {message.from_}")
                        logger.info(f"   Subject: {message.subject}")
                        logger.info(f"   Date: {message.date}")
                        logger.info(f"   Attachments: {len(message.attachments)}")
                        
                        # Process LAS attachments if any
                        las_files = []
                        if message.attachments:
                            for att in message.attachments:
                                if att.filename and att.filename.lower().endswith('.las'):
                                    logger.info(f"   📎 LAS file found: {att.filename}")
                                    las_files.append(att.filename)
                        
                        # Store in database
                        email_id = self.store_email_in_database(message, las_files)
                        if email_id:
                            processed_count += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing message {i}: {e}")
                        continue
                
                logger.info(f"📊 Summary:")
                logger.info(f"   Total emails found: {len(messages)}")
                logger.info(f"   Filtered emails: {filtered_count}")
                logger.info(f"   Successfully processed: {processed_count}")
                
                return processed_count > 0
                
        except Exception as e:
            logger.error(f"❌ Email connection failed: {e}")
            return False

def main():
    """Main function for standalone execution"""
    logger.info("🚀 Starting Email Receiver...")
    
    receiver = EmailReceiver()
    success = receiver.check_and_receive_emails()
    
    if success:
        logger.info("✅ Email processing completed successfully")
    else:
        logger.error("❌ Email processing failed")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)