## 2025-05-18 - Prevent Discord Mention Abuse

**Vulnerability:** The application was scraping external websites and directly passing the scraped content into a Discord webhook message without restricting Discord mentions (e.g., `@everyone`, `@here`, `<@&role_id>`). This allowed an attacker who controls the target website to trigger mass pings or exploit the webhook for spam.

**Learning:** When sending text from an untrusted source (like a scraped website) directly to a Discord webhook, Discord will parse and trigger any mentions present in the text unless explicitly told not to. This is a form of output encoding/sanitization failure specific to third-party integrations.

**Prevention:** Always include `"allowed_mentions": {"parse": []}` in the JSON payload sent to Discord webhooks when the content incorporates untrusted external data. This prevents Discord from parsing and executing any mentions contained within the message.
