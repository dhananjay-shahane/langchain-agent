#!/usr/bin/env python3
"""
Test Email Service - Check for recent emails in Gmail
"""
import os
import sys
import logging
from datetime import datetime
try:
    from imapclient import IMAPClient
except ImportError:
    print("imapclient library not found")
    exit(1)
import email
from email.header import decode_header

def decode_header_value(value):
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
        return str(value)

def test_email_receive():
    """Test receiving emails via IMAP and check for recent emails"""
    try:
        username = os.getenv('EMAIL_USER')
        password = os.getenv('EMAIL_PASS')
        
        if not username or not password:
            print("ERROR: EMAIL_USER or EMAIL_PASS not found in environment")
            return False
        
        print(f"✅ Email credentials found: {username}")
        
        # Test IMAP connection
        server = IMAPClient('imap.gmail.com')
        server.login(username, password)
        server.select_folder('INBOX')
        
        print("✅ IMAP connection successful")
        
        # Check for all emails
        all_emails = server.search('ALL')
        print(f"📧 Total emails in inbox: {len(all_emails)}")
        
        # Check for unseen emails
        unseen_emails = server.search('UNSEEN')
        print(f"📬 Unseen emails: {len(unseen_emails)}")
        
        # Check recent emails (last 20)
        recent_emails = all_emails[-20:] if len(all_emails) >= 20 else all_emails
        print(f"🔍 Checking {len(recent_emails)} most recent emails:")
        print("-" * 60)
        
        for i, uid in enumerate(reversed(recent_emails)):  # Show newest first
            try:
                response = server.fetch([uid], ['RFC822'])
                if uid in response:
                    email_data = response[uid][b'RFC822']
                    email_message = email.message_from_bytes(email_data)
                    
                    # Get email details
                    sender = decode_header_value(email_message.get('From', 'Unknown'))
                    subject = decode_header_value(email_message.get('Subject', 'No Subject'))
                    date = email_message.get('Date', 'No Date')
                    
                    # Check if unseen
                    flags_response = server.fetch([uid], ['FLAGS'])
                    flags = flags_response[uid][b'FLAGS'] if uid in flags_response else []
                    is_unseen = b'\\Seen' not in flags
                    
                    status = "🆕 UNSEEN" if is_unseen else "👁️ SEEN"
                    
                    print(f"{i+1:2}. {status} | UID: {uid}")
                    print(f"    From: {sender}")
                    print(f"    Subject: {subject}")
                    print(f"    Date: {date}")
                    print("-" * 60)
                    
            except Exception as e:
                print(f"Error processing email UID {uid}: {e}")
        
        if unseen_emails:
            print(f"\n🎯 Found {len(unseen_emails)} UNSEEN emails!")
            print(f"📧 Unseen UIDs: {unseen_emails}")
        else:
            print("\n📭 No unseen emails found")
        
        server.logout()
        return True
        
    except Exception as e:
        print(f"ERROR: Email receive test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run email configuration tests"""
    print("🔧 Testing Gmail Email Connection...")
    print("=" * 60)
    
    receive_ok = test_email_receive()
    
    print("=" * 60)
    if receive_ok:
        print("✅ Email connection is working!")
        print("📧 Ready to monitor for new emails")
        return True
    else:
        print("❌ Email connection has issues")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)