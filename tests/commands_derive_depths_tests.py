from click.testing import CliRunner

from regparser.commands.derive_depths import derive_depths


def test_produces_usage_message_with_no_args():
    result = CliRunner().invoke(derive_depths)
    assert result.exit_code == 2
    assert 'Usage' in result.output

