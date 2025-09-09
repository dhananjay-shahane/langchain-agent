#!/usr/bin/env python3
"""
Email Debug Script - Test email connection and check for incoming emails
"""
import os
import logging
from imap_tools.mailbox import MailBox
from imap_tools.query import A
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_email_connection():
    """Test email connection and debug issues"""
    
    # Get credentials
    server = os.getenv('IMAP_SERVER', 'imap.gmail.com')
    username = os.getenv('EMAIL_USER')
    password = os.getenv('EMAIL_PASS')
    filter_emails_str = os.getenv('FILTER_EMAIL', '')
    
    logger.info(f"🔧 Email Debug Test")
    logger.info(f"Server: {server}")
    logger.info(f"Username: {username}")
    logger.info(f"Password: {'*' * len(password) if password else 'NOT SET'}")
    logger.info(f"Filter emails: {filter_emails_str}")
    
    # Parse filter emails
    filter_emails = []
    if filter_emails_str:
        clean_str = filter_emails_str.strip('[]')
        filter_emails = [email.strip().strip('\'"') for email in clean_str.split(',') if email.strip()]
        logger.info(f"Parsed filter emails: {filter_emails}")
    
    if not username or not password:
        logger.error("❌ Missing email credentials!")
        return False
    
    try:
        logger.info("🔗 Attempting to connect to email server...")
        with MailBox(server).login(username, password) as mailbox:
            logger.info("✅ Successfully connected to email server!")
            
            # Check all folders
            logger.info("📁 Available folders:")
            for folder in mailbox.folder.list():
                logger.info(f"  - {folder}")
            
            # Check inbox
            mailbox.folder.set('INBOX')
            logger.info("📧 Checking INBOX...")
            
            # Get recent emails (last 24 hours)
            yesterday = datetime.now() - timedelta(days=1)
            
            # Check unread emails first
            unread_messages = list(mailbox.fetch(A(seen=False)))
            logger.info(f"Found {len(unread_messages)} unread emails")
            
            # Check recent emails
            recent_messages = list(mailbox.fetch(A(date_gte=yesterday.date())))
            logger.info(f"Found {len(recent_messages)} emails in last 24 hours")
            
            # Check emails from filtered senders
            if filter_emails:
                for filter_email in filter_emails:
                    logger.info(f"🔍 Checking emails from {filter_email}...")
                    sender_messages = list(mailbox.fetch(A(from_=filter_email)))
                    logger.info(f"Found {len(sender_messages)} emails from {filter_email}")
                    
                    # Show recent emails from this sender
                    for msg in sender_messages[-5:]:  # Last 5 emails
                        logger.info(f"  📧 UID: {msg.uid}, Subject: {msg.subject}, Date: {msg.date}")
                        logger.info(f"     From: {msg.from_}, Attachments: {len(msg.attachments)}")
                        if msg.attachments:
                            for att in msg.attachments:
                                logger.info(f"       🔗 {att.filename} ({len(att.payload)} bytes)")
            
            # Check all recent emails with attachments
            logger.info("🔍 Checking recent emails with attachments...")
            attachment_count = 0
            las_count = 0
            
            for message in recent_messages:
                if message.attachments:
                    attachment_count += 1
                    sender_email = str(message.from_).lower()
                    
                    # Check if sender matches filter
                    matches_filter = False
                    if filter_emails:
                        matches_filter = any(filter_email.lower() in sender_email for filter_email in filter_emails)
                    else:
                        matches_filter = True  # No filter, accept all
                    
                    logger.info(f"📧 Email with attachments:")
                    logger.info(f"   UID: {message.uid}")
                    logger.info(f"   From: {message.from_}")
                    logger.info(f"   Subject: {message.subject}")
                    logger.info(f"   Date: {message.date}")
                    logger.info(f"   Matches filter: {matches_filter}")
                    
                    for attachment in message.attachments:
                        is_las = attachment.filename and attachment.filename.lower().endswith('.las')
                        if is_las:
                            las_count += 1
                        logger.info(f"     📎 {attachment.filename} ({len(attachment.payload)} bytes) [LAS: {is_las}]")
            
            logger.info(f"📊 Summary:")
            logger.info(f"   Total recent emails: {len(recent_messages)}")
            logger.info(f"   Emails with attachments: {attachment_count}")
            logger.info(f"   LAS files found: {las_count}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_email_connection()