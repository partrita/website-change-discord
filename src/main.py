import hashlib
import ipaddress
import logging
import os
import random
import socket
import sqlite3
import time
import sys
from datetime import datetime, timedelta
from urllib3.util import parse_url
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, List, Any, Tuple

import requests
import yaml
import schedule
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fake_useragent import UserAgent
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.ssrf_adapter import SafeAdapter

# Load environment variables
load_dotenv()

# --- Configuration Constants ---
CONFIG_FILE = "config.yaml"
DB_FILE = "hashes.db"
LOG_FILE = "app.log"
DISCORD_WEBHOOK_URL: Optional[str] = os.getenv("DISCORD_WEBHOOK_URL")
ua = UserAgent()

# --- Logging Setup ---
# ... rest of logger setup ...
logger = logging.getLogger("website-change")
logger.setLevel(logging.INFO)

# Formatter: [2026-04-06 13:20:01] [INFO] Message
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# File Handler (Max 5MB, keep 3 backup files)
file_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Stream Handler (Console output for systemd/manual run)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


def init_db(db_path: str) -> sqlite3.Connection:
    """Initialize the SQLite database and create/update the table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_hashes (
            url TEXT PRIMARY KEY,
            hash TEXT,
            last_content TEXT,
            last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Check if last_content column exists (for backward compatibility)
    cursor.execute("PRAGMA table_info(site_hashes)")
    columns = [col[1] for col in cursor.fetchall()]
    if "last_content" not in columns:
        cursor.execute("ALTER TABLE site_hashes ADD COLUMN last_content TEXT")

    conn.commit()
    return conn


def get_stored_data(cursor: sqlite3.Cursor, url: str) -> Optional[Tuple[str, str, str]]:
    """Retrieve the stored hash, last content, and last checked timestamp for a given URL."""
    cursor.execute(
        "SELECT hash, last_content, last_checked FROM site_hashes WHERE url = ?", (url,)
    )
    result = cursor.fetchone()
    return result if result else None


def update_site_data(
    conn: sqlite3.Connection, url: str, new_hash: str, new_content: str
) -> None:
    """Update or insert the hash and content for a given URL in the database."""
    cursor = conn.cursor()
    # Use ISO 8601 format for consistency
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        INSERT OR REPLACE INTO site_hashes (url, hash, last_content, last_checked)
        VALUES (?, ?, ?, ?)
    """,
        (url, new_hash, new_content, now),
    )
    conn.commit()


def load_config(file_path: str) -> Dict[str, Any]:
    """Load the YAML configuration file."""
    if not os.path.exists(file_path):
        return {"targets": []}
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            return yaml.safe_load(f) or {"targets": []}
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            return {"targets": []}


def is_safe_url(url: str) -> bool:
    """Check if a URL is safe to fetch (prevents SSRF)."""
    try:
        parsed = parse_url(url)
        hostname = parsed.host
        if not hostname:
            return False

        addr_info = socket.getaddrinfo(hostname, None)
        if not addr_info:
            return False

        for item in addr_info:
            ip_str = item[4][0]
            # Handle IPv6 zone indices (e.g., fe80::1%eth0)
            if "%" in ip_str:
                ip_str = ip_str.split("%")[0]
            ip = ipaddress.ip_address(ip_str)

            if getattr(ip, "ipv4_mapped", None):
                ip = ip.ipv4_mapped

            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_unspecified
                or ip.is_reserved
            ):
                return False
        return True
    except Exception:
        return False


class SafeSession(requests.Session):
    def rebuild_auth(self, prepared_request, response):
        if not is_safe_url(prepared_request.url):
            raise requests.exceptions.RequestException(
                f"Security Error: Blocked unsafe redirect to {prepared_request.url}"
            )
        super().rebuild_auth(prepared_request, response)


def get_html(url: str, verify: bool = True) -> Optional[str]:
    """Fetch HTML content from a URL with random headers."""
    if not url.startswith(("http://", "https://")):
        logger.error(f"Invalid URL scheme for {url}")
        return None

    if not is_safe_url(url):
        logger.error(
            f"Security: Blocked attempt to fetch unsafe or internal URL: {url}"
        )
        return None

    headers = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/",
        "DNT": "1",
    }
    try:
        time.sleep(random.uniform(1.5, 4.0))
        with SafeSession() as session:
            session.mount("http://", SafeAdapter())
            session.mount("https://", SafeAdapter())

            # Disable warnings only if verify is False
            if not verify:
                import urllib3

                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            response = session.get(
                url, headers=headers, timeout=15, stream=True, verify=verify
            )
            response.raise_for_status()

        # Read in chunks up to 5MB to prevent memory exhaustion
        MAX_SIZE = 5 * 1024 * 1024
        content = b""
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > MAX_SIZE:
                logger.error(f"Response from {url} exceeded 5MB limit.")
                response.close()
                return None

        return content.decode(response.encoding or "utf-8", errors="replace")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return None


def parse_element(html: str, selector: str) -> Optional[str]:
    """Extract text from the HTML using a CSS selector."""
    soup = BeautifulSoup(html, "html.parser")
    element = soup.select_one(selector)
    return element.get_text(strip=True) if element else None


