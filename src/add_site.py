import yaml
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import os

CONFIG_FILE = "config.yaml"
ua = UserAgent()


def get_html(url):
    """Fetch HTML content from a URL with random headers."""
    headers = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/",
    }
    try:
        print(f"[*] Fetching {url}...")
        response = requests.get(url, headers=headers, timeout=15, stream=True)
        response.raise_for_status()

        MAX_SIZE = 5 * 1024 * 1024
        content = b""
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > MAX_SIZE:
                print(f"[!] Error: Response from {url} exceeded 5MB limit.")
                response.close()
                return None

        return content.decode(response.encoding or "utf-8", errors="replace")
    except Exception as e:
        print(f"[!] Error fetching {url}: {e}")
        return None


def parse_element(html, selector):
    """Extract text from the HTML using a CSS selector."""
    soup = BeautifulSoup(html, "html.parser")
    element = soup.select_one(selector)
    if element:
        return element.get_text(strip=True)
    return None


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"targets": []}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        try:
            return yaml.safe_load(f) or {"targets": []}
        except Exception:
            return {"targets": []}


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(
            config, f, allow_unicode=True, sort_keys=False, default_flow_style=False
        )


def main():
    print("=== Website Change Detection Helper ===")

    config = load_config()
    existing_urls = [t.get("url") for t in config.get("targets", [])]

    name = input("Enter site name (e.g., My Blog): ").strip()
    if not name:
        print("[!] Name is required.")
        return

    url = input("Enter website URL: ").strip()
    if not url.startswith("http"):
        print("[!] Invalid URL.")
        return

    if url in existing_urls:
        print(f"[!] Warning: {url} is already in the config.")
        cont = input("Do you want to continue anyway? (y/n): ").strip().lower()
        if cont != "y":
            return

    selector = input(
        "Enter CSS selector (e.g., #content, .article-title, h1): "
    ).strip()
    if not selector:
        print("[!] Selector is required.")
        return

    interval = input("Enter check interval in hours (default: 12): ").strip()
    try:
        interval_hours = int(interval) if interval else 12
    except ValueError:
        print("[!] Invalid interval, using default 12.")
        interval_hours = 12

    html = get_html(url)
    if not html:
        print("[!] Could not retrieve website content.")
        return

    result = parse_element(html, selector)

    if result is None:
        print(f"\n[!] Selector '{selector}' not found on the page.")
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string if soup.title else "No Title"
        print(f"[*] Page Title: {title}")
        print("[*] Tip: Check the selector in your browser's Inspect Tool.")
    else:
        print("\n" + "=" * 40)
        print(f"[*] Found content for selector '{selector}':")
        print("-" * 40)
        print(result[:500] + ("..." if len(result) > 500 else ""))
        print("-" * 40)
        print("=" * 40 + "\n")

        confirm = (
            input(f"Do you want to add this to {CONFIG_FILE}? (y/n): ").strip().lower()
        )
        if confirm == "y":
            new_target = {
                "name": name,
                "url": url,
                "selector": selector,
                "interval_hours": interval_hours,
            }
            config["targets"].append(new_target)
            save_config(config)
            print(f"[+] Successfully added '{name}' to {CONFIG_FILE}!")
        else:
            print("[*] Cancelled.")


if __name__ == "__main__":
    main()
