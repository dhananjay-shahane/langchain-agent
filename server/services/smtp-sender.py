#!/usr/bin/env python3
"""
SMTP Email Sender for Automated Replies
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.username = os.getenv('EMAIL_USER')
        self.password = os.getenv('EMAIL_PASS')
        
        if not self.username or not self.password:
            logger.error("Email credentials not found. Set EMAIL_USER and EMAIL_PASS environment variables.")
    
    def send_reply(self, to_email: str, subject: str, body: str, attachment_path: str = None):
        """Send email reply with optional attachment"""
        try:
            if not self.username or not self.password:
                logger.error("Cannot send email: credentials not configured")
                return False
            
            logger.info(f"Sending email to: {to_email}")
            logger.info(f"Subject: Re: {subject}")
            logger.info(f"Has attachment: {attachment_path is not None}")
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = to_email
            msg['Subject'] = f"Re: {subject}"
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Add attachment if provided
            if attachment_path and Path(attachment_path).exists():
                try:
                    with open(attachment_path, "rb") as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                    
                    encoders.encode_base64(part)
                    filename = Path(attachment_path).name
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {filename}'
                    )
                    msg.attach(part)
                    logger.info(f"Added attachment: {filename}")
                except Exception as e:
                    logger.warning(f"Could not attach file {attachment_path}: {e}")
            
            # Connect and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                
                text = msg.as_string()
                server.sendmail(self.username, to_email, text)
            
            logger.info(f"✅ Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

def send_analysis_reply(to_email: str, original_subject: str, las_filename: str, plot_path: str):
    """Send automated reply with analysis results"""
    sender = EmailSender()
    
    subject = f"LAS Analysis Results - {las_filename}"
    
    body = f"""Hello,

Thank you for sending the LAS file "{las_filename}". I have successfully processed your request and generated the requested analysis.

Please find the attached plot with your LAS file analysis results.

Analysis Details:
- File processed: {las_filename}
- Analysis type: As requested in your email
- Generated plot attached

If you need any additional analysis or have questions about the results, please feel free to reply to this email.

Best regards,
Automated LAS Analysis System
"""
    
    success = sender.send_reply(to_email, original_subject, body, plot_path)
    return success

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 4:
        to_email = sys.argv[1]
        subject = sys.argv[2]
        las_file = sys.argv[3]
        plot_path = sys.argv[4] if len(sys.argv) > 4 else None
        
        success = send_analysis_reply(to_email, subject, las_file, plot_path)
        sys.exit(0 if success else 1)
    else:
        print("Usage: python smtp-sender.py <to_email> <subject> <las_file> [plot_path]")
        sys.exit(1)