# @todo - this should be combined with build_from.py
import click

from regparser.builder import notices_for_cfr_part


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
@click.option('--include-notices-without-changes', is_flag=True,
              help='Include notices which do not change the regulation')
def notice_order(cfr_title, cfr_part, include_notices_without_changes):
    """Order notices associated with a reg."""
    notices_by_date = notices_for_cfr_part(str(cfr_title), str(cfr_part))
    for date in sorted(notices_by_date.keys()):
        click.echo(date)
        for notice in notices_by_date[date]:
            if 'changes' in notice or include_notices_without_changes:
                click.echo("\t" + notice['document_number'])
