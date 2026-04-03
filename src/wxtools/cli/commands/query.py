"""Query command."""

import click

@click.command()
@click.argument("keyword", required=False)
@click.option("--contact", help="Filter by contact name.")
@click.option("--conversation", help="Filter by conversation/group name.")
@click.option("--since", help="Start date (YYYY-MM-DD).")
@click.option("--until", "until_date", help="End date (YYYY-MM-DD).")
@click.option("--type", "msg_type", help="Message type filter.")
@click.option("--limit", type=int, default=100, help="Max results.")
@click.option("--offset", type=int, default=0, help="Pagination offset.")
@click.option("--sql", help="Raw SQL query (debug mode).")
@click.option("--account", help="Select account wxid.")
@click.pass_context
def query(ctx, keyword, contact, conversation, since, until_date, msg_type, limit, offset, sql, account):
    """Search messages in decrypted WeChat databases."""
    click.echo("Not implemented yet")
