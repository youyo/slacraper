"""
Core functionality for slacraper
"""

import os
import datetime
import re
import warnings
from typing import List, Dict, Any, Optional, Union, Tuple, Generator
from dateutil.relativedelta import relativedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from functools import lru_cache
import warnings  # warnings モジュールをインポート


class Slacraper:
    """
    Slack message scraper class
    """

    def __init__(
        self,
        channel: str,
        token: Optional[str] = None,
    ):
        """
        Initialize the Slacraper

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
        self._channel_id: Optional[str] = None
        self._user_cache: Dict[str, str] = {}
        self._workspace_id: Optional[str] = None

    @property
    def channel_id(self) -> str:
        """
        Get the channel ID from channel name

        Returns:
            str: Channel ID
        """
        if self._channel_id is not None:
            return self._channel_id

        # Search both public and private channels using pagination
        channel_types = ["public_channel", "private_channel"]
        for channel_type in channel_types:
            cursor = None
            while True:
                try:
                    response = self.client.conversations_list(
                        types=channel_type,
                        limit=200,  # Fetch in batches for efficiency
                        cursor=cursor,
                    )
                    # Ensure 'channels' key exists and is a list
                    channels_list = response.get("channels", [])
                    if not isinstance(channels_list, list):
                        warnings.warn(
                            f"Unexpected format for 'channels' in {channel_type} list response.",
                            UserWarning,
                        )
                        continue  # Continue to next channel type if format is wrong

                    for channel_info in channels_list:
                        # Ensure channel_info is a dict and has 'name' and 'id'
                        if (
                            isinstance(channel_info, dict)
                            and channel_info.get("name") == self.channel
                            and "id" in channel_info
                        ):
                            self._channel_id = channel_info["id"]
                            return self._channel_id  # Found the channel

                    # Check for pagination metadata
                    metadata = response.get("response_metadata", {})
                    cursor = metadata.get("next_cursor")

                    # Stop if no more pages or cursor is empty/missing
                    if not response.get("has_more") or not cursor:
                        break  # No more pages for this channel type

                except SlackApiError as e:
                    # If missing scopes for a type, log a warning and try the next type.
                    # Other errors should be raised.
                    if e.response and e.response.get("error") == "missing_scope":
                        warnings.warn(
                            f"Missing scope to list {channel_type}s. Ensure the bot token has necessary permissions (e.g., channels:read, groups:read). Error: {e}",
                            UserWarning,
                        )
                        break  # Move to the next channel type if scope is missing for this type
                    # Raise other Slack API errors, including original exception for context
                    raise ValueError(f"Error listing {channel_type}s: {e}") from e
                except Exception as e:
                    # Catch unexpected errors during processing
                    raise ValueError(
                        f"Unexpected error processing {channel_type} list: {e}"
                    ) from e

        # If the loop completes for all types without finding the channel
        raise ValueError(
            f"Channel '{self.channel}' not found in accessible public or private channels."
        )

    def parse_time_range(
        self, time_range: str
    ) -> Union[datetime.timedelta, relativedelta]:
        """
        Parse a natural language time range string into a timedelta or relativedelta.

        Args:
            time_range: Natural language time range (e.g., '1 hour', '2 days', '1 month').

        Returns:
            datetime.timedelta or dateutil.relativedelta.relativedelta: The parsed time duration.

        Raises:
            ValueError: If the time_range string cannot be parsed or is empty.
        """
        if not time_range:
            # Raise ValueError for empty string as it's invalid input.
            raise ValueError("Time range string cannot be empty.")

        time_range_norm = time_range.lower().strip()

        # Check for simple numeric hours first (common case)
        if time_range_norm.isdigit():
            # Ensure non-negative value
            hours_val = int(time_range_norm)
            if hours_val < 0:
                raise ValueError("Time range in hours cannot be negative.")
            return datetime.timedelta(hours=hours_val)

        # Regex matching for "number unit" format with specific units and end anchor
        match = re.match(
            r"(\d+)\s*(hours?|hr|hrs|minutes?|min|mins|days?|weeks?|wk|wks|months?|years?|yr|yrs)$",
            time_range_norm,
        )
        if match:
            value = int(match.group(1))
            unit = match.group(2)

            # Ensure non-negative value (already handled by \d+, but good practice)
            # if value < 0:
            #     raise ValueError("Time range value cannot be negative.")

            # Use startswith for flexibility with plurals, but unit is now guaranteed to be valid
            if unit.startswith("hour") or unit in ["hr", "hrs"]:
                return datetime.timedelta(hours=value)
            elif unit.startswith("minute") or unit in ["min", "mins"]:
                return datetime.timedelta(minutes=value)
            elif unit.startswith("day"):
                return datetime.timedelta(days=value)
            elif unit.startswith("week") or unit in ["wk", "wks"]:
                return datetime.timedelta(weeks=value)
            elif unit.startswith("month"):
                return relativedelta(months=value)
            elif unit.startswith("year") or unit in ["yr", "yrs"]:
                return relativedelta(years=value)
            # This part should theoretically not be reached if regex is correct

        # Handle 'a'/'an'/'one' and singular unit cases explicitly
        # time_range_norm is already normalized
        if time_range_norm in ["an hour", "one hour", "1 hour", "hour"]:
            return datetime.timedelta(hours=1)
        elif time_range_norm in ["a minute", "one minute", "1 minute", "minute"]:
            return datetime.timedelta(minutes=1)
        elif time_range_norm in ["a day", "one day", "1 day", "day", "today"]:
            return datetime.timedelta(days=1)
        elif time_range_norm in ["a week", "one week", "1 week", "week"]:
            return datetime.timedelta(weeks=1)
        elif time_range_norm in ["a month", "one month", "1 month", "month"]:
            return relativedelta(months=1)
        elif time_range_norm in ["a year", "one year", "1 year", "year"]:
            return relativedelta(years=1)

        # If nothing matches after all checks, raise an error
        raise ValueError(f"Could not parse time range: '{time_range}'")

    def _fetch_user_name(self, user_id: str) -> Optional[str]:
        """Fetch user name from user ID, using cache. Handles API errors."""
        if user_id in self._user_cache:
            return self._user_cache[user_id]

        try:
            user_info_response = self.client.users_info(user=user_id)
            # Ensure the response structure is as expected before accessing keys
            user_data = user_info_response.get("user")
            if isinstance(user_data, dict):
                user_name = user_data.get("name")
                if user_name:
                    self._user_cache[user_id] = user_name
                    return user_name
                else:
                    # User object exists but name is missing/empty
                    warnings.warn(
                        f"User ID {user_id} found but 'name' key is missing or empty in user_info response.",
                        UserWarning,
                    )
                    self._user_cache[user_id] = None  # Cache as None if name is missing
                    return None
            else:
                # Unexpected response structure
                warnings.warn(
                    f"Unexpected structure for 'user' object in users_info response for {user_id}.",
                    UserWarning,
                )
                self._user_cache[user_id] = None  # Cache failure
                return None

        except SlackApiError as e:
            # Handle specific, common errors gracefully
            error_type = e.response.get("error") if e.response else "unknown_error"
            if error_type == "user_not_found":
                # Don't print a warning for users not found, just cache None
                pass
            elif error_type == "missing_scope":
                warnings.warn(
                    f"Missing 'users:read' scope to fetch user info for {user_id}. Error: {e}",
                    UserWarning,
                )
            else:
                # Log other unexpected API errors
                warnings.warn(
                    f"Slack API error fetching user info for {user_id}: {e}",
                    UserWarning,
                )

            # Cache failure regardless of the specific API error
            self._user_cache[user_id] = None
            return None
        except Exception as e:
            # Catch any other unexpected errors during the process
            warnings.warn(
                f"Unexpected error fetching user name for {user_id}: {e}", UserWarning
            )
            self._user_cache[user_id] = None  # Cache failure
            return None

    def _fetch_paginated_messages(
        self, oldest_ts: float, limit: int = 200
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Fetch messages using cursor-based pagination with robust error handling.

        Yields:
            Dict[str, Any]: Individual message dictionaries.

        Raises:
            ValueError: If a Slack API error occurs that prevents message retrieval.
            RuntimeError: If an unexpected error occurs during processing.
        """
        cursor = None
        page_count = 0  # Add page count for debugging/logging
        while True:
            page_count += 1
            try:
                response = self.client.conversations_history(
                    channel=self.channel_id,  # Assumes channel_id is already validated/fetched
                    oldest=str(oldest_ts),
                    limit=limit,
                    cursor=cursor,
                )
                # Validate response structure before proceeding
                if not isinstance(response.get("messages"), list):
                    warnings.warn(
                        f"Page {page_count}: 'messages' key missing or not a list in conversations.history response. Response: {response}",
                        UserWarning,
                    )
                    break  # Stop pagination if response format is invalid

                messages_list = response["messages"]
                for msg in messages_list:
                    # Optionally add basic validation for each message dict
                    if isinstance(msg, dict):
                        yield msg
                    else:
                        warnings.warn(
                            f"Page {page_count}: Skipping non-dictionary item in messages list: {msg}",
                            UserWarning,
                        )

                # Check for pagination metadata safely
                metadata = response.get("response_metadata", {})
                if not isinstance(metadata, dict):
                    warnings.warn(
                        f"Page {page_count}: 'response_metadata' is not a dictionary. Stopping pagination.",
                        UserWarning,
                    )
                    break

                cursor = metadata.get("next_cursor")

                # Stop if no more pages indicated or cursor is missing/empty
                if not response.get("has_more") or not cursor:
                    break

            except SlackApiError as e:
                # Handle specific API errors potentially recoverable or informative
                error_type = e.response.get("error") if e.response else "unknown_error"
                if error_type == "ratelimited":
                    # Basic rate limit handling (could implement backoff)
                    warnings.warn(
                        f"Page {page_count}: Rate limited fetching messages. Consider adding delays or reducing frequency. Error: {e}",
                        UserWarning,
                    )
                    # Depending on strategy, could break, sleep, or re-raise
                    # For now, re-raise as ValueError to signal failure
                    raise ValueError(
                        f"Rate limited while retrieving messages from channel {self.channel_id}. Error: {e}"
                    ) from e
                elif error_type == "missing_scope":
                    # This scope should generally be present if channel_id was found, but check anyway
                    raise ValueError(
                        f"Missing 'channels:history' or 'groups:history' scope for channel {self.channel_id}. Error: {e}"
                    ) from e
                else:
                    # Raise other Slack API errors
                    raise ValueError(
                        f"Slack API error on page {page_count} retrieving messages from channel {self.channel_id}: {e}"
                    ) from e

            except Exception as e:
                # Catch any other unexpected errors during the loop
                raise RuntimeError(
                    f"Unexpected error on page {page_count} fetching paginated messages: {e}"
                ) from e

    def get_messages(
        self,
        time_range: Union[str, int, float] = "1 hour",  # Allow float for hours
        user: Optional[str] = None,
        text_contains: Optional[str] = None,
        reaction: Optional[str] = None,
        include_url: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get messages from the Slack channel with pagination and filtering.

        Args:
            time_range: Natural language time range (e.g., '1 hour', '2 days', '1 week')
                        or number of hours (int or float) to look back.
            user: Filter messages by username (case-insensitive).
            text_contains: Filter messages containing this text (case-insensitive).
            reaction: Filter messages with this reaction.
            include_url: Include message URL in the output.

        Returns:
            List of messages as dictionaries.

        Raises:
            ValueError: If channel is not found, token is invalid, time_range is invalid,
                        or an API error occurs during message retrieval.
            TypeError: If time_range or hours has an invalid type.
        """
        time_delta: Union[datetime.timedelta, relativedelta]

        if isinstance(time_range, (int, float)):
            if time_range < 0:
                raise ValueError("time_range (hours) cannot be negative.")
            time_delta = datetime.timedelta(hours=time_range)
        elif isinstance(time_range, str):
            try:
                # parse_time_range now returns Union[timedelta, relativedelta]
                # or raises ValueError
                time_delta = self.parse_time_range(time_range)
            except ValueError as e:
                # Improve error message clarity
                raise ValueError(
                    f"Invalid time_range string: '{time_range}'. {e}"
                ) from e
        else:
            raise TypeError("time_range must be a string or a number (hours).")

        # --- Calculate oldest timestamp ---
        # Use timezone-aware datetime for calculations to avoid ambiguity
        now = datetime.datetime.now(datetime.timezone.utc)

        try:
            if isinstance(time_delta, relativedelta):
                # relativedelta subtraction works directly with timezone-aware datetime
                oldest_dt = now - time_delta
            elif isinstance(time_delta, datetime.timedelta):
                oldest_dt = now - time_delta
            else:
                # Should be unreachable due to earlier checks
                raise TypeError("Internal error: Unexpected type for time_delta.")
        except OverflowError:
            # Handle cases where time_delta is too large resulting in invalid date
            raise ValueError(
                "Calculated time range results in an invalid date/time (too far in the past)."
            )

        oldest_ts = oldest_dt.timestamp()

        # --- Fetch and process messages ---
        messages = []
        # Fetch workspace_id and channel_id once if needed, handling potential errors
        current_channel_id = None
        workspace_id = None
        try:
            # Access channel_id property to trigger fetching if not already done
            current_channel_id = self.channel_id
            if include_url:
                workspace_id = self._get_workspace_id()
        except ValueError as e:
            # Propagate channel finding or workspace ID errors clearly
            raise ValueError(
                f"Could not determine channel ID or workspace ID needed for operation: {e}"
            ) from e

        # Use the generator to fetch messages page by page
        try:
            for msg in self._fetch_paginated_messages(oldest_ts):
                # Basic message validation (ensure it's a dictionary)
                if not isinstance(msg, dict):
                    warnings.warn(
                        f"Skipping non-dictionary item in messages: {msg}", UserWarning
                    )
                    continue

                # Check for essential keys 'text' and 'ts'
                msg_text = msg.get("text")  # Use .get for safer access
                msg_ts = msg.get("ts")
                if msg_text is None or msg_ts is None:
                    # Skip messages missing essential fields
                    continue

                # --- Filtering ---
                user_id = msg.get("user")
                user_name = self._fetch_user_name(user_id) if user_id else None

                # User filter (case-insensitive)
                if user and (not user_name or user.lower() != user_name.lower()):
                    continue

                # Text filter (case-insensitive)
                # Ensure msg_text is treated as a string for comparison
                if text_contains and text_contains.lower() not in str(msg_text).lower():
                    continue

                # Reaction filter
                reactions_list = msg.get("reactions")  # Cache for reuse
                if reaction:
                    if not isinstance(reactions_list, list):
                        continue
                    # Check reaction name safely within the list comprehension
                    if not any(
                        r.get("name") == reaction
                        for r in reactions_list
                        if isinstance(r, dict)
                    ):
                        continue

                # --- Formatting ---
                formatted_msg = {
                    "channel": self.channel,
                    "user": user_id or "",
                    "user_name": user_name,  # Could be None
                    "text": str(msg_text),  # Ensure text is string
                    "timestamp": self._format_timestamp(msg_ts),  # Format timestamp
                }

                # Add reactions if present and valid
                if isinstance(reactions_list, list):
                    formatted_msg["reactions"] = reactions_list

                # Add URL if requested and IDs are valid
                if (
                    include_url
                    and workspace_id
                    and workspace_id != "workspace"
                    and current_channel_id
                ):
                    # Ensure timestamp is string before replacing
                    ts_for_url = str(msg_ts).replace(".", "")
                    formatted_msg["url"] = (
                        f"https://{workspace_id}.slack.com/archives/{current_channel_id}/p{ts_for_url}"
                    )

                messages.append(formatted_msg)

        except ValueError as e:
            # Catch errors from _fetch_paginated_messages and re-raise with context
            raise ValueError(f"Failed to retrieve messages: {e}") from e
        except Exception as e:
            # Catch any other unexpected errors during message processing
            raise RuntimeError(
                f"An unexpected error occurred while processing messages: {e}"
            ) from e

        return messages

    # L487 の不要なコメントを削除

    def _format_timestamp(self, ts: str) -> str:
        """
        Format a Slack timestamp string to ISO 8601 format (UTC).

        Args:
            ts: Slack timestamp (string like "1678886400.000100").

        Returns:
            Formatted timestamp string in ISO 8601 format with 'Z' for UTC,
            or the original timestamp string if formatting fails.
        """
        try:
            # Convert Slack timestamp string to float, then to timezone-aware datetime in UTC
            dt_utc = datetime.datetime.fromtimestamp(
                float(ts), tz=datetime.timezone.utc
            )
            # Format to ISO 8601 with milliseconds and 'Z' UTC designator
            # Ensure microseconds are handled correctly (strftime %f gives microseconds)
            # Pad with zeros if needed to get 3 digits for milliseconds
            microseconds = dt_utc.strftime("%f")
            milliseconds = microseconds[:3].ljust(
                3, "0"
            )  # Take first 3 digits, pad if less
            return dt_utc.strftime(f"%Y-%m-%dT%H:%M:%S.{milliseconds}Z")
        except (ValueError, TypeError, OverflowError) as e:
            # Handle potential errors during conversion (e.g., invalid format, out of range)
            warnings.warn(
                f"Could not format timestamp '{ts}'. Error: {e}. Returning original value.",
                UserWarning,
            )
            # Ensure the returned value is always a string, even if input wasn't
            return str(ts)

    @lru_cache(maxsize=1)  # Keep lru_cache for automatic caching
    def _get_workspace_id(self) -> str:
        """
        Get the workspace domain (e.g., 'myworkspace') for URL generation.
        Uses team.info API call and caches the result via lru_cache.

        Returns:
            Workspace domain string, or 'workspace' as a fallback if the API call fails
            or the domain is not found in the response.
        """
        # lru_cache handles the caching, no need for explicit self._workspace_id check
        try:
            response = self.client.team_info()
            # Safely access nested dictionary keys using .get() to avoid KeyErrors
            team_data = response.get("team")
            if isinstance(team_data, dict):
                domain = team_data.get("domain")
                if domain and isinstance(domain, str):
                    return domain  # Return the found domain
                else:
                    # Log if the domain key is missing or not a string
                    warnings.warn(
                        "Warning: 'domain' key missing, empty, or not a string in team_info response['team']. Using 'workspace' fallback.",
                        UserWarning,
                    )
                    return "workspace"  # Fallback
            else:
                # Log if the 'team' key is missing or not a dictionary
                warnings.warn(
                    "Warning: 'team' key missing or not a dictionary in team_info response. Using 'workspace' fallback.",
                    UserWarning,
                )
                return "workspace"  # Fallback

        except SlackApiError as e:
            # Log the API error for debugging purposes
            error_type = e.response.get("error") if e.response else "unknown_error"
            warnings.warn(
                f"Slack API error ({error_type}) retrieving workspace domain via team_info. Error: {e}. Using 'workspace' fallback.",
                UserWarning,
            )
            return "workspace"  # Fallback in case of API error
        except Exception as e:
            # Catch any other unexpected errors during the API call or processing
            warnings.warn(
                f"Unexpected error retrieving workspace domain: {e}. Using 'workspace' fallback.",
                UserWarning,
            )
            return "workspace"  # Fallback for other errors
