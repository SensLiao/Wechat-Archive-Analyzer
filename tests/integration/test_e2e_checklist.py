"""E2E integration tests — requires real WeChat data on Windows.

Skipped by default. Run with: WXTOOLS_E2E=1 python -X utf8 -m pytest tests/integration/ -v
"""
import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("WXTOOLS_E2E"),
    reason="Set WXTOOLS_E2E=1 to run integration tests",
)


def test_key_extract_and_verify():
    from click.testing import CliRunner
    from wxtools.interfaces.cli.main import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "key", "extract"])
    assert result.exit_code == 0 or "already stored" in result.output
    result = runner.invoke(cli, ["--json", "key", "verify"])
    assert result.exit_code == 0


def test_query_with_session():
    from click.testing import CliRunner
    from wxtools.interfaces.cli.main import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "query", "你好", "--limit", "5"])
    assert result.exit_code == 0


def test_export_all_formats():
    import tempfile
    from click.testing import CliRunner
    from wxtools.interfaces.cli.main import cli
    runner = CliRunner()
    for fmt in ["json", "csv", "html"]:
        with tempfile.TemporaryDirectory() as td:
            result = runner.invoke(cli, ["--json", "export", "--format", fmt, "-o", td, "--limit", "10", "--yes"])
            assert result.exit_code == 0, f"Export {fmt} failed: {result.output}"
