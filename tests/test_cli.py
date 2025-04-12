"""
Tests for the CLI module
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from src.slacraper.cli import main
from src.slacraper.core import Slacraper


@pytest.fixture
def cli_runner():
    """CLI runner fixture"""
    return CliRunner()


@pytest.fixture
def sample_data():
    """Sample test data"""
    channel = "general"
    token = "xoxb-test-token"

    # Sample messages
    sample_messages = [
        {
            "channel": channel,
            "user": "U12345678",
            "user_name": "testuser",
            "text": "Hello, world!",
            "timestamp": "2023-01-01T12:00:00",
            "reactions": [
                {
                    "name": "thumbsup",
                    "count": 2,
                    "users": ["U87654321", "U11223344"],
                }
            ],
        },
        {
            "channel": channel,
            "user": "U87654321",
            "user_name": "anotheruser",
            "text": "Testing slacraper",
            "timestamp": "2023-01-01T12:05:00",
        },
    ]

    return {"channel": channel, "token": token, "sample_messages": sample_messages}


@patch.object(Slacraper, "get_messages")
@patch.object(Slacraper, "__init__")
def test_basic_command(mock_init, mock_get_messages, cli_runner, sample_data):
    """Test basic command with required options"""
    # Setup mocks
    mock_init.return_value = None
    mock_get_messages.return_value = sample_data["sample_messages"]

    # Run command
    result = cli_runner.invoke(main, ["--channel", sample_data["channel"]])

    # Assertions
    assert result.exit_code == 0
    mock_init.assert_called_once_with(channel=sample_data["channel"], token=None)
    mock_get_messages.assert_called_once()
    call_args = mock_get_messages.call_args[1]
    assert call_args["time_range"] == "1 hour"
    assert call_args["user"] is None
    assert call_args["text_contains"] is None
    assert call_args["reaction"] is None
    assert call_args["include_url"] is False
    assert "hours" not in call_args  # hours should not be passed anymore

    # Check output
    output = json.loads(result.output)
    assert len(output) == 2
    assert output[0]["user_name"] == "testuser"
    assert output[1]["text"] == "Testing slacraper"


@patch.object(Slacraper, "get_messages")
@patch.object(Slacraper, "__init__")
def test_command_with_token(mock_init, mock_get_messages, cli_runner, sample_data):
    """Test command with token option"""
    # Setup mocks
    mock_init.return_value = None
    mock_get_messages.return_value = sample_data["sample_messages"]

    # Run command
    result = cli_runner.invoke(
        main, ["--channel", sample_data["channel"], "--token", sample_data["token"]]
    )

    # Assertions
    assert result.exit_code == 0
    mock_init.assert_called_once_with(
        channel=sample_data["channel"], token=sample_data["token"]
    )


# --hours オプションのテストは削除されました


@patch.object(Slacraper, "get_messages")
@patch.object(Slacraper, "__init__")
def test_command_with_time_range(mock_init, mock_get_messages, cli_runner, sample_data):
    """Test command with time-range option"""
    # Setup mocks
    mock_init.return_value = None
    mock_get_messages.return_value = sample_data["sample_messages"]

    # Run command
    result = cli_runner.invoke(
        main, ["--channel", sample_data["channel"], "--time-range", "1 week"]
    )

    # Assertions
    assert result.exit_code == 0
    mock_get_messages.assert_called_once()
    call_args = mock_get_messages.call_args[1]
    assert call_args["time_range"] == "1 week"
    assert "hours" not in call_args  # hours should not be passed anymore


# --hours と --time-range の両方を指定するテストは削除されました


@patch.object(Slacraper, "get_messages")
@patch.object(Slacraper, "__init__")
def test_command_with_filters(mock_init, mock_get_messages, cli_runner, sample_data):
    """Test command with filter options"""
    # Setup mocks
    mock_init.return_value = None
    mock_get_messages.return_value = [
        sample_data["sample_messages"][0]
    ]  # Just one message after filtering

    # Run command
    result = cli_runner.invoke(
        main,
        [
            "--channel",
            sample_data["channel"],
            "--user",
            "testuser",
            "--text-contains",
            "Hello",
            "--reaction",
            "thumbsup",
        ],
    )

    # Assertions
    assert result.exit_code == 0
    mock_get_messages.assert_called_once()
    call_args = mock_get_messages.call_args[1]
    assert call_args["time_range"] == "1 hour"
    assert call_args["user"] == "testuser"
    assert call_args["text_contains"] == "Hello"
    assert call_args["reaction"] == "thumbsup"
    assert call_args["include_url"] is False
    assert "hours" not in call_args  # hours should not be passed anymore

    # Check output
    output = json.loads(result.output)
    assert len(output) == 1
    assert output[0]["user_name"] == "testuser"


@patch.object(Slacraper, "get_messages")
@patch.object(Slacraper, "__init__")
def test_command_with_url(mock_init, mock_get_messages, cli_runner, sample_data):
    """Test command with include-url option"""
    # Setup mocks
    mock_init.return_value = None
    # Add URL to sample messages
    messages_with_url = sample_data["sample_messages"].copy()
    for msg in messages_with_url:
        msg["url"] = (
            f"https://workspace.slack.com/archives/C12345678/p{msg['timestamp'].replace(':', '').replace('-', '')}"
        )
    mock_get_messages.return_value = messages_with_url

    # Run command
    result = cli_runner.invoke(
        main, ["--channel", sample_data["channel"], "--include-url"]
    )

    # Assertions
    assert result.exit_code == 0
    mock_get_messages.assert_called_once()
    call_args = mock_get_messages.call_args[1]
    assert call_args["time_range"] == "1 hour"
    assert call_args["include_url"] is True
    assert "hours" not in call_args  # hours should not be passed anymore

    # Check output
    output = json.loads(result.output)
    assert len(output) == 2
    assert "url" in output[0]


@patch.object(Slacraper, "__init__")
def test_missing_channel(mock_init, cli_runner):
    """Test command without required channel option"""
    # Run command
    result = cli_runner.invoke(main, [])

    # Assertions
    assert result.exit_code != 0
    assert "Missing option '--channel'" in result.output


@patch.object(Slacraper, "__init__")
def test_initialization_error(mock_init, cli_runner, sample_data):
    """Test error handling when initialization fails"""
    # Setup mock to raise an error
    mock_init.side_effect = ValueError("Invalid token")

    # Run command
    result = cli_runner.invoke(main, ["--channel", sample_data["channel"]])

    # Assertions
    assert result.exit_code == 1
    assert "Error: Invalid token" in result.output
