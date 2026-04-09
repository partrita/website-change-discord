## 2025-02-14 - Prevent SSRF in Discord Webhooks
**Vulnerability:** The application blindly accepted any URL as a Discord webhook in the configuration, allowing potential SSRF attacks where the server could be tricked into making POST requests to internal endpoints.
**Learning:** Even when reading from local configuration files, external URLs used in network requests must be strictly validated against an allowlist of trusted domains to prevent SSRF if the configuration is tampered with or misconfigured.
**Prevention:** Always use an allowlist approach for any URL that the server will fetch or post data to.

## 2026-04-06 - [CRITICAL] Prevent SSRF in Website Scraper
**Vulnerability:** The `get_html` function in `src/main.py` and `src/add_site.py` fetched user-provided URLs using `requests.get()` without validating the underlying IP addresses. This allowed Server-Side Request Forgery (SSRF), where an attacker could provide URLs pointing to internal networks, loopback addresses (`127.0.0.1`), or cloud metadata endpoints (`169.254.169.254`).
**Learning:** URL validation based on scheme (e.g., checking for `http://` or `https://`) is insufficient to prevent SSRF. DNS resolution must be performed, and the resulting IP addresses must be checked against safe ranges before initiating the HTTP request.
**Prevention:** Implement a robust URL validation function (`is_safe_url`) that uses `urllib.parse.urlparse` to extract the hostname, `socket.getaddrinfo` to resolve all associated IP addresses, and the `ipaddress` module to ensure none of the resolved IPs are private, loopback, link-local, or multicast.
