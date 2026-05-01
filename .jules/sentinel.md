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

## 2024-04-13 - SSRF Bypass via 0.0.0.0
**Vulnerability:** The application was vulnerable to Server-Side Request Forgery (SSRF) bypass because it allowed requests to `0.0.0.0`, which many operating systems route to localhost.
**Learning:** Python's `ipaddress` module properties like `is_private` and `is_loopback` do NOT catch `0.0.0.0` (which is `is_unspecified`) or other reserved IPs.
**Prevention:** Always check `ip.is_unspecified` and `ip.is_reserved` alongside other checks when implementing an SSRF blocklist with `ipaddress`.

## 2026-04-19 - [CRITICAL] Prevent SSRF DNS Rebinding (TOCTOU)
**Vulnerability:** Even though the application previously validated URLs to prevent SSRF, it was still vulnerable to DNS Rebinding (Time-of-Check to Time-of-Use) attacks. The validation resolved the IP for safety (`is_safe_url`), but `requests.get()` independently resolved the IP again. An attacker could respond with a safe IP first, and then an internal IP (like `127.0.0.1`) on the second resolution.
**Learning:** URL validation is useless if the HTTP client re-resolves the domain name. The IP must be validated exactly at the moment of connection establishment to prevent TOCTOU vulnerabilities.
**Prevention:** Use a custom `urllib3` connection adapter (`requests.adapters.HTTPAdapter`) to intercept socket creation. Resolve the domain, validate the IP immediately, and pass that exact validated IP directly into `urllib3.util.connection.create_connection`. Also, ensure that IPv4-mapped IPv6 addresses are properly unwrapped (`ip.ipv4_mapped`) before validation to avoid `ipaddress` module bypasses.

## 2025-02-24 - [CRITICAL] Fix SSRF bypass via IPv4-mapped IPv6
**Vulnerability:** The application's `is_safe_url` function failed to evaluate the underlying IPv4 address for IPv4-mapped IPv6 addresses (e.g., `::ffff:127.0.0.1`). This allowed attackers to bypass SSRF protections and access internal networks or loopback addresses.
**Learning:** Python's `ipaddress` module requires explicitly unwrapping IPv4-mapped IPv6 addresses using `getattr(ip, "ipv4_mapped", None)` before applying checks like `is_private` or `is_loopback`.
**Prevention:** Always check if an IP address is an IPv4-mapped IPv6 address and extract the underlying IPv4 address before validating it against blocklists in SSRF protections.

## 2025-02-28 - [CRITICAL] Prevent SSRF Bypass in Discord Webhooks via requests.post
**Vulnerability:** The `send_discord_notification` function in `src/main.py` validated the webhook URL scheme and prefix using a naive string `startswith` check, and then used the default `requests.post()` to make the request. This bypassed the `SafeSession` and `SafeAdapter` used in the rest of the app, making the webhook request vulnerable to DNS rebinding or redirects to internal IPs if the URL was somehow bypassed or if `discord.com` unexpectedly redirected.
**Learning:** Default `requests` methods (`requests.get`, `requests.post`) must never be used when an application provides a custom `SafeSession` class to prevent SSRF and DNS rebinding. Any URL processing that might issue HTTP requests must be done through the validated session.
**Prevention:** Always use the project's custom `SafeSession` as a context manager (with `SafeAdapter` mounted) for all outbound HTTP requests to prevent SSRF.

## 2026-04-25 - [CRITICAL] Prevent SSRF Bypass via Carrier-Grade NAT (CGNAT) and other non-global IP ranges
**Vulnerability:** The application used `ipaddress` to block unsafe IP addresses by explicitly checking `is_private`, `is_loopback`, `is_link_local`, `is_multicast`, `is_unspecified`, and `is_reserved`. However, it missed explicitly checking if the IP was not globally routable using `not ip.is_global`. This allowed certain non-routable IP ranges like Carrier-Grade NAT (CGNAT, e.g., `100.64.0.0/10`) to bypass the SSRF checks and hit internal/provider infrastructure.
**Learning:** Python's `ipaddress` module's explicit checks for private/reserved are not exhaustive. Some IP blocks are functionally private or reserved but do not return `True` for `is_private` or `is_reserved`. `ip.is_global` covers the intent of "is this IP safe to route to the public internet".
**Prevention:** Always include `not ip.is_global` in the list of explicit blocked IP properties when using the `ipaddress` module to prevent SSRF vulnerabilities to ensure no non-publicly routable IP ranges are bypassed.

## 2026-04-29 - Fix SSRF IPv6 URL Parsing
**Vulnerability:** The application was rejecting valid external IPv6 URLs formatted with brackets (e.g., `http://[2606:4700:4700::1111]/`) because `urllib3.util.parse_url` retains the brackets in the `hostname` attribute. Passing a bracketed IPv6 address to `socket.getaddrinfo` throws a `socket.gaierror` (Name or service not known), leading `is_safe_url` to falsely return `False` and incorrectly blocking valid outbound requests or webhooks.
**Learning:** Python's `socket.getaddrinfo` expects raw IPv6 addresses without the enclosing brackets `[]`, which are mandated by RFC 3986 for URLs but aren't valid hostnames for DNS/socket resolution.
**Prevention:** When resolving parsed URL hostnames with `socket.getaddrinfo` for SSRF protection, always explicitly strip brackets `[]` (e.g., `hostname.strip('[]')`) to ensure correct resolution of IPv6 addresses.
