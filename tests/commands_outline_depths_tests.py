from click.testing import CliRunner

from regparser.commands.outline_depths import outline_depths


def test_produces_usage_message_with_no_arg():
    result = CliRunner().invoke(outline_depths)
    assert result.exit_code == 2
    assert 'Usage' in result.output


def test_returns_simple_result_for_a_simple_outline():
    result = CliRunner().invoke(outline_depths, ['a b'])
    assert result.output == "0 0\n"
    assert result.exit_code == 0


def test_handles_roman_numerals():
    result = CliRunner().invoke(outline_depths, ['1 2 3 i ii iv 4 5 i A'])
    assert result.output == "0 0 0 1 1 1 0 0 1 2\n"
    assert result.exit_code == 0
