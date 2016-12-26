from click.testing import CliRunner

from regparser.commands.derive_depths import derive_depths


def test_produces_usage_message_with_no_arg():
    result = CliRunner().invoke(derive_depths)
    assert result.exit_code == 2
    assert 'Usage' in result.output


def test_returns_simple_result_for_a_simple_outline():
    result = CliRunner().invoke(derive_depths, '(a),(b),(c)')
    assert result.exit_code == 0
    assert result.output == "[0, 0, 0]\n"
