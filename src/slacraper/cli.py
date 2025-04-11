"""
Command-line interface for slacraper
"""

import os
import sys
import json
import click
from typing import Optional

from .core import SlackScraper


@click.command()
@click.option(
    "--channel",
    required=True,
    help="Slack channel name to scrape messages from",
)
@click.option(
    "--token",
    help="Slack Bot Token. If not provided, it will be read from SLACK_BOT_TOKEN environment variable",
)
@click.option(
    "--time-range",
    default="1 hour",
    help="Time range to look back for messages (e.g., '1 hour', '2 days', '1 week', default: '1 hour')",
)
@click.option(
    "--hours",
    type=int,
    help="(Deprecated) Number of hours to look back for messages",
)
@click.option(
    "--user",
    help="Filter messages by username",
)
@click.option(
    "--text-contains",
    help="Filter messages containing this text",
)
@click.option(
    "--reaction",
    help="Filter messages with this reaction",
)
@click.option(
    "--include-url",
    is_flag=True,
    help="Include message URL in the output",
)
def main(
    channel: str,
    token: Optional[str],
    time_range: str,
    hours: Optional[int],
    user: Optional[str],
    text_contains: Optional[str],
    reaction: Optional[str],
    include_url: bool,
) -> None:
    """
    Scrape messages from a Slack channel
    """
    try:
        # Initialize the scraper
        scraper = SlackScraper(channel=channel, token=token)

        # Get messages
        messages = scraper.get_messages(
            time_range=time_range,  # 常にtime_rangeを使用
            hours=hours,  # hoursも明示的に渡す
            user=user,
            text_contains=text_contains,
            reaction=reaction,
            include_url=include_url,
        )

        # Output as JSON
        print(json.dumps(messages, ensure_ascii=False, indent=2))

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
