import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Repository / project base directory (defaults to repo root where pyproject.toml is)
DEFAULT_PROJECT_DIR = Path(__file__).resolve().parent.parent

# 1. Determine base directory
initial_project_dir = os.getenv("PROJECT_DIR")
BASE_DIR: Path = (
    Path(os.path.expanduser(initial_project_dir)).resolve()
    if initial_project_dir
    else DEFAULT_PROJECT_DIR
)

# 2. Load .env file
# Allow explicit ENV_FILE override, otherwise load from BASE_DIR/.env
env_file = os.getenv("ENV_FILE")
if env_file and Path(env_file).is_file():
    load_dotenv(dotenv_path=Path(env_file).resolve())
else:
    dotenv_candidate = BASE_DIR / ".env"
    if dotenv_candidate.is_file():
        load_dotenv(dotenv_path=dotenv_candidate)
    else:
        # Fallback to current working directory search
        load_dotenv()

# If PROJECT_DIR was defined inside .env, update BASE_DIR
env_project_dir = os.getenv("PROJECT_DIR")
if env_project_dir:
    BASE_DIR = Path(os.path.expanduser(env_project_dir)).resolve()


def resolve_path(path_str: str, root_dir: Path = BASE_DIR) -> str:
    """Resolve a file path. If relative, resolve against root_dir."""
    expanded = os.path.expanduser(path_str)
    p = Path(expanded)
    if not p.is_absolute():
        p = (root_dir / p).resolve()
    return str(p)


# File paths
CONFIG_FILE: str = resolve_path(os.getenv("CONFIG_FILE", "config.yaml"))
DB_FILE: str = resolve_path(os.getenv("DB_FILE", "hashes.db"))
LOG_FILE: str = resolve_path(os.getenv("LOG_FILE", "app.log"))

# Discord Webhook
DISCORD_WEBHOOK_URL: Optional[str] = os.getenv("DISCORD_WEBHOOK_URL")

# Execution Intervals & Times
DEFAULT_INTERVAL_HOURS: int = int(os.getenv("DEFAULT_INTERVAL_HOURS", "24"))

# Daemon interval (in minutes). Can also be specified as DAEMON_INTERVAL_HOURS
_daemon_min = os.getenv("DAEMON_INTERVAL_MINUTES")
if _daemon_min:
    DAEMON_INTERVAL_MINUTES: int = int(_daemon_min)
elif os.getenv("DAEMON_INTERVAL_HOURS"):
    DAEMON_INTERVAL_MINUTES = int(os.getenv("DAEMON_INTERVAL_HOURS", "1")) * 60
else:
    DAEMON_INTERVAL_MINUTES = 60

# systemd Timer schedule
SYSTEMD_TIMER_ON_CALENDAR: str = os.getenv("SYSTEMD_TIMER_ON_CALENDAR", "hourly")

# Timeouts & Logging
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "15"))
DISCORD_TIMEOUT: int = int(os.getenv("DISCORD_TIMEOUT", "10"))
LOG_MAX_BYTES: int = int(os.getenv("LOG_MAX_BYTES", str(5 * 1024 * 1024)))
LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "3"))
