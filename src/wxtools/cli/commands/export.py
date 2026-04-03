"""Export command."""

import click

@click.command()
@click.option("--format", "fmt", default="json", help="Output format (v1: json only).")
@click.option("--output", "-o", "output_path", help="Output file or directory.")
@click.option("--contact", help="Scope to contact.")
@click.option("--conversation", help="Scope to conversation/group.")
@click.option("--since", help="Start date.")
@click.option("--until", "until_date", help="End date.")
@click.option("--limit", type=int, help="Max messages.")
@click.option("--account", help="Select account.")
@click.option("--yes", is_flag=True, help="Skip confirmation for large exports.")
@click.pass_context
def export(ctx, fmt, output_path, contact, conversation, since, until_date, limit, account, yes):
    """Export messages to file."""
    click.echo("Not implemented yet")
