#!/usr/bin/env python3
"""
Email Monitor for Incoming LAS File Attachments
"""
import asyncio
import time
import os
import shutil
import json
from pathlib import Path
from typing import List, Optional
from imap_tools.mailbox import MailBox
from imap_tools.query import A
from subprocess import Popen, PIPE
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmailAttachmentMonitor:
    def __init__(self):
        self.server = os.getenv('IMAP_SERVER', 'imap.gmail.com')
        self.username = os.getenv('EMAIL_USER')
        self.password = os.getenv('EMAIL_PASS')
        self.download_dir = Path("data")
        self.download_dir.mkdir(exist_ok=True)
        self.processed_uids = set()
        
        # Parse filter emails from environment variable
        filter_emails_str = os.getenv('FILTER_EMAIL', '')
        self.filter_emails = []
        if filter_emails_str:
            # Remove brackets and split by comma, then clean up each email
            clean_str = filter_emails_str.strip('[]')
            self.filter_emails = [email.strip().strip('\'"') for email in clean_str.split(',') if email.strip()]
            logger.info(f"Filtering emails from: {self.filter_emails}")
        
        if not self.username or not self.password:
            logger.warning("Email credentials not found in environment variables")
            logger.warning("Set EMAIL_USER and EMAIL_PASS to enable email monitoring")
    
    def _store_email_in_database(self, message, las_files_saved):
        """Store email information in the database via HTTP API"""
        try:
            email_data = {
                "uid": str(message.uid),
                "sender": str(message.from_),
                "subject": message.subject or "",
                "content": message.text or message.html or "",
                "hasAttachments": len(message.attachments) > 0,
                "processed": False,
                "autoProcessed": False,
                "relatedLasFiles": las_files_saved,
                "relatedOutputFiles": [],
                "replyEmailSent": False,
                "receivedAt": message.date.isoformat() if message.date else None
            }
            
            # Send to local API endpoint to store in database
            import requests
            response = requests.post('http://localhost:5000/api/emails/store', json=email_data, timeout=5)
            if response.status_code == 200:
                logger.info(f"📧 Email stored in database: {email_data['uid']}")
                return response.json().get('email_id')
            else:
                logger.warning(f"Failed to store email in database: {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"Could not store email in database: {e}")
            return None
    
    def _should_auto_process_email(self, message):
        """Determine if email should be automatically processed"""
        content = (message.text or message.html or "").lower()
        subject = (message.subject or "").lower()
        
        # Keywords that indicate analysis request
        analysis_keywords = [
            'gamma ray', 'gamma', 'porosity', 'resistivity', 'plot', 'chart', 
            'analysis', 'analyze', 'graph', 'curve', 'log', 'well log',
            'create plot', 'generate plot', 'make plot', 'show plot'
        ]
        
        return any(keyword in content or keyword in subject for keyword in analysis_keywords)
    
    def _extract_analysis_type(self, message):
        """Extract what type of analysis is requested"""
        content = (message.text or message.html or "").lower()
        subject = (message.subject or "").lower()
        full_text = f"{subject} {content}"
        
        if 'gamma' in full_text:
            return 'gamma'
        elif 'porosity' in full_text:
            return 'porosity'  
        elif 'resistivity' in full_text:
            return 'resistivity'
        else:
            return 'gamma'  # Default to gamma ray
    
    def _trigger_automatic_processing(self, email_id, las_filename, analysis_type, sender_email, subject):
        """Trigger automatic LAS file analysis"""
        try:
            logger.info(f"🤖 Starting automatic processing for {las_filename}")
            
            # Call the plotting script
            plot_script = Path(os.getcwd()) / "scripts" / "las_plotter.py"
            result = Popen([
                "python", str(plot_script), las_filename, analysis_type
            ], stdout=PIPE, stderr=PIPE, text=True)
            
            stdout, stderr = result.communicate(timeout=60)
            
            if result.returncode == 0:
                # Extract generated filename from output
                for line in stdout.split('\n'):
                    if line.startswith('SUCCESS:'):
                        plot_filename = line.replace('SUCCESS:', '').strip()
                        plot_path = Path("output") / plot_filename
                        
                        if plot_path.exists():
                            logger.info(f"📊 Plot generated: {plot_filename}")
                            
                            # Send email reply with attachment
                            self._send_analysis_reply(sender_email, subject, las_filename, str(plot_path))
                            
                            # Update email as processed
                            self._update_email_processed(email_id, [plot_filename])
                            return True
                        break
                
                logger.warning(f"Plot generated but file not found in output")
            else:
                logger.error(f"Plot generation failed: {stderr}")
                
        except Exception as e:
            logger.error(f"Automatic processing failed: {e}")
            
        return False
    
    def _send_analysis_reply(self, to_email, original_subject, las_filename, plot_path):
        """Send automated reply email with analysis results"""
        try:
            smtp_script = Path(os.getcwd()) / "server" / "services" / "smtp-sender.py"
            result = Popen([
                "python", str(smtp_script), to_email, original_subject, las_filename, plot_path
            ], stdout=PIPE, stderr=PIPE, text=True)
            
            stdout, stderr = result.communicate(timeout=30)
            
            if result.returncode == 0:
                logger.info(f"📧 Reply sent to {to_email}")
                return True
            else:
                logger.error(f"Failed to send reply: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending reply email: {e}")
            return False
    
    def _update_email_processed(self, email_id, output_files):
        """Update email as processed with generated files"""
        try:
            if not email_id:
                return
                
            update_data = {
                "processed": True,
                "autoProcessed": True,
                "relatedOutputFiles": output_files,
                "replyEmailSent": True
            }
            
            import requests
            response = requests.patch(f'http://localhost:5000/api/emails/{email_id}', 
                                    json=update_data, timeout=5)
            if response.status_code == 200:
                logger.info(f"✅ Email marked as processed: {email_id}")
            else:
                logger.warning(f"Failed to update email status: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Could not update email status: {e}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage"""
        import re
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        return safe_name[:255]
    
    def _should_process_attachment(self, attachment) -> bool:
        """Check if attachment should be processed"""
        if not attachment.filename:
            return False
        
        # Check file extension
        if not attachment.filename.lower().endswith('.las'):
            return False
        
        # Check file size (limit to 50MB)
        size_mb = len(attachment.payload) / (1024 * 1024)
        if size_mb > 50:
            logger.warning(f"Attachment {attachment.filename} too large: {size_mb:.2f}MB")
            return False
        
        return True
    
    def _save_attachment(self, attachment, message) -> Optional[str]:
        """Save attachment to data directory"""
        try:
            safe_filename = self._sanitize_filename(attachment.filename)
            file_path = self.download_dir / safe_filename
            
            # Handle duplicates
            counter = 1
            original_path = file_path
            while file_path.exists():
                stem = original_path.stem
                suffix = original_path.suffix
                file_path = self.download_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(attachment.payload)
            
            logger.info(f"💾 LAS FILE SAVED: {file_path.name} -> data/{file_path.name}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error saving {attachment.filename}: {e}")
            return None
    
    async def process_new_emails(self):
        """Process new emails for LAS attachments"""
        if not self.username or not self.password:
            return
        
        try:
            with MailBox(self.server).login(self.username, self.password) as mailbox:
                # Get recent emails with attachments (last 24 hours, including read ones)
                from datetime import datetime, timedelta
                yesterday = datetime.now() - timedelta(days=1)
                
                # First try unread emails
                messages = list(mailbox.fetch(A(seen=False)))
                logger.info(f"Found {len(messages)} unread emails")
                
                # If no unread emails, check recent emails from last 24 hours
                if len(messages) == 0:
                    messages = list(mailbox.fetch(A(date_gte=yesterday.date())))
                    logger.info(f"Checking {len(messages)} recent emails from last 24 hours")
                
                for message in messages:
                    # Skip if already processed
                    if message.uid in self.processed_uids:
                        continue
                    
                    # Filter by sender email if filter is configured
                    sender_email = str(message.from_).lower()
                    if self.filter_emails:
                        email_matches = any(filter_email.lower() in sender_email for filter_email in self.filter_emails)
                        if not email_matches:
                            logger.info(f"Skipping email from {sender_email} (not in filter list)")
                            continue
                    
                    logger.info(f"📧 RECEIVED EMAIL - ID: {message.uid}")
                    logger.info(f"   From: {message.from_}")
                    logger.info(f"   Subject: {message.subject}")
                    logger.info(f"   Date: {message.date}")
                    logger.info(f"   Attachments: {len(message.attachments)}")
                    las_files_found = 0
                    
                    las_files_saved = []
                    # Process attachments if they exist
                    if message.attachments:
                        for attachment in message.attachments:
                            logger.info(f"Checking attachment: {attachment.filename} (size: {len(attachment.payload) / 1024:.1f}KB)")
                            if self._should_process_attachment(attachment):
                                logger.info(f"Processing LAS attachment: {attachment.filename}")
                                saved_path = self._save_attachment(attachment, message)
                                if saved_path:
                                    las_files_found += 1
                                    las_files_saved.append(saved_path)
                            else:
                                logger.info(f"Skipping attachment: {attachment.filename} (not a .las file or too large)")
                    else:
                        logger.info("No attachments in this email")
                    
                    # Store email in database (even if no LAS files)
                    saved_las_filenames = [Path(path).name for path in las_files_saved] if las_files_found > 0 else []
                    email_id = self._store_email_in_database(message, saved_las_filenames)
                    
                    if las_files_found > 0:
                        logger.info(f"✅ SUCCESS: Saved {las_files_found} LAS file(s) from Email ID {message.uid} ({message.from_})")
                        
                        # Check if this email should be automatically processed
                        if self._should_auto_process_email(message) and saved_las_filenames:
                            analysis_type = self._extract_analysis_type(message)
                            logger.info(f"🤖 Auto-processing triggered: {analysis_type} analysis for {saved_las_filenames[0]}")
                            
                            # Trigger automatic processing
                            success = self._trigger_automatic_processing(
                                email_id, 
                                saved_las_filenames[0], 
                                analysis_type,
                                str(message.from_),
                                message.subject or ""
                            )
                            
                            if success:
                                logger.info(f"🎉 Automatic processing completed for Email ID {message.uid}")
                            else:
                                logger.warning(f"⚠️  Automatic processing failed for Email ID {message.uid}")
                    else:
                        logger.info(f"📧 Email received from {message.from_} - No LAS files found")
                    
                    # Mark email as read and remember we processed it (only for unread emails)
                    if hasattr(message, 'seen') and not message.seen:
                        mailbox.flag([str(message.uid)], '\\Seen', True)
                    self.processed_uids.add(message.uid)
                    
        except Exception as e:
            logger.error(f"Error processing emails: {e}")
    
    async def run_monitor(self, check_interval: int = 10):
        """Run the email monitor continuously"""
        logger.info(f"Starting email monitor (checking every {check_interval} seconds)")
        
        while True:
            try:
                await self.process_new_emails()
                await asyncio.sleep(check_interval)
            except KeyboardInterrupt:
                logger.info("Email monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(check_interval)

async def main():
    """Main function"""
    monitor = EmailAttachmentMonitor()
    await monitor.run_monitor()

if __name__ == "__main__":
    asyncio.run(main())
