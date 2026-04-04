"""E2E integration tests — requires real WeChat data on Windows.

Skipped by default. Run with: WXTOOLS_E2E=1 python -X utf8 -m pytest tests/integration/ -v
"""
import os
import sys
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("WXTOOLS_E2E"),
    reason="Set WXTOOLS_E2E=1 to run integration tests",
)


def test_key_extract_and_verify():
    from click.testing import CliRunner
    from wxtools.cli.main import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["key", "extract", "--json"])
    assert result.exit_code == 0 or "already stored" in result.output
    result = runner.invoke(cli, ["key", "verify", "--json"])
    assert result.exit_code == 0


def test_query_with_session():
    from click.testing import CliRunner
    from wxtools.cli.main import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["query", "你好", "--limit", "5", "--json"])
    assert result.exit_code == 0


def test_export_all_formats():
    import tempfile
    from click.testing import CliRunner
    from wxtools.cli.main import cli
    runner = CliRunner()
    for fmt in ["json", "csv", "html"]:
        with tempfile.TemporaryDirectory() as td:
            result = runner.invoke(cli, ["export", "--format", fmt, "-o", td, "--limit", "10", "--yes", "--json"])
            assert result.exit_code == 0, f"Export {fmt} failed: {result.output}"
