from click.testing import CliRunner
from wxtools.cli.main import cli


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "wxtools" in result.output.lower() or "Usage" in result.output


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.3.0" in result.output


def test_query_surface_option_in_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["query", "--help"])
    assert result.exit_code == 0
    assert "--surface" in result.output
    assert "chat" in result.output
    assert "public" in result.output
    assert "moments" in result.output


def test_export_surface_option_in_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["export", "--help"])
    assert result.exit_code == 0
    assert "--surface" in result.output
