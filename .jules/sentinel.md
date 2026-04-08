## 2025-02-14 - Prevent SSRF in Discord Webhooks
**Vulnerability:** The application blindly accepted any URL as a Discord webhook in the configuration, allowing potential SSRF attacks where the server could be tricked into making POST requests to internal endpoints.
**Learning:** Even when reading from local configuration files, external URLs used in network requests must be strictly validated against an allowlist of trusted domains to prevent SSRF if the configuration is tampered with or misconfigured.
**Prevention:** Always use an allowlist approach for any URL that the server will fetch or post data to.
