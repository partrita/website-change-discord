## 2025-02-14 - Prevent SSRF in Discord Webhooks
**Vulnerability:** The application blindly accepted any URL as a Discord webhook in the configuration, allowing potential SSRF attacks where the server could be tricked into making POST requests to internal endpoints.
**Learning:** Even when reading from local configuration files, external URLs used in network requests must be strictly validated against an allowlist of trusted domains to prevent SSRF if the configuration is tampered with or misconfigured.
**Prevention:** Always use an allowlist approach for any URL that the server will fetch or post data to.

## 2026-04-06 - [CRITICAL] Prevent SSRF in Website Scraper
**Vulnerability:** The `get_html` function in `src/main.py` and `src/add_site.py` fetched user-provided URLs using `requests.get()` without validating the underlying IP addresses. This allowed Server-Side Request Forgery (SSRF), where an attacker could provide URLs pointing to internal networks, loopback addresses (`127.0.0.1`), or cloud metadata endpoints (`169.254.169.254`).
**Learning:** URL validation based on scheme (e.g., checking for `http://` or `https://`) is insufficient to prevent SSRF. DNS resolution must be performed, and the resulting IP addresses must be checked against safe ranges before initiating the HTTP request.
**Prevention:** Implement a robust URL validation function (`is_safe_url`) that uses `urllib.parse.urlparse` to extract the hostname, `socket.getaddrinfo` to resolve all associated IP addresses, and the `ipaddress` module to ensure none of the resolved IPs are private, loopback, link-local, or multicast.

## 2023-10-25 - Prevent SSRF via Redirects
**Vulnerability:** The application verified that initial URLs were safe, but allowed `requests.get` to automatically follow redirects to unsafe internal IPs (like 127.0.0.1 or 169.254.169.254), bypassing the SSRF protection.
**Learning:** SSRF prevention requires checking redirects as well as the initial URL. `requests` follows redirects by default. Overriding `requests.Session().rebuild_auth` is a reliable way to hook into redirect URL resolution before requests are sent.
**Prevention:** Use a custom `requests.Session` subclass that overrides `rebuild_auth` to validate URLs during redirection, instead of just checking the initial URL and using `requests.get()`.

## 2025-02-14 - Prevent SSRF bypass through parser confusion
**Vulnerability:** URL parsing functions like `urllib.parse.urlparse` and the one used internally by the `requests` library might interpret URLs differently (parser confusion). This could allow an attacker to craft a URL that bypasses the SSRF checks using `urlparse` while successfully hitting internal endpoints via `requests`.
**Learning:** We need to use `urllib3.util.parse_url` when dealing with `requests` validation because `urllib3` is used by `requests` underneath. This ensures consistency between validation and network requests, avoiding parser confusion.
**Prevention:** Use `urllib3.util.parse_url` to extract the host (`parsed.host`) when validating URLs before making requests with the `requests` module, rather than using `urllib.parse.urlparse`.
