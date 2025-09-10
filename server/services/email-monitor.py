#!/usr/bin/env python3
"""
Simple Email Monitor for checking new emails
"""
import imaplib
import email
import time
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set up credentials and server
IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.gmail.com')
EMAIL_USER = os.getenv('EMAIL_USER', '')
EMAIL_PASS = os.getenv('EMAIL_PASS', '')

def check_new_emails():
    """Check for new unseen emails and print their content"""
    if not EMAIL_USER or not EMAIL_PASS:
        logger.warning("Email credentials not found in environment variables")
        return
    
    try:
        # Connect and login to IMAP server
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        # Search for all unseen messages
        status, messages = mail.search(None, '(UNSEEN)')
        
        if not messages[0]:
            logger.info("No new emails found")
            mail.logout()
            return
        
        message_ids = messages[0].split()
        logger.info(f"Found {len(message_ids)} new emails")
        
        for num in message_ids:
            status, data = mail.fetch(num, '(RFC822)')
            
            if status != 'OK' or not data or not data[0]:
                continue
                
            bytes_data = data[0][1]
            email_message = email.message_from_bytes(bytes_data)
            
            # Get email details
            sender = email_message.get('From', 'Unknown')
            subject = email_message.get('Subject', 'No Subject')
            
            logger.info(f"📧 New Email Received:")
            logger.info(f"   From: {sender}")
            logger.info(f"   Subject: {subject}")
            
            # Process email body
            body = ""
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            payload = part.get_payload(decode=True)
                            if isinstance(payload, bytes):
                                body = payload.decode('utf-8', errors='ignore')
                            else:
                                body = str(payload)
                            break
                        except Exception as e:
                            logger.warning(f"Error decoding email body: {e}")
            else:
                try:
                    payload = email_message.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        body = payload.decode('utf-8', errors='ignore')
                    else:
                        body = str(payload)
                except Exception as e:
                    logger.warning(f"Error decoding email body: {e}")
            
            if body:
                logger.info(f"   Body: {body[:200]}...")  # Show first 200 chars
            
            # Check for attachments
            attachments = []
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_disposition() == 'attachment':
                        filename = part.get_filename()
                        if filename:
                            attachments.append(filename)
                            logger.info(f"   Attachment: {filename}")
            
            if attachments:
                logger.info(f"   Total attachments: {len(attachments)}")
            else:
                logger.info("   No attachments")
        
        mail.logout()
        
    except Exception as e:
        logger.error(f"Error checking emails: {e}")

def run_monitor():
    """Run the email monitor continuously"""
    logger.info("Starting email monitor (checking every 60 seconds)")
    
    if not EMAIL_USER or not EMAIL_PASS:
        logger.error("Email credentials not configured. Set EMAIL_USER and EMAIL_PASS environment variables.")
        return
    
    while True:
        try:
            check_new_emails()
            time.sleep(60)  # Wait for 60 seconds, then check again
        except KeyboardInterrupt:
            logger.info("Email monitor stopped by user")
            break
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_monitor()