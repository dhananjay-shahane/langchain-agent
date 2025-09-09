#!/usr/bin/env python3
"""
Simple Email Check - Minimal email fetching for debugging
"""
import os
import sys
import requests
from imap_tools import MailBox, A
from datetime import datetime, timedelta

def simple_email_check():
    """Simple email check with minimal operations"""
    server = os.getenv('IMAP_SERVER', 'imap.gmail.com')
    username = os.getenv('EMAIL_USER') or os.getenv('SMTP_USER')
    password = os.getenv('EMAIL_PASS') or os.getenv('SMTP_PASSWORD')
    
    print(f"Testing: {username} -> {server}")
    
    try:
        with MailBox(server).login(username, password) as mailbox:
            print("✅ Connected!")
            
            # Just get the first 5 emails
            print("Fetching first 5 emails...")
            messages = list(mailbox.fetch(limit=5))
            print(f"Found {len(messages)} emails")
            
            for i, msg in enumerate(messages):
                print(f"{i+1}. {msg.from_} | {msg.subject}")
                
                # Store this email in database
                email_data = {
                    "uid": str(msg.uid),
                    "sender": str(msg.from_),
                    "subject": msg.subject or "",
                    "content": msg.text or msg.html or "",
                    "hasAttachments": len(msg.attachments) > 0,
                    "processed": False,
                    "autoProcessed": False,
                    "relatedLasFiles": [],
                    "relatedOutputFiles": [],
                    "replyEmailSent": False,
                    "receivedAt": msg.date.isoformat() if msg.date else datetime.now().isoformat()
                }
                
                try:
                    response = requests.post('http://localhost:5000/api/emails/store', 
                                           json=email_data, timeout=5)
                    if response.status_code == 200:
                        print(f"   ✅ Stored in database")
                    else:
                        print(f"   ❌ Failed to store: {response.status_code}")
                except Exception as e:
                    print(f"   ❌ Storage error: {e}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    simple_email_check()