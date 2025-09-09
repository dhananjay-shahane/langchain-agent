#!/usr/bin/env python3
"""
Direct Email Fetch - Fast and reliable email processing
"""
import os
import sys
import requests
import json
from imap_tools import MailBox, A
from datetime import datetime, timedelta

def fetch_and_store_emails():
    """Fetch emails and store them directly"""
    server = os.getenv('IMAP_SERVER', 'imap.gmail.com')
    username = os.getenv('EMAIL_USER') or os.getenv('SMTP_USER')
    password = os.getenv('EMAIL_PASS') or os.getenv('SMTP_PASSWORD')
    filter_emails_str = os.getenv('FILTER_EMAIL', '')
    
    print(f"[EMAIL] Starting fetch for {username}")
    
    # Parse filter emails
    filter_emails = []
    if filter_emails_str:
        clean_str = filter_emails_str.strip('[]')
        filter_emails = [email.strip().strip('\'"') for email in clean_str.split(',') if email.strip()]
    
    print(f"[EMAIL] Filter: {filter_emails}")
    
    if not username or not password:
        print("[EMAIL] ERROR: Missing credentials")
        return False
    
    try:
        print(f"[EMAIL] Connecting to {server}...")
        with MailBox(server).login(username, password) as mailbox:
            print("[EMAIL] Connected! Fetching emails...")
            
            # Get last 10 emails only for speed
            messages = list(mailbox.fetch(limit=10, reverse=True))
            print(f"[EMAIL] Found {len(messages)} recent emails")
            
            stored_count = 0
            for message in messages:
                sender_email = str(message.from_).lower()
                
                # Check filter
                if filter_emails:
                    matches = any(filter_email.lower() in sender_email for filter_email in filter_emails)
                    if not matches:
                        continue
                
                print(f"[EMAIL] Processing: {message.from_} | {message.subject}")
                
                # Store email
                email_data = {
                    "uid": str(message.uid),
                    "sender": str(message.from_),
                    "subject": message.subject or "",
                    "content": message.text or message.html or "",
                    "hasAttachments": len(message.attachments) > 0,
                    "processed": False,
                    "autoProcessed": False,
                    "relatedLasFiles": [],
                    "relatedOutputFiles": [],
                    "replyEmailSent": False
                }
                
                try:
                    response = requests.post('http://localhost:5000/api/emails/store', 
                                           json=email_data, timeout=5)
                    if response.status_code == 200:
                        stored_count += 1
                        print(f"[EMAIL] ✅ Stored email from {message.from_}")
                    else:
                        print(f"[EMAIL] ❌ Storage failed: {response.status_code}")
                except Exception as e:
                    print(f"[EMAIL] ❌ Storage error: {e}")
            
            print(f"[EMAIL] Complete! Stored {stored_count} emails")
            return stored_count > 0
            
    except Exception as e:
        print(f"[EMAIL] ERROR: {e}")
        return False

if __name__ == "__main__":
    success = fetch_and_store_emails()
    sys.exit(0 if success else 1)