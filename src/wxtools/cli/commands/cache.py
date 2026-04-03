"""Cache management commands."""

import click

@click.group()
def cache():
    """Manage decrypted database cache."""
    pass

@cache.command()
@click.pass_context
def status(ctx):
    """Show cache status."""
    click.echo("Not implemented yet")

@cache.command()
@click.option("--account", help="Clear cache for specific account.")
@click.option("--yes", is_flag=True, help="Skip confirmation.")
@click.pass_context
def clear(ctx, account, yes):
    """Clear decrypted cache."""
    click.echo("Not implemented yet")
