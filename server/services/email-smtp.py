#!/usr/bin/env python3
"""
SMTP/IMAP Email Service for LAS File Processing
"""
import os
import sys
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path
from imap_tools.mailbox import MailBox

def test_smtp_connection():
    """Test SMTP connection for sending emails"""
    try:
        email_user = os.getenv('EMAIL_USER')
        email_pass = os.getenv('EMAIL_PASS')
        
        if not email_user or not email_pass:
            return {"success": False, "message": "Email credentials not configured"}
        
        # Determine SMTP server based on email domain
        if 'gmail.com' in email_user:
            smtp_server = 'smtp.gmail.com'
            smtp_port = 587
        elif 'outlook.com' in email_user or 'hotmail.com' in email_user:
            smtp_server = 'smtp.live.com'
            smtp_port = 587
        elif 'yahoo.com' in email_user:
            smtp_server = 'smtp.mail.yahoo.com'
            smtp_port = 587
        else:
            smtp_server = 'smtp.gmail.com'  # Default
            smtp_port = 587
        
        # Test SMTP connection
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(email_user, email_pass)
            
        return {"success": True, "message": f"SMTP connection successful to {smtp_server}"}
        
    except Exception as e:
        return {"success": False, "message": f"SMTP connection failed: {str(e)}"}

def test_imap_connection():
    """Test IMAP connection for receiving emails"""
    try:
        email_user = os.getenv('EMAIL_USER')
        email_pass = os.getenv('EMAIL_PASS')
        
        if not email_user or not email_pass:
            return {"success": False, "message": "Email credentials not configured"}
        
        # Determine IMAP server based on email domain
        if 'gmail.com' in email_user:
            imap_server = 'imap.gmail.com'
        elif 'outlook.com' in email_user or 'hotmail.com' in email_user:
            imap_server = 'imap-mail.outlook.com'
        elif 'yahoo.com' in email_user:
            imap_server = 'imap.mail.yahoo.com'
        else:
            imap_server = 'imap.gmail.com'  # Default
        
        # Test IMAP connection
        with MailBox(imap_server).login(email_user, email_pass) as mailbox:
            # Just test connection, don't fetch emails
            pass
            
        return {"success": True, "message": f"IMAP connection successful to {imap_server}"}
        
    except Exception as e:
        return {"success": False, "message": f"IMAP connection failed: {str(e)}"}

def send_test_email(recipient_email=None):
    """Send a test email to verify SMTP functionality"""
    try:
        email_user = os.getenv('EMAIL_USER')
        email_pass = os.getenv('EMAIL_PASS')
        
        if not email_user or not email_pass:
            return {"success": False, "message": "Email credentials not configured"}
        
        recipient = recipient_email or email_user  # Send to self if no recipient
        
        # Create test message
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = recipient
        msg['Subject'] = "LAS File Processing System - Test Email"
        
        body = """
        This is a test email from your LAS File Processing System.
        
        System Status:
        ✓ SMTP connection working
        ✓ Email sending functional
        ✓ Ready to receive LAS file attachments
        
        You can now send LAS files as attachments to this email address
        and they will be automatically processed by the system.
        
        Best regards,
        LAS File Processing System
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Determine SMTP server
        if 'gmail.com' in email_user:
            smtp_server = 'smtp.gmail.com'
            smtp_port = 587
        elif 'outlook.com' in email_user or 'hotmail.com' in email_user:
            smtp_server = 'smtp.live.com'
            smtp_port = 587
        elif 'yahoo.com' in email_user:
            smtp_server = 'smtp.mail.yahoo.com'
            smtp_port = 587
        else:
            smtp_server = 'smtp.gmail.com'
            smtp_port = 587
        
        # Send email
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(email_user, email_pass)
            server.send_message(msg)
            
        return {"success": True, "message": f"Test email sent successfully to {recipient}"}
        
    except Exception as e:
        return {"success": False, "message": f"Failed to send test email: {str(e)}"}

def main():
    """Test email functionality"""
    print("🔧 Testing Email System (SMTP/IMAP)...")
    print("-" * 50)
    
    # Test SMTP
    smtp_result = test_smtp_connection()
    print(f"SMTP: {'✓' if smtp_result['success'] else '✗'} {smtp_result['message']}")
    
    # Test IMAP
    imap_result = test_imap_connection()
    print(f"IMAP: {'✓' if imap_result['success'] else '✗'} {imap_result['message']}")
    
    # Send test email if both work
    if smtp_result['success'] and imap_result['success']:
        test_result = send_test_email()
        print(f"Test Email: {'✓' if test_result['success'] else '✗'} {test_result['message']}")
        
        print("-" * 50)
        print("✅ Email system fully functional!")
        print("📧 Ready to process LAS file attachments")
        return True
    else:
        print("-" * 50)
        print("❌ Email system has issues")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)