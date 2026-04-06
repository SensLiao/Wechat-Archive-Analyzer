"""App management commands — start the local Web App."""
from __future__ import annotations

import logging
import webbrowser

import click

logger = logging.getLogger("wxtools.interfaces.cli.app")


@click.group()
def app():
    """Manage the local Web App."""
    pass


@app.command()
@click.option("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1).")
@click.option("--port", type=int, default=8808, help="Port (default: 8808).")
@click.option(
    "--open/--no-open", default=True, help="Auto-open browser (default: --open)."
)
@click.pass_context
def start(ctx, host, port, open):
    """Start the local Web App (API + frontend)."""
    import uvicorn
    from pathlib import Path

    from wxtools.interfaces.api.app import create_app

    state = ctx.obj

    # Determine static dir — look for built frontend
    static_dir = Path(__file__).resolve().parents[3] / "web" / "dist"
    if not static_dir.is_dir():
        static_dir = None

    app_instance, token = create_app(static_dir=static_dir)

    url = f"http://{host}:{port}"

    if not (state and state.json_mode):
        click.echo(f"wxtools Web App starting at {url}")
        click.echo(f"Session token: {token}")
        click.echo(f"API docs: {url}/api/docs")
        if static_dir:
            click.echo(f"Frontend: {url}")
        else:
            click.echo("Frontend not built. Run 'cd web && npm run build' first.")
        click.echo("Press Ctrl+C to stop.\n")

    if open and not (state and state.json_mode):
        # Open browser with token in URL for convenience
        webbrowser.open(f"{url}?token={token}")

    uvicorn.run(app_instance, host=host, port=port, log_level="info")
