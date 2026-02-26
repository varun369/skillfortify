from skillfortify import __version__
from click.testing import CliRunner

from skillfortify.cli.main import cli


def test_version():
    assert __version__ == "0.1.0"


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Formal verification" in result.output


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output
