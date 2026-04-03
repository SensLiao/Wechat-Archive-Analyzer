"""Skill install/uninstall commands."""

import click

@click.command(name="install-skill")
@click.pass_context
def skill_group(ctx):
    """Install /wechat skill to Claude Code."""
    click.echo("Not implemented yet")

@click.command(name="uninstall-skill")
@click.pass_context
def uninstall_skill(ctx):
    """Remove /wechat skill from Claude Code."""
    click.echo("Not implemented yet")
