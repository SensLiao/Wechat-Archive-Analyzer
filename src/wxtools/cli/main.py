"""wxtools CLI entry point."""

from __future__ import annotations

import os
import sys

import click

# Force UTF-8 on Windows to avoid GBK encoding errors with emoji/CJK
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

import wxtools


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

    # Initialize logging
    from wxtools.core.config import load_config
    from wxtools.core.logging_setup import setup_logging

    cfg = load_config()
    setup_logging(
        verbosity=verbose,
        json_mode=json_mode,
        log_dir=cfg.logs_dir,
    )


# Import and register command groups after cli is defined
from wxtools.cli.commands import key, query, export, cache, config_cmd, skill  # noqa: E402
from wxtools.cli.commands import app as app_cmd  # noqa: E402

cli.add_command(key.key)
cli.add_command(query.query)
cli.add_command(export.export)
cli.add_command(cache.cache)
cli.add_command(config_cmd.config)
cli.add_command(skill.skill_group, name="install-skill")
cli.add_command(skill.uninstall_skill, name="uninstall-skill")
cli.add_command(app_cmd.app)
