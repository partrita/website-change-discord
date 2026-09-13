from pathlib import Path

from src.config import resolve_path
from src.setup_systemd import generate_unit_files


def test_resolve_path():
    root = Path("/tmp/test_project")
    # Relative path should resolve relative to root
    assert resolve_path("test.yaml", root_dir=root) == "/tmp/test_project/test.yaml"
    assert resolve_path("sub/test.db", root_dir=root) == "/tmp/test_project/sub/test.db"

    # Absolute path should remain unchanged
    assert resolve_path("/var/log/test.log", root_dir=root) == "/var/log/test.log"


def test_generate_unit_files():
    units = generate_unit_files(
        project_dir="/opt/website-change",
        config_file="/opt/website-change/config.yaml",
        timer_schedule="*:0/30",
        uv_cmd="/usr/local/bin/uv",
    )

    assert "website-change.service" in units
    assert "website-change.timer" in units
    assert "website-change.path" in units

    service = units["website-change.service"]
    assert "WorkingDirectory=/opt/website-change" in service
    assert "ExecStart=/usr/local/bin/uv run monitor" in service

    timer = units["website-change.timer"]
    assert "OnCalendar=*:0/30" in timer

    path = units["website-change.path"]
    assert "ConditionPathExists=/opt/website-change/config.yaml" in path
    assert "PathModified=/opt/website-change/config.yaml" in path
