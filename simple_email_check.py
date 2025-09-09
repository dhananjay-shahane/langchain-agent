#!/usr/bin/env python3
import os
from imap_tools.mailbox import MailBox
from imap_tools.query import A
from datetime import datetime, timedelta

# Get credentials
username = os.getenv('SMTP_USER') or os.getenv('EMAIL_USER')
password = os.getenv('SMTP_PASSWORD') or os.getenv('EMAIL_PASS')
server = os.getenv('IMAP_SERVER', 'imap.gmail.com')

print(f"Checking emails for: {username}")

try:
    with MailBox(server).login(username, password) as mailbox:
        # Get emails from last 2 hours only
        recent_time = datetime.now() - timedelta(hours=2)
        messages = list(mailbox.fetch(A(date_gte=recent_time.date())))
        
        print(f"Found {len(messages)} emails in last 2 days")
        
        # Check specifically for emails from dhananjayshahane24@gmail.com
        target_sender = "dhananjayshahane24@gmail.com"
        
        for message in messages[-10:]:  # Last 10 emails
            sender = str(message.from_).lower()
            has_attachments = len(message.attachments) > 0
            has_las = any(att.filename and att.filename.lower().endswith('.las') for att in message.attachments)
            
            print(f"\n📧 Email:")
            print(f"   From: {message.from_}")
            print(f"   Subject: {message.subject}")
            print(f"   Date: {message.date}")
            print(f"   Attachments: {len(message.attachments)}")
            
            if has_attachments:
                for att in message.attachments:
                    print(f"     📎 {att.filename}")
            
            if target_sender in sender:
                print(f"   🎯 MATCH! This is from the target sender")
                if has_las:
                    print(f"   ✅ HAS LAS FILE!")
                    
except Exception as e:
    print(f"Error: {e}")