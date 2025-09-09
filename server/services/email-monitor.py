#!/usr/bin/env python3
"""
Email Monitor for Incoming LAS File Attachments
"""
import asyncio
import time
import os
import shutil
from pathlib import Path
from typing import List, Optional
from imap_tools.mailbox import MailBox
from imap_tools.query import A
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
        
        if not self.username or not self.password:
            logger.warning("Email credentials not found in environment variables")
            logger.warning("Set EMAIL_USER and EMAIL_PASS to enable email monitoring")
    
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
            
            logger.info(f"Saved LAS file: {file_path}")
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
                    if not message.attachments:
                        continue
                    if message.uid in self.processed_uids:
                        continue
                    
                    logger.info(f"Processing email: {message.subject} from {message.from_}")
                    logger.info(f"Email has {len(message.attachments)} attachment(s)")
                    las_files_found = 0
                    
                    for attachment in message.attachments:
                        logger.info(f"Checking attachment: {attachment.filename} (size: {len(attachment.payload) / 1024:.1f}KB)")
                        if self._should_process_attachment(attachment):
                            logger.info(f"Processing LAS attachment: {attachment.filename}")
                            saved_path = self._save_attachment(attachment, message)
                            if saved_path:
                                las_files_found += 1
                        else:
                            logger.info(f"Skipping attachment: {attachment.filename} (not a .las file or too large)")
                    
                    if las_files_found > 0:
                        logger.info(f"Found {las_files_found} LAS file(s) in email from {message.from_}")
                    
                    # Mark email as read and remember we processed it (only for unread emails)
                    if not message.seen:
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
