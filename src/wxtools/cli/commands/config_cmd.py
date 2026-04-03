"""Config commands."""

import click

@click.group(name="config")
def config():
    """Manage configuration."""
    pass

@config.command()
@click.pass_context
def show(ctx):
    """Display current configuration."""
    click.echo("Not implemented yet")

@config.command(name="set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def set_config(ctx, key, value):
    """Set a configuration value."""
    click.echo("Not implemented yet")
