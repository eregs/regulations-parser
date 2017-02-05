import click

from regparser.commands.annual_editions import annual_editions
from regparser.commands.annual_version import annual_version
from regparser.commands.diffs import diffs
from regparser.commands.fill_with_rules import fill_with_rules
from regparser.commands.import_notice import import_notice, parse_notice
from regparser.commands.layers import layers
from regparser.commands.notice_preamble import notice_preamble
from regparser.commands.proposal_versions import proposal_versions
from regparser.commands.versions import versions
from regparser.commands.write_to import write_to


@click.command()
@click.argument('xml_file', type=click.Path(exists=True))
@click.argument('output', envvar='EREGS_OUTPUT_DIR')
@click.option('--only-latest', is_flag=True, default=False,
              help="Don't derive historyl use the latest annual edition")
@click.pass_context
def proposal_pipeline(ctx, xml_file, output, only_latest):
    """Full proposal parsing pipeline. Reads the XML file provided, pulls out
    the preamble, parses versions of the relevant CFR parts, inserts a version
    for each associated with this proposal, builds layers + diffs, and writes
    them out."""
    ctx.invoke(import_notice, xml_file=xml_file)

    notice_xml = parse_notice(xml_file)
    ctx.invoke(notice_preamble, doc_number=notice_xml.version_id)

    for title, part in notice_xml.cfr_ref_pairs:
        if only_latest:
            ctx.invoke(annual_version, cfr_title=title, cfr_part=part)
        else:
            ctx.invoke(versions, cfr_title=title, cfr_part=part)
            ctx.invoke(annual_editions, cfr_title=title, cfr_part=part)

    ctx.invoke(proposal_versions, doc_number=notice_xml.version_id)

    for title, part in notice_xml.cfr_ref_pairs:
        ctx.invoke(fill_with_rules, cfr_title=title, cfr_part=part)
        ctx.invoke(diffs, cfr_title=title, cfr_part=part)

    ctx.invoke(layers)
    ctx.invoke(write_to, output=output)
