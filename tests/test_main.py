import hashlib
import sqlite3
from typing import Dict, Any, Generator
from unittest.mock import MagicMock, patch

import pytest
from src.main import (
    calculate_hash,
    parse_element,
    init_db,
    get_stored_data,
    update_site_data,
    process_target,
    is_safe_url,
)


def test_is_safe_url() -> None:
    # Public URLs should be safe
    assert is_safe_url("https://google.com") is True
    assert is_safe_url("http://example.com") is True

    # Internal / Localhost should be unsafe
    assert is_safe_url("http://localhost") is False
    assert is_safe_url("http://127.0.0.1") is False
    assert is_safe_url("http://192.168.1.1") is False
    assert is_safe_url("http://10.0.0.1") is False
    assert is_safe_url("http://0.0.0.0") is False

    # Cloud metadata endpoints should be unsafe
    assert is_safe_url("http://169.254.169.254") is False

    # Invalid URLs should be handled safely
    assert is_safe_url("not_a_url") is False


# 1. Hash Calculation Test
def test_calculate_hash() -> None:
    data = "test data"
    expected_hash = hashlib.sha256(data.encode("utf-8")).hexdigest()
    assert calculate_hash(data) == expected_hash


# 2. HTML Parsing Test
def test_parse_element() -> None:
    html = "<html><body><h1 id='title'>Hello World</h1></body></html>"
    selector = "h1#title"
    assert parse_element(html, selector) == "Hello World"
    assert parse_element(html, "div.none") is None


# 3. Database Interaction Test
@pytest.fixture
def db_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = init_db(":memory:")
    yield conn
    conn.close()


def test_db_operations(db_conn: sqlite3.Connection) -> None:
    url = "https://example.com"
    test_hash = "abc123hash"
    test_content = "Old Content"

    # Should be None initially
    assert get_stored_data(db_conn.cursor(), url) is None

    # Store data
    update_site_data(db_conn, url, test_hash, test_content)
    result = get_stored_data(db_conn.cursor(), url)
    assert result[:2] == (test_hash, test_content)
    assert len(result) == 3

    # Update data
    new_hash = "xyz789hash"
    new_content = "New Content"
    update_site_data(db_conn, url, new_hash, new_content)
    result = get_stored_data(db_conn.cursor(), url)
    assert result[:2] == (new_hash, new_content)


# 4. Full Process Flow Test
@patch("src.main.get_html")
@patch("src.main.send_discord_notification")
def test_process_target_flow(
    mock_notify: MagicMock, mock_get_html: MagicMock, db_conn: sqlite3.Connection
) -> None:
    target: Dict[str, Any] = {
        "name": "Test Site",
        "url": "https://test.com",
        "selector": "h1",
        "interval_hours": 0,
    }
    global_webhook = "https://webhook.com"

    # First execution: Save initial data
    mock_get_html.return_value = "<html><h1>Initial Content</h1></html>"
    process_target(db_conn, target, global_webhook)

    stored = get_stored_data(db_conn.cursor(), target["url"])
    assert stored is not None
    assert stored[1] == "Initial Content"
    mock_notify.assert_not_called()

    # Second execution: Change detected
    mock_get_html.return_value = "<html><h1>Changed Content</h1></html>"
    process_target(db_conn, target, global_webhook)

    stored = get_stored_data(db_conn.cursor(), target["url"])
    assert stored[1] == "Changed Content"
    mock_notify.assert_called_once()

    # Check if notification message contains both old and new content
    args, _ = mock_notify.call_args
    message = args[1]
    assert "Initial Content" in message
    assert "Changed Content" in message


@patch("src.main.get_html")
def test_process_target_verify_ssl(
    mock_get_html: MagicMock, db_conn: sqlite3.Connection
) -> None:
    target: Dict[str, Any] = {
        "name": "Secure Site",
        "url": "https://secure.com",
        "selector": "h1",
        "interval_hours": 0,
        "verify_ssl": False,
    }
    mock_get_html.return_value = "<html><h1>Content</h1></html>"

    process_target(db_conn, target, None)

    # Ensure get_html was called with verify=False
    mock_get_html.assert_called_with("https://secure.com", verify=False)
