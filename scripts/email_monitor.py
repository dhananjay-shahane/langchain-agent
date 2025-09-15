#!/usr/bin/env python3
"""
Email Monitor Service for LAS File Analysis System

This script monitors Gmail IMAP for new emails and saves them to JSON format
with their attachments. It's designed to be started/stopped via API calls.
"""

import os
import sys
import json
import email
import time
import signal
import requests
from pathlib import Path
import ssl
import socket
from imapclient import IMAPClient

# Configuration
IMAP_SERVER = "imap.gmail.com"
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASS")
API_BASE_URL = "http://localhost:5000/api"

# Paths
DATA_DIR = Path("data")
ATTACHMENTS_DIR = DATA_DIR / "email-attachments"
STATUS_FILE = Path("scripts/email_monitor_status.json")

# Create necessary directories
ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)


class EmailMonitor:

    def __init__(self):
        self.running = False
        self.client = None
        self.last_uid = 0

        # Validate environment variables
        if not EMAIL_USER or not EMAIL_PASSWORD:
            print(
                "❌ EMAIL_USER and EMAIL_PASSWORD environment variables are required"
            )
            sys.exit(1)

        # Ensure we have valid string values
        self.email_user = EMAIL_USER
        self.email_password = EMAIL_PASSWORD

        # Signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"📱 Received signal {signum}, shutting down gracefully...")
        self.stop()
        sys.exit(0)

    def update_status(self, is_running, error=None, emails_processed=None):
        """Update monitor status via API"""
        try:
            data = {"isRunning": is_running}
            if error:
                data["lastError"] = str(error)
            if emails_processed is not None:
                data["emailsProcessed"] = str(emails_processed)

            if is_running:
                data["lastStarted"] = time.time(
                ) * 1000  # Convert to milliseconds for JavaScript
            else:
                data["lastStopped"] = time.time(
                ) * 1000  # Convert to milliseconds for JavaScript

            response = requests.put(f"{API_BASE_URL}/emails/monitor/status",
                                    json=data)
            if response.status_code == 200:
                print(f"✅ Status updated: Running={is_running}")
            else:
                print(f"⚠️ Failed to update status: {response.status_code}")
        except Exception as e:
            print(f"❌ Error updating status: {e}")

    def save_email_to_api(self, entry):
        """Save email entry via API"""
        try:
            response = requests.post(f"{API_BASE_URL}/emails", json=entry)
            if response.status_code == 201:
                print(f"✅ Email saved to database: UID {entry['uid']}")
                return True
            else:
                print(
                    f"⚠️ Failed to save email: {response.status_code} - {response.text}"
                )
                return False
        except Exception as e:
            print(f"❌ Error saving email to API: {e}")
            return False

    def process_new_email(self, uid, msg):
        """Extract email details and save"""
        try:
            subject = msg.get("Subject", "No Subject")
            from_ = msg.get("From", "Unknown")

            # Extract plain text body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type(
                    ) == "text/plain" and not part.get_filename():
                        try:
                            body = part.get_payload(decode=True).decode(
                                "utf-8", errors="ignore")
                            break
                        except Exception:
                            pass
            else:
                try:
                    body = msg.get_payload(decode=True).decode("utf-8",
                                                               errors="ignore")
                except Exception:
                    pass

            # Handle attachments
            attachments = []
            if msg.is_multipart():
                for part in msg.walk():
                    filename = part.get_filename()
                    if filename:
                        # Save attachment to disk
                        filepath = ATTACHMENTS_DIR / filename
                        try:
                            with open(filepath, "wb") as f:
                                f.write(part.get_payload(decode=True))
                            attachments.append(filename)
                            print(f"📎 Saved attachment: {filename}")
                        except Exception as e:
                            print(f"❌ Error saving attachment {filename}: {e}")

            # Create email entry
            entry = {
                "uid": str(uid),
                "from": from_,
                "subject": subject,
                "body": body.strip(),
                "attachments": attachments,
                "replyStatus": "pending"
            }

            print(
                f"📧 Processing Email UID {uid} | From: {from_} | Subject: {subject}"
            )

            # Save to database via API
            if self.save_email_to_api(entry):
                return True
            else:
                print(f"❌ Failed to save email UID {uid}")
                return False

        except Exception as e:
            print(f"❌ Error processing email UID {uid}: {e}")
            return False

    def connect(self):
        """Connect to IMAP server"""
        try:
            ctx = ssl.create_default_context()
            if hasattr(ssl, "TLSVersion"):
                ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            self.client = IMAPClient(IMAP_SERVER,
                                     port=993,
                                     ssl=True,
                                     ssl_context=ctx,
                                     timeout=30)
            self.client.login(self.email_user, self.email_password)
            self.client.select_folder("INBOX")
            print(f"✅ Connected to {IMAP_SERVER}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            self.update_status(False, error=str(e))
            return False

    def disconnect(self):
        """Disconnect from IMAP server"""
        if self.client:
            try:
                self.client.logout()
                print("📤 Disconnected from IMAP server")
            except Exception as e:
                print(f"⚠️ Error during disconnect: {e}")
            finally:
                self.client = None

    def start(self):
        """Start email monitoring"""
        if self.running:
            print("⚠️ Monitor is already running")
            return

        print("🚀 Starting email monitor...")
        self.running = True
        self.update_status(True)

        if not self.connect():
            self.running = False
            return

        try:
            # Get baseline UID (ignore old emails)
            if self.client:
                all_messages = self.client.search("ALL")
            else:
                return
            self.last_uid = max(all_messages) if all_messages else 0
            print(f"👉 Monitoring from UID {self.last_uid}")

            emails_processed = 0

            while self.running:
                try:
                    # Keep connection alive
                    if self.client:
                        self.client.noop()

                    # Check for new messages
                    if self.client:
                        all_messages = self.client.search("ALL")
                    else:
                        continue
                    new_messages = [
                        uid for uid in all_messages if uid > self.last_uid
                    ]

                    if new_messages:
                        for uid in sorted(new_messages):
                            if not self.running:
                                break

                            try:
                                if self.client:
                                    msg_data = self.client.fetch([uid],
                                                                 ["RFC822"])
                                    raw_email = msg_data[uid][b"RFC822"]
                                    if isinstance(raw_email, bytes):
                                        msg = email.message_from_bytes(
                                            raw_email)
                                    else:
                                        print(
                                            f"❌ Invalid email data type for UID {uid}"
                                        )
                                        continue
                                else:
                                    break

                                if self.process_new_email(uid, msg):
                                    emails_processed += 1
                                    self.update_status(
                                        True,
                                        emails_processed=emails_processed)

                                self.last_uid = max(self.last_uid, uid)
                            except Exception as e:
                                print(
                                    f"❌ Error processing email UID {uid}: {e}")
                    else:
                        print("✅ No new emails found")

                    # Wait before next check
                    for _ in range(30):  # 30 second wait with 1-second checks
                        if not self.running:
                            break
                        time.sleep(1)

                except (ssl.SSLError, ssl.SSLEOFError, ConnectionResetError,
                        TimeoutError, socket.timeout) as e:
                    print(f"⚠️ Transient IMAP/SSL error: {e} — reconnecting")
                    self.disconnect()
                    time.sleep(5)
                    if not self.connect():
                        time.sleep(10)
                    continue
                except Exception as e:
                    print(f"❌ Error in monitoring loop: {e}")
                    self.update_status(False, error=str(e))
                    time.sleep(10)

        except Exception as e:
            print(f"❌ Critical error in email monitor: {e}")
            self.update_status(False, error=str(e))
        finally:
            self.disconnect()
            self.running = False
            self.update_status(False)

    def stop(self):
        """Stop email monitoring"""
        if not self.running:
            print("⚠️ Monitor is not running")
            return

        print("🛑 Stopping email monitor...")
        self.running = False
        self.update_status(False)


def main():
    """Main entry point"""
    if len(sys.argv) != 2 or sys.argv[1] not in ["start", "stop"]:
        print("Usage: python email_monitor.py [start|stop]")
        sys.exit(1)

    command = sys.argv[1]
    monitor = EmailMonitor()

    if command == "start":
        monitor.start()
    elif command == "stop":
        monitor.stop()


if __name__ == "__main__":
    main()
