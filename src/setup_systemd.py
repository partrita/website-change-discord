import argparse
import os
import shutil
import subprocess
from pathlib import Path

from src.config import (
    BASE_DIR,
    CONFIG_FILE,
    SYSTEMD_TIMER_ON_CALENDAR,
)


def generate_unit_files(
    project_dir: str,
    config_file: str,
    timer_schedule: str,
    uv_cmd: str,
) -> dict[str, str]:
    """Generate the contents of systemd unit files based on configuration."""
    service_content = f"""[Unit]
Description=Website Change Notification Service
After=network.target

[Service]
Type=oneshot
WorkingDirectory={project_dir}
Environment="PATH=%h/.local/bin:%h/.cargo/bin:/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart={uv_cmd} run monitor

[Install]
WantedBy=default.target
"""

    timer_content = f"""[Unit]
Description=Run Website Change Notification Service ({timer_schedule})
PartOf=website-change.service

[Timer]
# Execution schedule configured via .env
OnCalendar={timer_schedule}
# Ensure it runs even if it missed its last scheduled time
Persistent=true

[Install]
WantedBy=timers.target
"""

    path_content = f"""[Unit]
Description=Watch config.yaml for changes
ConditionPathExists={config_file}

[Path]
PathModified={config_file}
Unit=website-change.service

[Install]
WantedBy=default.target
"""

    return {
        "website-change.service": service_content,
        "website-change.timer": timer_content,
        "website-change.path": path_content,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Configure and install systemd user units for website-change-discord using .env settings."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated systemd unit files without writing them to disk.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path.home() / ".config" / "systemd" / "user"),
        help="Directory to install the unit files (default: ~/.config/systemd/user).",
    )
    parser.add_argument(
        "--enable",
        action="store_true",
        help="Automatically enable and start website-change.timer and website-change.path.",
    )
    parser.add_argument(
        "--uv-path",
        default=None,
        help="Custom path to uv executable (default: auto-detected from environment).",
    )

    args = parser.parse_args()

    project_dir = str(BASE_DIR)
    config_file = str(CONFIG_FILE)
    timer_schedule = SYSTEMD_TIMER_ON_CALENDAR

    # Detect uv executable
    if args.uv_path:
        uv_cmd = args.uv_path
    else:
        detected_uv = shutil.which("uv")
        uv_cmd = detected_uv if detected_uv else "/usr/bin/env uv"

    units = generate_unit_files(
        project_dir=project_dir,
        config_file=config_file,
        timer_schedule=timer_schedule,
        uv_cmd=uv_cmd,
    )

    if args.dry_run:
        print("=== Systemd User Units Preview (dry-run) ===")
        print(f"Project Directory : {project_dir}")
        print(f"Config File Path  : {config_file}")
        print(f"Timer Schedule    : {timer_schedule}")
        print(f"UV Executable     : {uv_cmd}\n")
        for filename, content in units.items():
            print(f"--- {filename} ---")
            print(content)
        return

    dest_dir = Path(os.path.expanduser(args.output_dir)).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Installing systemd user units to: {dest_dir}")
    print(f"    - WorkingDirectory : {project_dir}")
    print(f"    - Config Path      : {config_file}")
    print(f"    - Timer OnCalendar : {timer_schedule}")
    print(f"    - UV Command       : {uv_cmd}")

    for filename, content in units.items():
        unit_path = dest_dir / filename
        unit_path.write_text(content, encoding="utf-8")
        print(f"[+] Written: {unit_path}")

    # Reload daemon if systemctl is available
    if shutil.which("systemctl"):
        print("[*] Running 'systemctl --user daemon-reload'...")
        res = subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        if res.returncode == 0:
            print("[+] Daemon reloaded successfully.")
        else:
            print("[!] Warning: systemctl --user daemon-reload returned non-zero exit code.")

        if args.enable:
            print("[*] Enabling and starting website-change.timer and website-change.path...")
            subprocess.run(
                ["systemctl", "--user", "enable", "--now", "website-change.timer", "website-change.path"],
                check=False,
            )
            print("[+] Units enabled and started.")
        else:
            print("\nTo enable and start the units, run:")
            print("  systemctl --user enable --now website-change.timer")
            print("  systemctl --user enable --now website-change.path")
    else:
        print("[!] Note: systemctl not found in PATH. Skipping daemon reload.")


if __name__ == "__main__":
    main()
