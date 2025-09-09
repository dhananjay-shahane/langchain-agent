#!/usr/bin/env python3
"""
Quick test to debug email processing
"""
import os
import sys
from pathlib import Path
from imap_tools import MailBox, A
from datetime import datetime, timedelta

def test_email_connection():
    username = os.getenv('EMAIL_USER')
    password = os.getenv('EMAIL_PASS')
    server = os.getenv('IMAP_SERVER', 'imap.gmail.com')
    
    print(f"Testing connection to {server} with user: {username}")
    
    if not username or not password:
        print("ERROR: Email credentials not found!")
        return
    
    try:
        with MailBox(server).login(username, password) as mailbox:
            print("✅ Successfully connected to email server")
            
            # Check unread emails
            unread_messages = list(mailbox.fetch(A(seen=False)))
            print(f"📧 Found {len(unread_messages)} unread emails")
            
            # Check recent emails (last 24 hours)
            yesterday = datetime.now() - timedelta(days=1)
            recent_messages = list(mailbox.fetch(A(date_gte=yesterday.date())))
            print(f"📅 Found {len(recent_messages)} emails from last 24 hours")
            
            # Process recent emails with attachments
            processed_count = 0
            las_found_count = 0
            
            for message in recent_messages:
                if not message.attachments:
                    continue
                    
                processed_count += 1
                print(f"\n📎 Email: '{message.subject[:50]}...' from {message.from_}")
                print(f"   Date: {message.date}")
                print(f"   Attachments: {len(message.attachments)}")
                
                for i, attachment in enumerate(message.attachments):
                    filename = attachment.filename or f"attachment_{i}"
                    size_kb = len(attachment.payload) / 1024
                    print(f"     - {filename} ({size_kb:.1f}KB)")
                    
                    if filename.lower().endswith('.las'):
                        print(f"       🎯 LAS FILE FOUND: {filename}")
                        las_found_count += 1
                    else:
                        print(f"       ❌ Not LAS file: {filename}")
            
            print(f"\n📊 Summary:")
            print(f"   - {processed_count} emails with attachments")
            print(f"   - {las_found_count} LAS files found")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_email_connection()