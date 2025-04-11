"""
Tests for the core module
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from src.slacraper.core import SlackScraper


@pytest.fixture
def mock_env():
    """Mock environment variable"""
    with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}):
        yield


@pytest.fixture
def sample_data():
    """Sample test data"""
    return {
        "channel": "general",
        "token": "xoxb-custom-token",
        "channel_id": "C12345678",
        "sample_messages": {
            "messages": [
                {
                    "type": "message",
                    "user": "U12345678",
                    "text": "Hello, world!",
                    "ts": "1609459200.000100",
                    "reactions": [
                        {
                            "name": "thumbsup",
                            "count": 2,
                            "users": ["U87654321", "U11223344"],
                        }
                    ],
                },
                {
                    "type": "message",
                    "user": "U87654321",
                    "text": "Testing slacraper",
                    "ts": "1609459300.000200",
                },
            ]
        },
        "sample_user_info": {"user": {"id": "U12345678", "name": "testuser"}},
        "sample_team_info": {
            "team": {"id": "T12345678", "name": "Test Team", "domain": "test-team"}
        },
    }


@pytest.mark.usefixtures("mock_env")
@patch("src.slacraper.core.WebClient")
def test_init_with_token_param(mock_client, sample_data):
    """Test initialization with token parameter"""
    scraper = SlackScraper(channel=sample_data["channel"], token=sample_data["token"])

    assert scraper.channel == sample_data["channel"]
    assert scraper.token == sample_data["token"]
    mock_client.assert_called_once_with(token=sample_data["token"])


@pytest.mark.usefixtures("mock_env")
@patch("src.slacraper.core.WebClient")
def test_init_with_env_token(mock_client, sample_data):
    """Test initialization with environment variable token"""
    scraper = SlackScraper(channel=sample_data["channel"])

    assert scraper.channel == sample_data["channel"]
    assert scraper.token == "xoxb-test-token"
    mock_client.assert_called_once_with(token="xoxb-test-token")


@patch("src.slacraper.core.WebClient")
def test_init_without_token(mock_client, sample_data):
    """Test initialization without token"""
    # No environment variable, no token parameter
    with pytest.raises(ValueError) as excinfo:
        SlackScraper(channel=sample_data["channel"])

    assert "Slack Bot Token is required" in str(excinfo.value)


@pytest.mark.usefixtures("mock_env")
@patch("src.slacraper.core.WebClient")
def test_channel_id_public(mock_client, sample_data):
    """Test getting channel ID from public channel"""
    # Setup mock
    mock_instance = mock_client.return_value
    mock_instance.conversations_list.return_value = {
        "channels": [
            {"id": "C11111111", "name": "random"},
            {"id": sample_data["channel_id"], "name": sample_data["channel"]},
            {"id": "C33333333", "name": "announcements"},
        ]
    }

    # Create scraper and get channel ID
    scraper = SlackScraper(channel=sample_data["channel"])
    result = scraper.channel_id

    # Assertions
    assert result == sample_data["channel_id"]
    mock_instance.conversations_list.assert_called_once()


@pytest.mark.usefixtures("mock_env")
@patch("src.slacraper.core.WebClient")
def test_channel_id_private(mock_client, sample_data):
    """Test getting channel ID from private channel"""
    # Setup mock
    mock_instance = mock_client.return_value
    mock_instance.conversations_list.side_effect = [
        # First call returns public channels without our target
        {
            "channels": [
                {"id": "C11111111", "name": "random"},
                {"id": "C33333333", "name": "announcements"},
            ]
        },
        # Second call returns private channels with our target
        {
            "channels": [
                {"id": sample_data["channel_id"], "name": sample_data["channel"]}
            ]
        },
    ]

    # Create scraper and get channel ID
    scraper = SlackScraper(channel=sample_data["channel"])
    result = scraper.channel_id

    # Assertions
    assert result == sample_data["channel_id"]
    mock_instance.conversations_list.assert_called_with(types="private_channel")


@pytest.mark.usefixtures("mock_env")
@patch("src.slacraper.core.WebClient")
def test_channel_id_not_found(mock_client, sample_data):
    """Test getting channel ID when channel not found"""
    # Setup mock
    mock_instance = mock_client.return_value
    mock_instance.conversations_list.side_effect = [
        # First call returns public channels without our target
        {
            "channels": [
                {"id": "C11111111", "name": "random"},
                {"id": "C33333333", "name": "announcements"},
            ]
        },
        # Second call returns private channels without our target
        {"channels": [{"id": "C44444444", "name": "private-channel"}]},
    ]

    # Create scraper and try to get channel ID
    scraper = SlackScraper(channel=sample_data["channel"])
    with pytest.raises(ValueError) as excinfo:
        _ = scraper.channel_id

    assert f"Channel '{sample_data['channel']}' not found" in str(excinfo.value)


@pytest.mark.usefixtures("mock_env")
@patch("src.slacraper.core.WebClient")
def test_get_messages_basic(mock_client, sample_data):
    """Test getting messages with basic parameters"""
    # Setup mocks
    mock_instance = mock_client.return_value
    mock_instance.conversations_list.return_value = {
        "channels": [{"id": sample_data["channel_id"], "name": sample_data["channel"]}]
    }
    mock_instance.conversations_history.return_value = sample_data["sample_messages"]
    mock_instance.users_info.side_effect = [
        {"user": {"name": "testuser"}},
        {"user": {"name": "anotheruser"}},
    ]
    mock_instance.team_info.return_value = sample_data["sample_team_info"]

    # Create scraper and get messages
    scraper = SlackScraper(channel=sample_data["channel"])
    messages = scraper.get_messages(time_range="1 hour")

    # Assertions
    assert len(messages) == 2
    assert messages[0]["channel"] == sample_data["channel"]
    assert messages[0]["user"] == "U12345678"
    assert messages[0]["user_name"] == "testuser"
    assert messages[0]["text"] == "Hello, world!"
    assert "reactions" in messages[0]
    assert messages[0]["reactions"][0]["name"] == "thumbsup"

    # Check that the timestamp was formatted correctly
    expected_dt = datetime.fromtimestamp(1609459200.000100)
    assert messages[0]["timestamp"] == expected_dt.isoformat()


@pytest.mark.usefixtures("mock_env")
@patch("src.slacraper.core.WebClient")
def test_get_messages_with_filters(mock_client, sample_data):
    """Test getting messages with filters"""
    # Setup mocks
    mock_instance = mock_client.return_value
    mock_instance.conversations_list.return_value = {
        "channels": [{"id": sample_data["channel_id"], "name": sample_data["channel"]}]
    }

    # Create scraper
    scraper = SlackScraper(channel=sample_data["channel"])

    # Test user filter
    mock_instance.conversations_history.return_value = sample_data["sample_messages"]
    mock_instance.users_info.side_effect = [
        {"user": {"name": "testuser"}},
        {"user": {"name": "anotheruser"}},
    ]
    messages = scraper.get_messages(time_range="1 hour", user="testuser")
    assert len(messages) == 1
    assert messages[0]["user_name"] == "testuser"

    # Reset mocks for next test
    mock_instance.users_info.reset_mock()
    mock_instance.users_info.side_effect = [
        {"user": {"name": "testuser"}},
        {"user": {"name": "anotheruser"}},
    ]

    # Test text filter
    messages = scraper.get_messages(time_range="1 hour", text_contains="slacraper")
    assert len(messages) == 1
    assert messages[0]["text"] == "Testing slacraper"


@pytest.mark.usefixtures("mock_env")
@patch("src.slacraper.core.WebClient")
def test_get_messages_with_url(mock_client, sample_data):
    """Test getting messages with URL included"""
    # Setup mocks
    mock_instance = mock_client.return_value
    mock_instance.conversations_list.return_value = {
        "channels": [{"id": sample_data["channel_id"], "name": sample_data["channel"]}]
    }
    mock_instance.conversations_history.return_value = sample_data["sample_messages"]
    mock_instance.users_info.side_effect = [
        {"user": {"name": "testuser"}},
        {"user": {"name": "anotheruser"}},
    ]
    mock_instance.team_info.return_value = sample_data["sample_team_info"]

    # Create scraper and get messages with URL
    scraper = SlackScraper(channel=sample_data["channel"])
    messages = scraper.get_messages(time_range="1 hour", include_url=True)

    # Assertions
    assert len(messages) == 2
    assert "url" in messages[0]
    expected_url = f"https://test-team.slack.com/archives/{sample_data['channel_id']}/p1609459200000100"
    assert messages[0]["url"] == expected_url


@pytest.mark.usefixtures("mock_env")
@patch("src.slacraper.core.WebClient")
def test_parse_time_range(mock_client, sample_data):
    """Test parsing time range"""
    scraper = SlackScraper(channel=sample_data["channel"])

    # Test hours
    assert scraper.parse_time_range("1 hour") == timedelta(hours=1)
    assert scraper.parse_time_range("2 hours") == timedelta(hours=2)
    assert scraper.parse_time_range("24 hours") == timedelta(hours=24)

    # Test days
    assert scraper.parse_time_range("1 day") == timedelta(days=1)
    assert scraper.parse_time_range("7 days") == timedelta(days=7)

    # Test weeks
    assert scraper.parse_time_range("1 week") == timedelta(weeks=1)
    assert scraper.parse_time_range("2 weeks") == timedelta(weeks=2)

    # Test months
    assert scraper.parse_time_range("1 month").months == 1
    assert scraper.parse_time_range("6 months").months == 6

    # Test years
    assert scraper.parse_time_range("1 year").years == 1

    # Test special cases
    assert scraper.parse_time_range("today") == timedelta(days=1)

    # Test numeric only
    assert scraper.parse_time_range("12") == timedelta(hours=12)

    # Test default
    assert scraper.parse_time_range("invalid") == timedelta(hours=1)
    assert scraper.parse_time_range("") == timedelta(hours=1)
