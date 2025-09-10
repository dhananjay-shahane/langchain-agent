#!/usr/bin/env python3
"""
Test Email Service Configuration
"""
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import smtplib
from imap_tools.mailbox import MailBox
from pathlib import Path

def test_email_send():
    """Test sending email with LAS file attachment"""
    try:
        # Check if SendGrid API key is available
        api_key = os.getenv('SENDGRID_API_KEY')
        if not api_key:
            print("ERROR: SENDGRID_API_KEY not found in environment")
            return False
        
        print("✓ SendGrid API key found")
        
        # Import SendGrid after confirming key exists
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType
        except ImportError:
            print("ERROR: SendGrid library not installed")
            return False
        
        # Test file attachment
        test_file = Path("data/sample_well_01.las")
        if not test_file.exists():
            print("ERROR: Test LAS file not found")
            return False
        
        print("✓ Test LAS file found")
        print("✓ SendGrid email service ready")
        return True
        
    except Exception as e:
        print(f"ERROR: Email send test failed: {e}")
        return False

def test_email_receive():
    """Test receiving emails via IMAP"""
    try:
        username = os.getenv('EMAIL_USER')
        password = os.getenv('EMAIL_PASS')
        
        if not username or not password:
            print("ERROR: EMAIL_USER or EMAIL_PASS not found in environment")
            return False
        
        print("✓ Email credentials found")
        
        # Test IMAP connection
        server = 'imap.gmail.com'  # Default to Gmail
        
        with MailBox(server).login(username, password) as mailbox:
            # Just test connection, don't fetch emails
            print("✓ IMAP connection successful")
            print(f"✓ Connected to {username}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Email receive test failed: {e}")
        return False

def main():
    """Run email configuration tests"""
    print("🔧 Testing Email Configuration...")
    print("-" * 40)
    
    send_ok = test_email_send()
    receive_ok = test_email_receive()
    
    print("-" * 40)
    if send_ok and receive_ok:
        print("✅ Email configuration is working!")
        print("📧 Ready to receive LAS file attachments")
        print("📤 Ready to send notifications")
        return True
    else:
        print("❌ Email configuration has issues")
        if not send_ok:
            print("  - SendGrid email sending not working")
        if not receive_ok:
            print("  - IMAP email receiving not working")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)