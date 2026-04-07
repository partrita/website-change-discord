## 2025-05-18 - Prevent Discord Mention Abuse

**Vulnerability:** The application was scraping external websites and directly passing the scraped content into a Discord webhook message without restricting Discord mentions (e.g., `@everyone`, `@here`, `<@&role_id>`). This allowed an attacker who controls the target website to trigger mass pings or exploit the webhook for spam.

**Learning:** When sending text from an untrusted source (like a scraped website) directly to a Discord webhook, Discord will parse and trigger any mentions present in the text unless explicitly told not to. This is a form of output encoding/sanitization failure specific to third-party integrations.

**Prevention:** Always include `"allowed_mentions": {"parse": []}` in the JSON payload sent to Discord webhooks when the content incorporates untrusted external data. This prevents Discord from parsing and executing any mentions contained within the message.
## 2026-04-06 - Logging Secret Webhook URL
**Vulnerability:** Discord Webhook URL (which contains a secret token) can be leaked into `app.log` through exception messages if a request fails.
**Learning:** `requests.exceptions` often include the full URL in their string representation. Direct logging of the exception object `f"{e}"` or `str(e)` is unsafe when the URL is a secret.
**Prevention:** Catch specific exceptions and log generic messages without the exception object, or carefully sanitize the exception message before logging. Also, ensure database files are correctly ignored in `.gitignore`.
## 2026-04-06 - Prevent DoS via Large HTTP Responses
**Vulnerability:** The application used `requests.get()` without `stream=True` and without limits, making it susceptible to DoS attacks via memory exhaustion if a target URL returned an infinitely large stream or a massive file.
**Learning:** `requests.get()` pulls the entire response body into memory by default. When scraping arbitrary or untrusted URLs, this behavior is a security risk.
**Prevention:** Always use `stream=True` and manually read the response in chunks up to a safe maximum size limit. Ensure the socket is explicitly closed (`response.close()`) if the limit is exceeded to prevent file descriptor leaks.
