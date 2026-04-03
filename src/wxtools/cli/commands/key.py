"""Key management commands."""

import click

@click.group()
def key():
    """Manage WeChat decryption keys."""
    pass

@key.command()
@click.pass_context
def extract(ctx):
    """Extract key from running WeChat process."""
    click.echo("Not implemented yet")

@key.command()
@click.pass_context
def status(ctx):
    """Show stored key status."""
    click.echo("Not implemented yet")

@key.command(name="set-password")
@click.pass_context
def set_password(ctx):
    """Set password protection for stored keys."""
    click.echo("Not implemented yet")

@key.command(name="remove-password")
@click.pass_context
def remove_password(ctx):
    """Remove password protection."""
    click.echo("Not implemented yet")
