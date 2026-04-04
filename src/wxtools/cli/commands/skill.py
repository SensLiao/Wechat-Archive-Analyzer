"""Skill install/uninstall commands."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import click

from wxtools.cli.output import error_envelope, print_json, success_envelope

logger = logging.getLogger("wxtools.cli.skill")

SKILL_DEST = Path.home() / ".claude" / "skills" / "wechat.md"
CODEX_SKILL_DEST = Path.home() / ".codex" / "skills" / "wechat.md"


def _find_skill_template(target: str = "claude_code") -> Path:
    """Locate the bundled skill template for the given target."""
    pkg_dir = Path(__file__).resolve().parent.parent.parent
    template = pkg_dir / "adapters" / target / "skill_template.md"
    if template.exists():
        return template
    raise FileNotFoundError(f"Skill template not found at {template}")


def _install_codex(ctx, state) -> None:
    """Install wechat skill to Codex."""
    try:
        template = _find_skill_template("codex")
    except FileNotFoundError as e:
        if state.json_mode:
            print_json(error_envelope(
                "CONFIG_ERROR", str(e),
                "Reinstall wxtools package.",
                command="install-skill",
            ))
        else:
            click.echo(f"Error: {e}", err=True)
        ctx.exit(6)
        return

    if CODEX_SKILL_DEST.exists():
        if not state.json_mode:
            if not click.confirm(f"Codex skill already exists at {CODEX_SKILL_DEST}. Overwrite?"):
                click.echo("Aborted.")
                return

    CODEX_SKILL_DEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template, CODEX_SKILL_DEST)

    if state.json_mode:
        print_json(success_envelope(
            {"path": str(CODEX_SKILL_DEST), "action": "installed", "target": "codex"},
            command="install-skill",
        ))
    else:
        click.echo(f"Codex skill installed to {CODEX_SKILL_DEST}")
        click.echo("You can now use /wechat in Codex.")


def _uninstall_codex(ctx, state) -> None:
    """Remove wechat skill from Codex."""
    if not CODEX_SKILL_DEST.exists():
        if state.json_mode:
            print_json(success_envelope(
                {"path": str(CODEX_SKILL_DEST), "action": "not_found", "target": "codex"},
                command="uninstall-skill",
            ))
        else:
            click.echo("Codex skill not installed. Nothing to remove.")
        return

    CODEX_SKILL_DEST.unlink()

    if state.json_mode:
        print_json(success_envelope(
            {"path": str(CODEX_SKILL_DEST), "action": "removed", "target": "codex"},
            command="uninstall-skill",
        ))
    else:
        click.echo(f"Codex skill removed from {CODEX_SKILL_DEST}")


@click.command(name="install-skill")
@click.option("--codex", is_flag=True, help="Install to Codex (~/.codex/skills/) instead of Claude Code.")
@click.pass_context
def skill_group(ctx, codex: bool):
    """Install /wechat skill to Claude Code or Codex."""
    state = ctx.obj

    if codex:
        _install_codex(ctx, state)
        return

    try:
        template = _find_skill_template("claude_code")
    except FileNotFoundError as e:
        if state.json_mode:
            print_json(error_envelope(
                "CONFIG_ERROR", str(e),
                "Reinstall wxtools package.",
                command="install-skill",
            ))
        else:
            click.echo(f"Error: {e}", err=True)
        ctx.exit(6)
        return

    # Check if already installed
    if SKILL_DEST.exists():
        if not state.json_mode:
            if not click.confirm(f"Skill already exists at {SKILL_DEST}. Overwrite?"):
                click.echo("Aborted.")
                return

    SKILL_DEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template, SKILL_DEST)

    if state.json_mode:
        print_json(success_envelope(
            {"path": str(SKILL_DEST), "action": "installed", "target": "claude-code"},
            command="install-skill",
        ))
    else:
        click.echo(f"Skill installed to {SKILL_DEST}")
        click.echo("You can now use /wechat in Claude Code.")


@click.command(name="uninstall-skill")
@click.option("--codex", is_flag=True, help="Uninstall from Codex (~/.codex/skills/) instead of Claude Code.")
@click.pass_context
def uninstall_skill(ctx, codex: bool):
    """Remove /wechat skill from Claude Code or Codex."""
    state = ctx.obj

    if codex:
        _uninstall_codex(ctx, state)
        return

    if not SKILL_DEST.exists():
        if state.json_mode:
            print_json(success_envelope(
                {"path": str(SKILL_DEST), "action": "not_found", "target": "claude-code"},
                command="uninstall-skill",
            ))
        else:
            click.echo("Skill not installed. Nothing to remove.")
        return

    SKILL_DEST.unlink()

    if state.json_mode:
        print_json(success_envelope(
            {"path": str(SKILL_DEST), "action": "removed", "target": "claude-code"},
            command="uninstall-skill",
        ))
    else:
        click.echo(f"Skill removed from {SKILL_DEST}")
