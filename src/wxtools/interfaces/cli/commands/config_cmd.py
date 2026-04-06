"""Config commands."""

from __future__ import annotations

import logging

import click
import yaml

from wxtools.interfaces.cli.output import error_envelope, print_json, success_envelope
from wxtools.runtime.config import DEFAULTS, VALIDATORS, load_config

logger = logging.getLogger("wxtools.interfaces.cli.config")


@click.group(name="config")
def config():
    """Manage configuration."""
    pass


@config.command()
@click.pass_context
def show(ctx):
    """Display current configuration."""
    state = ctx.obj
    cfg = load_config()
    data = cfg.to_dict()

    if state.json_mode:
        print_json(success_envelope(
            {"config": data, "config_file": str(cfg.home_dir / "config.yaml")},
            command="config show",
        ))
    else:
        click.echo(f"Config file: {cfg.home_dir / 'config.yaml'}\n")
        for key, val in sorted(data.items()):
            default = DEFAULTS.get(key)
            marker = "" if val == default else " (custom)"
            click.echo(f"  {key}: {val}{marker}")


@config.command(name="set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def set_config(ctx, key, value):
    """Set a configuration value."""
    state = ctx.obj
    cfg = load_config()

    if key not in DEFAULTS:
        msg = f"Unknown config key: {key}"
        valid_keys = ", ".join(sorted(DEFAULTS.keys()))
        if state.json_mode:
            print_json(error_envelope(
                "CONFIG_ERROR", msg,
                f"Valid keys: {valid_keys}",
                command="config set",
            ))
        else:
            click.echo(f"Error: {msg}", err=True)
            click.echo(f"  Valid keys: {valid_keys}", err=True)
        ctx.exit(6)
        return

    # Validate value
    if key in VALIDATORS:
        try:
            value = str(VALIDATORS[key](value))
        except (ValueError, TypeError) as e:
            if state.json_mode:
                print_json(error_envelope(
                    "CONFIG_ERROR", f"Invalid value for {key}: {e}",
                    "Check config documentation.",
                    command="config set",
                ))
            else:
                click.echo(f"Error: Invalid value for {key}: {e}", err=True)
            ctx.exit(6)
            return

    # Read existing config file
    config_file = cfg.home_dir / "config.yaml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            existing = yaml.safe_load(f) or {}

    # Coerce numeric values
    if key in ("default_limit", "query_timeout"):
        try:
            value = int(value)
        except ValueError:
            pass

    existing[key] = value

    with open(config_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(existing, f, default_flow_style=False, allow_unicode=True)

    if state.json_mode:
        print_json(success_envelope(
            {"key": key, "value": value},
            command="config set",
        ))
    else:
        click.echo(f"Set {key} = {value}")
