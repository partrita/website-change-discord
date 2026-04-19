# GEMINI.md

## Project Overview
**Website Change Discord Watcher** is a Python-based automation tool designed to monitor specific sections of websites and send notifications to a Discord webhook when changes are detected. It uses CSS selectors for precise targeting and maintains state using an SQLite database to ensure only meaningful updates are reported.

### Tech Stack
- **Language:** Python 3.12+
- **Package Manager:** [uv](https://github.com/astral-sh/uv)
- **Web Scraping:** BeautifulSoup4, Requests
- **Configuration:** YAML (PyYAML), Environment Variables (python-dotenv)
- **Persistence:** SQLite3 (hashes and last-seen content)
- **Automation:** systemd (Service, Timer, and Path units for Linux servers)
- **Utilities:** `fake-useragent` (anti-bot), `watchdog` (config monitoring), `schedule` (daemon mode)

## Architecture
- `src/main.py`: The core engine. It fetches HTML, extracts content via CSS selectors, computes SHA256 hashes, and compares them against stored values in `hashes.db`.
- `src/add_site.py`: An interactive CLI helper to test selectors and add new sites to `config.yaml`.
- `config.yaml`: Central registry for monitored targets.
- `systemd/`: Contains unit files for robust deployment on Linux, enabling periodic checks (`.timer`) and immediate execution upon configuration changes (`.path`).

## Building and Running

### Prerequisites
- Install `uv`: `curl -LsSf https://astral-sh.uv.io/install.sh | sh`
- Set up environment: `cp .env.bak .env` and fill in `DISCORD_WEBHOOK_URL`.

### Key Commands
- **Initialize Environment:** `uv sync`
- **Add a Site:** `uv run add_site` (interactive CLI)
- **Run Manual Scan:** `uv run monitor`
- **Run in Daemon Mode:** `uv run monitor --daemon`
- **Run Tests:** `pytest`

### Deployment (systemd)
The project is optimized for `systemd --user` execution:
1. Copy units: `cp systemd/* ~/.config/systemd/user/`
2. Reload: `systemctl --user daemon-reload`
3. Enable Timer: `systemctl --user enable --now website-change.timer`
4. (Optional) Enable Path Watcher: `systemctl --user enable --now website-change.path`

## Development Conventions

### Coding Style
- **Formatting & Linting:** Uses `ruff` (inferred from `.ruff_cache`).
- **Type Safety:** Type hints are used throughout the codebase (e.g., `Optional`, `Dict`, `List`).
- **Security:** 
    - Always use `is_safe_url()` before fetching to prevent SSRF.
    - Webhook URLs are redacted in logs.
    - User-Agents and Referers are randomized to avoid bot detection.

### Testing
- Tests are located in the `tests/` directory.
- Run tests using `pytest`.
- Mocking is expected for network requests to ensure tests are deterministic.

### Data Management
- **Database:** `hashes.db` stores site hashes and `last_content` (for change summaries).
- **Logs:** `app.log` (rotating) and systemd journal.
