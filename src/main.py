import hashlib
import os
import random
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple

import requests
import yaml
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fake_useragent import UserAgent

# Load environment variables
load_dotenv()

# --- Configuration Constants ---
CONFIG_FILE = "config.yaml"
DB_FILE = "hashes.db"
DISCORD_WEBHOOK_URL: Optional[str] = os.getenv("DISCORD_WEBHOOK_URL")
ua = UserAgent()


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
    cursor.execute("SELECT hash, last_content, last_checked FROM site_hashes WHERE url = ?", (url,))
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
        return yaml.safe_load(f) or {"targets": []}


def get_html(url: str) -> Optional[str]:
    """Fetch HTML content from a URL with random headers."""
    headers = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/",
        "DNT": "1",
    }
    try:
        time.sleep(random.uniform(1.5, 4.0))
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"[-] [Error] {url}: {e}")
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
    payload = {"content": message}
    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        print(f"[-] Discord error: {e}")


def process_target(
    conn: sqlite3.Connection, target: Dict[str, Any], global_webhook: Optional[str]
) -> None:
    """Check a single target for changes if the interval has passed."""
    name = target.get("name", target["url"])
    url = target["url"]
    selector = target["selector"]
    webhook = target.get("webhook_url") or global_webhook
    interval_hours = target.get("interval_hours", 24)

    stored_data = get_stored_data(conn.cursor(), url)
    if stored_data:
        previous_hash, previous_content, last_checked_str = stored_data
        if last_checked_str:
            last_checked = datetime.strptime(last_checked_str, "%Y-%m-%d %H:%M:%S")
            if datetime.now() < last_checked + timedelta(hours=interval_hours):
                print(f"[-] Skipping: {name} (Interval not reached)")
                return
    else:
        previous_hash, previous_content = None, None

    print(f"[*] Checking: {name}...", end=" ", flush=True)
    html = get_html(url)
    if not html:
        print("Failed (HTTP error)")
        return

    parsed_data = parse_element(html, selector)
    if parsed_data is None:
        print("Failed (Selector not found)")
        return

    current_hash = calculate_hash(parsed_data)

    if stored_data is None:
        print("Initial check. Data saved.")
        update_site_data(conn, url, current_hash, parsed_data)
        return

    if current_hash != previous_hash:
        print("CHANGE DETECTED!")
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
        print("No changes.")
        # Update last_checked even if no change was detected
        update_site_data(conn, url, current_hash, parsed_data)


def run_job() -> None:
    """Main job function."""
    print(f"\n[*] Starting scan at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    config = load_config(CONFIG_FILE)
    global_webhook = DISCORD_WEBHOOK_URL
    targets: List[Dict[str, Any]] = config.get("targets", [])

    if not targets:
        print("[!] No targets found.")
        return

    conn = init_db(DB_FILE)
    try:
        for target in targets:
            process_target(conn, target, global_webhook)
            time.sleep(random.uniform(2.0, 5.0))
    finally:
        conn.close()
    print("[*] Scan completed.")


def main() -> None:
    run_job()


if __name__ == "__main__":
    main()
