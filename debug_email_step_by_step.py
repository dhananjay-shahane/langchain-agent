#!/usr/bin/env python3
"""
Step-by-step email debugging
"""
import os
import requests
import json
from imap_tools.mailbox import MailBox
from imap_tools.query import A
from datetime import datetime, timedelta

def step1_check_credentials():
    print("=== STEP 1: Check Credentials ===")
    username = os.getenv('SMTP_USER') or os.getenv('EMAIL_USER')
    password = os.getenv('SMTP_PASSWORD') or os.getenv('EMAIL_PASS')
    server = os.getenv('IMAP_SERVER', 'imap.gmail.com')
    filter_email = os.getenv('FILTER_EMAIL', '')
    
    print(f"Server: {server}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password) if password else 'NOT SET'}")
    print(f"Filter: {filter_email}")
    return username, password, server, filter_email

def step2_test_connection(username, password, server):
    print("\n=== STEP 2: Test Email Connection ===")
    try:
        with MailBox(server).login(username, password) as mailbox:
            print("✅ Successfully connected to email server")
            return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def step3_fetch_emails(username, password, server, filter_email):
    print("\n=== STEP 3: Fetch Recent Emails ===")
    try:
        with MailBox(server).login(username, password) as mailbox:
            # Get emails from last 2 hours
            recent_time = datetime.now() - timedelta(hours=2)
            
            # Check unread emails first
            unread_messages = list(mailbox.fetch(A(seen=False)))
            print(f"Unread emails: {len(unread_messages)}")
            
            # Check recent emails
            recent_messages = list(mailbox.fetch(A(date_gte=recent_time.date())))
            print(f"Recent emails (last 2 days): {len(recent_messages)}")
            
            # Filter by sender
            filter_emails = [email.strip().strip('\'"') for email in filter_email.strip('[]').split(',') if email.strip()]
            
            print(f"Looking for emails from: {filter_emails}")
            
            found_emails = []
            for message in recent_messages:
                sender_email = str(message.from_).lower()
                matches_filter = any(filter_email.lower() in sender_email for filter_email in filter_emails)
                
                if matches_filter:
                    found_emails.append({
                        'uid': message.uid,
                        'from': str(message.from_),
                        'subject': message.subject,
                        'date': str(message.date),
                        'attachments': len(message.attachments)
                    })
                    print(f"📧 FOUND: UID={message.uid}, From={message.from_}, Subject={message.subject}")
            
            print(f"Total matching emails found: {len(found_emails)}")
            return found_emails
            
    except Exception as e:
        print(f"❌ Error fetching emails: {e}")
        return []

def step4_test_api():
    print("\n=== STEP 4: Test API Endpoints ===")
    try:
        # Test the API endpoint
        response = requests.get('http://localhost:5000/api/emails/received', timeout=5)
        print(f"API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"API Response: {json.dumps(data, indent=2)}")
            return data
        else:
            print(f"API Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ API Test failed: {e}")
        return None

def step5_check_database():
    print("\n=== STEP 5: Test Database Storage ===")
    try:
        # Try to store a test email
        test_email = {
            "uid": "TEST_123",
            "sender": "test@example.com",
            "subject": "Test Email",
            "content": "This is a test",
            "hasAttachments": False,
            "processed": False,
            "autoProcessed": False,
            "relatedLasFiles": [],
            "relatedOutputFiles": [],
            "replyEmailSent": False,
            "receivedAt": datetime.now().isoformat()
        }
        
        response = requests.post('http://localhost:5000/api/emails/store', json=test_email, timeout=5)
        print(f"Store Test Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Database storage working")
            # Now check if we can retrieve it
            response = requests.get('http://localhost:5000/api/emails/received', timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"Retrieved emails: {data.get('totalEmails', 0)}")
                return True
        else:
            print(f"❌ Database storage failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def main():
    print("🔍 EMAIL DEBUGGING - STEP BY STEP")
    print("=" * 50)
    
    # Step 1: Check credentials
    username, password, server, filter_email = step1_check_credentials()
    
    if not username or not password:
        print("❌ CRITICAL: Missing email credentials!")
        return
    
    # Step 2: Test connection
    if not step2_test_connection(username, password, server):
        return
    
    # Step 3: Fetch emails
    found_emails = step3_fetch_emails(username, password, server, filter_email)
    
    # Step 4: Test API
    api_data = step4_test_api()
    
    # Step 5: Test database
    db_working = step5_check_database()
    
    print("\n" + "=" * 50)
    print("🔍 DEBUGGING SUMMARY:")
    print(f"✅ Email connection: Working")
    print(f"📧 Found matching emails: {len(found_emails)}")
    print(f"🔗 API working: {'Yes' if api_data is not None else 'No'}")
    print(f"💾 Database working: {'Yes' if db_working else 'No'}")
    
    if len(found_emails) > 0 and (api_data is None or api_data.get('totalEmails', 0) == 0):
        print("\n❌ PROBLEM IDENTIFIED:")
        print("   Emails exist in Gmail but not in database!")
        print("   The email monitor is not processing them correctly.")
    
    if len(found_emails) == 0:
        print("\n❓ POSSIBLE ISSUES:")
        print("   1. Emails might be too old (checking last 2 hours only)")
        print("   2. Email sender filter might not match exactly")
        print("   3. Emails might be in spam/other folders")

if __name__ == "__main__":
    main()