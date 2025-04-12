"""
Command-line interface for slacraper
"""

import os
import sys
import json
import click
import warnings
from typing import Optional, Union

from .core import Slacraper


@click.command()
@click.option(
    "--channel",
    required=True,
    help="Slack channel name to scrape messages from",
)
@click.option(
    "--token",
    help="Slack Bot Token. Overrides SLACK_BOT_TOKEN environment variable if provided.",
)
@click.option(
    "--time-range",
    default="1 hour",
    help="Time range to look back (e.g., '1 hour', '2 days', '1 week', '30 minutes'). Default: '1 hour'.",
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
    user: Optional[str],
    text_contains: Optional[str],
    reaction: Optional[str],
    include_url: bool,
) -> None:
    """
    Scrape messages from a Slack channel
    """
    # final_time_range 変数は不要なので削除

    try:
        # Initialize the scraper
        # Token precedence: --token > SLACK_BOT_TOKEN
        scraper = Slacraper(channel=channel, token=token)

        # Get messages using the determined time range
        messages = scraper.get_messages(
            time_range=time_range,  # 直接 time_range を渡す
            # core.py が time_range 文字列または数値を処理する
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