def calculate_hash(data: str) -> str:
    """Calculate the SHA256 hash of a string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def send_discord_notification(webhook_url: Optional[str], message: str) -> None:
    """Send a notification message to a Discord webhook."""
    if not webhook_url or "YOUR_WEBHOOK_URL" in webhook_url:
        return

    # Security: Prevent SSRF by validating the webhook URL scheme and domain
    allowed_prefixes = (
        "https://discord.com/api/webhooks/",
        "https://discordapp.com/api/webhooks/",
    )
    if not webhook_url.startswith(allowed_prefixes):
        logger.error("Invalid Discord webhook URL provided (Security restriction)")
        return

    payload = {
        "content": message,
        "allowed_mentions": {
            "parse": []
        },  # Prevent malicious pings from scraped content
    }
    try:
        with SafeSession() as session:
            adapter = SafeAdapter()
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            response = session.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
    except Exception:
        # Avoid logging the exception object directly as it contains the secret webhook URL
        logger.error("Discord notification error (URL redacted for security)")


def process_target(
    conn: sqlite3.Connection, target: Dict[str, Any], global_webhook: Optional[str]
) -> None:
    """Check a single target for changes if the interval has passed."""
    name = target.get("name", target["url"])
    url = target["url"]
    selector = target["selector"]
    webhook = target.get("webhook_url") or global_webhook
    interval_hours = target.get("interval_hours", 24)
    verify_ssl = target.get("verify_ssl", True)

    stored_data = get_stored_data(conn.cursor(), url)
    if stored_data:
        previous_hash, previous_content, last_checked_str = stored_data
        if last_checked_str:
            last_checked = datetime.strptime(last_checked_str, "%Y-%m-%d %H:%M:%S")
            # Using 2-minute buffer for systemd timer variations
            if datetime.now() < last_checked + timedelta(
                hours=interval_hours
            ) - timedelta(minutes=2):
                logger.info(f"Skipping: {name} (Interval not reached)")
                return
    else:
        previous_hash, previous_content = None, None

    logger.info(f"Checking: {name} ({url})")
    html = get_html(url, verify=verify_ssl)
    if not html:
        return

    parsed_data = parse_element(html, selector)
    if parsed_data is None:
        logger.warning(f"Selector '{selector}' not found on {name}")
        return

    current_hash = calculate_hash(parsed_data)

    if stored_data is None:
        logger.info(f"Initial check for {name}. Data saved.")
        update_site_data(conn, url, current_hash, parsed_data)
        return

    if current_hash != previous_hash:
        logger.info(f"CHANGE DETECTED for {name}!")
        # Create a brief summary of changes
        old_text = (
            (previous_content[:100] + "...")
            if previous_content and len(previous_content) > 100
            else (previous_content or "N/A")
        )
        new_text = (
            (parsed_data[:100] + "...") if len(parsed_data) > 100 else parsed_data
        )

        message = (
            f"🔔 **[{name}] 웹사이트 변동 감지!**\n"
            f"🔗 **URL**: {url}\n"
            f"--------------------------------------------\n"
            f"🔹 **이전 내용**:\n{old_text}\n\n"
            f"🔸 **현재 내용**:\n{new_text}\n"
            f"--------------------------------------------"
        )
        send_discord_notification(webhook, message)
        update_site_data(conn, url, current_hash, parsed_data)
    else:
        logger.info(f"No changes for {name}.")
        # Update last_checked even if no change was detected
        update_site_data(conn, url, current_hash, parsed_data)


def run_job() -> None:
    """Main job function."""
    logger.info("Starting scan...")
    config = load_config(CONFIG_FILE)
    global_webhook = DISCORD_WEBHOOK_URL
    targets: List[Dict[str, Any]] = config.get("targets", [])

    if not targets:
        logger.warning("No targets found in config.")
        return

    conn = init_db(DB_FILE)
    try:
        for target in targets:
            process_target(conn, target, global_webhook)
            time.sleep(random.uniform(2.0, 5.0))
    finally:
        conn.close()
    logger.info("Scan completed.")


class ConfigChangeHandler(FileSystemEventHandler):
    """Handler for config file modification events."""

    def __init__(self, callback: Any) -> None:
        self.callback = callback

    def on_modified(self, event: Any) -> None:
        if event.src_path.endswith(CONFIG_FILE):
            logger.info(
                f"Config file {CONFIG_FILE} changed. Triggering immediate scan..."
            )
            self.callback()


def main() -> None:
    """Main entry point."""
    if "--daemon" in sys.argv:
        logger.info("Running in daemon mode. Monitoring config changes.")
        run_job()  # Initial scan on startup

        # Schedule hourly scan
        schedule.every(1).hours.do(run_job)

        # Setup watchdog to monitor config file changes
        event_handler = ConfigChangeHandler(run_job)
        observer = Observer()
        # Watch the current directory for the config file
        observer.schedule(event_handler, path=".", recursive=False)
        observer.start()

        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Stopping daemon...")
            observer.stop()
        observer.join()
    else:
        # One-off scan
        run_job()


if __name__ == "__main__":
    main()
