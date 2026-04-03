"""wxtools CLI entry point."""

from __future__ import annotations

import json
import sys

import click

import wxtools
from wxtools.core.errors import WxToolsError
from wxtools.cli.output import error_envelope, print_json


class GlobalState:
    def __init__(self):
        self.json_mode: bool = False
        self.verbosity: int = 0
        self.command_name: str = ""


pass_state = click.make_pass_decorator(GlobalState, ensure=True)


@click.group()
@click.option("--json", "json_mode", is_flag=True, help="Output JSON envelopes.")
@click.option("-v", "--verbose", count=True, help="Increase verbosity (-v INFO, -vv DEBUG).")
@click.version_option(wxtools.__version__, prog_name="wxtools")
@click.pass_context
def cli(ctx: click.Context, json_mode: bool, verbose: int):
    """wxtools — Local-first WeChat chat history toolkit."""
    state = GlobalState()
    state.json_mode = json_mode
    state.verbosity = verbose
    ctx.obj = state


# Import and register command groups after cli is defined
from wxtools.cli.commands import key, query, export, cache, config_cmd, skill  # noqa: E402

cli.add_command(key.key)
cli.add_command(query.query)
cli.add_command(export.export)
cli.add_command(cache.cache)
cli.add_command(config_cmd.config)
cli.add_command(skill.skill_group, name="install-skill")
cli.add_command(skill.uninstall_skill, name="uninstall-skill")
