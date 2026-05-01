import ipaddress
import os
import socket
import yaml
from urllib3.util import parse_url

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from src.ssrf_adapter import SafeAdapter

CONFIG_FILE = "config.yaml"
ua = UserAgent()


def is_safe_url(url: str) -> bool:
    """Check if a URL is safe to fetch (prevents SSRF)."""
    try:
        parsed = parse_url(url)
        hostname = parsed.host
        if not hostname:
            return False

        hostname = hostname.strip("[]")
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
                or not ip.is_global
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


def get_html(url, verify=True):
    """Fetch HTML content from a URL with random headers."""
    if not is_safe_url(url):
        print(
            f"[!] Security Error: Blocked attempt to fetch unsafe or internal URL: {url}"
        )
        return None, verify

    headers = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/",
    }
    try:
        print(f"[*] Fetching {url}...")
        with SafeSession() as session:
            session.mount("http://", SafeAdapter())
            session.mount("https://", SafeAdapter())

            if not verify:
                import urllib3

                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = session.get(
                url, headers=headers, timeout=15, stream=True, verify=verify
            )
            response.raise_for_status()

        MAX_SIZE = 5 * 1024 * 1024
        content = b""
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > MAX_SIZE:
                print(f"[!] Error: Response from {url} exceeded 5MB limit.")
                response.close()
                return None, verify

        return content.decode(response.encoding or "utf-8", errors="replace"), verify
    except requests.exceptions.SSLError as e:
        print(f"[!] SSL Certificate Error: {e}")
        if verify:
            choice = (
                input(
                    "[?] SSL 인증서 확인에 실패했습니다. 인증서 검증 없이 계속하시겠습니까? (y/n): "
                )
                .strip()
                .lower()
            )
            if choice == "y":
                return get_html(url, verify=False)
        return None, verify
    except Exception as e:
        print(f"[!] Error fetching {url}: {e}")
        return None, verify


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

    html, final_verify = get_html(url)
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
            if not final_verify:
                new_target["verify_ssl"] = False
            config["targets"].append(new_target)
            save_config(config)
            print(f"[+] Successfully added '{name}' to {CONFIG_FILE}!")
        else:
            print("[*] Cancelled.")


if __name__ == "__main__":
    main()
