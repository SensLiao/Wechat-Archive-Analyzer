"""App management commands — start the local Web App."""
from __future__ import annotations

import logging
import webbrowser

import click

logger = logging.getLogger("wxtools.interfaces.cli.app")


def _free_port(host: str, port: int) -> bool:
    """Kill any leftover process occupying *host:port*.

    Returns True if the port is (now) free, False if we couldn't free it.
    """
    import socket, time

    # Quick check — if we can bind, the port is already free
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            pass  # port in use — try to reclaim it

    logger.info("Port %d is in use, attempting to reclaim…", port)

    # Platform-specific: find and kill the process holding the port
    import subprocess, sys

    if sys.platform == "win32":
        # netstat -ano | findstr :<port>.*LISTENING → extract PID
        try:
            out = subprocess.check_output(
                f"netstat -ano | findstr :{port}",
                shell=True, text=True, stderr=subprocess.DEVNULL,
            )
            for line in out.strip().splitlines():
                if "LISTENING" in line:
                    pid = line.strip().split()[-1]
                    if pid.isdigit():
                        subprocess.run(
                            ["taskkill", "/PID", pid, "/F"],
                            capture_output=True,
                        )
                        click.echo(f"Stopped previous server (PID {pid}) on port {port}.")
                        break
        except subprocess.CalledProcessError:
            pass
    else:
        # Unix: lsof -ti :<port> → kill
        try:
            out = subprocess.check_output(
                ["lsof", "-ti", f":{port}"],
                text=True, stderr=subprocess.DEVNULL,
            )
            for pid in out.strip().splitlines():
                if pid.isdigit():
                    subprocess.run(["kill", "-9", pid], capture_output=True)
                    click.echo(f"Stopped previous server (PID {pid}) on port {port}.")
                    break
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    # Wait for the port to actually free (TIME_WAIT may linger briefly)
    for _ in range(10):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return True
            except OSError:
                time.sleep(0.5)

    return False


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

    # Reclaim port if a previous server didn't shut down cleanly
    if not _free_port(host, port):
        raise click.ClickException(
            f"Port {port} is still in use and could not be freed. "
            f"Try a different port: wxtools app start --port {port + 1}"
        )

    state = ctx.obj

    # Determine static dir — look for built frontend
    # parents[5] goes from interfaces/cli/commands/app.py up to the repo root
    static_dir = Path(__file__).resolve().parents[5] / "web" / "dist"
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
        # Token is injected into HTML by the backend — no URL param needed
        webbrowser.open(url)

    uvicorn.run(app_instance, host=host, port=port, log_level="info")
