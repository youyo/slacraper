"""
Core functionality for slacraper
"""

import os
import datetime
import re
from typing import List, Dict, Any, Optional, Union, Tuple
from dateutil.relativedelta import relativedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackScraper:
    """
    Slack message scraper class
    """

    def __init__(
        self,
        channel: str,
        token: Optional[str] = None,
    ):
        """
        Initialize the SlackScraper

        Args:
            channel: Slack channel name to scrape messages from
            token: Slack Bot Token. If not provided, it will be read from SLACK_BOT_TOKEN environment variable
        """
        self.channel = channel
        self.token = token or os.environ.get("SLACK_BOT_TOKEN")

        if not self.token:
            raise ValueError(
                "Slack Bot Token is required. Either pass it as token parameter or set SLACK_BOT_TOKEN environment variable."
            )

        self.client = WebClient(token=self.token)
        self._channel_id = None

    @property
    def channel_id(self) -> str:
        """
        Get the channel ID from channel name

        Returns:
            str: Channel ID
        """
        if self._channel_id is not None:
            return self._channel_id

        try:
            # Try to find the channel in public channels
            response = self.client.conversations_list()
            for channel in response["channels"]:
                if channel["name"] == self.channel:
                    self._channel_id = channel["id"]
                    return self._channel_id

            # If not found, try to find in private channels
            response = self.client.conversations_list(types="private_channel")
            for channel in response["channels"]:
                if channel["name"] == self.channel:
                    self._channel_id = channel["id"]
                    return self._channel_id

            raise ValueError(f"Channel '{self.channel}' not found")

        except SlackApiError as e:
            raise ValueError(f"Error finding channel: {e}")

    def parse_time_range(self, time_range: str) -> datetime.timedelta:
        """
        Parse a natural language time range into a timedelta

        Args:
            time_range: Natural language time range (e.g., '1 hour', '2 days', '1 week')

        Returns:
            datetime.timedelta: The parsed time delta
        """
        # Default to 1 hour if not specified
        if not time_range:
            return datetime.timedelta(hours=1)

        # Try to parse the time range
        time_range = time_range.lower().strip()

        # Check for simple numeric hours
        if time_range.isdigit():
            return datetime.timedelta(hours=int(time_range))

        # Parse natural language time expressions
        match = re.match(r"(\d+)\s*(hour|hours|hr|hrs)", time_range)
        if match:
            return datetime.timedelta(hours=int(match.group(1)))

        match = re.match(r"(\d+)\s*(minute|minutes|min|mins)", time_range)
        if match:
            return datetime.timedelta(minutes=int(match.group(1)))

        match = re.match(r"(\d+)\s*(day|days)", time_range)
        if match:
            return datetime.timedelta(days=int(match.group(1)))

        match = re.match(r"(\d+)\s*(week|weeks|wk|wks)", time_range)
        if match:
            return datetime.timedelta(weeks=int(match.group(1)))

        match = re.match(r"(\d+)\s*(month|months)", time_range)
        if match:
            return relativedelta(months=int(match.group(1)))

        match = re.match(r"(\d+)\s*(year|years|yr|yrs)", time_range)
        if match:
            return relativedelta(years=int(match.group(1)))

        # Special cases
        if time_range in ["an hour", "one hour", "1 hour"]:
            return datetime.timedelta(hours=1)
        elif time_range in ["a day", "one day", "1 day", "today"]:
            return datetime.timedelta(days=1)
        elif time_range in ["a week", "one week", "1 week"]:
            return datetime.timedelta(weeks=1)
        elif time_range in ["a month", "one month", "1 month"]:
            return relativedelta(months=1)
        elif time_range in ["a year", "one year", "1 year"]:
            return relativedelta(years=1)

        # Default to 1 hour if we couldn't parse it
        return datetime.timedelta(hours=1)

    def get_messages(
        self,
        time_range: Union[str, int] = "1 hour",
        user: Optional[str] = None,
        text_contains: Optional[str] = None,
        reaction: Optional[str] = None,
        include_url: bool = False,
        hours: Optional[int] = None,  # For backward compatibility
    ) -> List[Dict[str, Any]]:
        """
        Get messages from the Slack channel

        Args:
            time_range: Natural language time range (e.g., '1 hour', '2 days', '1 week')
                        or number of hours to look back
            user: Filter messages by username
            text_contains: Filter messages containing this text
            reaction: Filter messages with this reaction
            include_url: Include message URL in the output
            hours: (Deprecated) Number of hours to look back for messages

        Returns:
            List of messages as dictionaries
        """
        # Handle backward compatibility
        if hours is not None:
            time_delta = datetime.timedelta(hours=hours)
        else:
            # Parse time_range if it's a string
            if isinstance(time_range, str):
                time_delta = self.parse_time_range(time_range)
            else:
                # Assume it's a number of hours
                time_delta = datetime.timedelta(hours=time_range)

        # Calculate the timestamp for the specified time ago
        oldest = datetime.datetime.now() - time_delta
        oldest_ts = oldest.timestamp()

        try:
            # Get messages from the channel
            response = self.client.conversations_history(
                channel=self.channel_id,
                oldest=str(oldest_ts),
            )

            messages = []
            for msg in response["messages"]:
                # Skip messages without text
                if "text" not in msg:
                    continue

                # Get user info
                user_info = None
                user_name = None
                if "user" in msg:
                    try:
                        user_info = self.client.users_info(user=msg["user"])
                        user_name = user_info["user"]["name"]
                    except SlackApiError:
                        user_name = msg[
                            "user"
                        ]  # Fallback to user ID if user info can't be retrieved

                # Apply user filter if specified
                if user and (not user_name or user.lower() != user_name.lower()):
                    continue

                # Apply text filter if specified
                if text_contains and text_contains.lower() not in msg["text"].lower():
                    continue

                # Apply reaction filter if specified
                if reaction:
                    if "reactions" not in msg:
                        continue

                    reaction_found = False
                    for r in msg["reactions"]:
                        if r["name"] == reaction:
                            reaction_found = True
                            break

                    if not reaction_found:
                        continue

                # Format the message
                formatted_msg = {
                    "channel": self.channel,
                    "user": msg.get("user", ""),
                    "user_name": user_name,
                    "text": msg["text"],
                    "timestamp": self._format_timestamp(msg["ts"]),
                }

                # Add reactions if present
                if "reactions" in msg:
                    formatted_msg["reactions"] = msg["reactions"]

                # Add URL if requested
                if include_url:
                    workspace_id = self._get_workspace_id()
                    ts_for_url = msg["ts"].replace(".", "")
                    formatted_msg["url"] = (
                        f"https://{workspace_id}.slack.com/archives/{self.channel_id}/p{ts_for_url}"
                    )

                messages.append(formatted_msg)

            return messages

        except SlackApiError as e:
            raise ValueError(f"Error retrieving messages: {e}")

    def _format_timestamp(self, ts: str) -> str:
        """
        Format a Slack timestamp to ISO format

        Args:
            ts: Slack timestamp

        Returns:
            Formatted timestamp string
        """
        dt = datetime.datetime.fromtimestamp(float(ts))
        return dt.isoformat()

    def _get_workspace_id(self) -> str:
        """
        Get the workspace ID for URL generation

        Returns:
            Workspace ID
        """
        try:
            response = self.client.team_info()
            return response["team"]["domain"]
        except SlackApiError:
            # Fallback to a generic name if we can't get the workspace info
            return "workspace"
