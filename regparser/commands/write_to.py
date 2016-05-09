import click
import logging

from regparser.api_writer import Client
from regparser.commands import utils
from regparser.index import entry
from regparser.notice.build import add_footnotes, process_sxs


logger = logging.getLogger(__name__)


def write_trees(client, only_title, only_part):
    for tree_entry in utils.relevant_paths(entry.Tree(), only_title,
                                           only_part):
        cfr_title, cfr_part, version_id = tree_entry.path
        client.regulation(cfr_part, version_id).write(tree_entry.read())


def write_layers(client, only_title, only_part):
    """Write all layers that match the filtering criteria. If CFR title/part
    are used to filter, only process CFR layers. Otherwise, process all
    layers."""
    for layer_dir in utils.relevant_paths(entry.Layer.cfr(), only_title,
                                          only_part):
        _, cfr_title, cfr_part, version_id = layer_dir.path
        for layer_name in layer_dir:
            layer = (layer_dir / layer_name).read()
            doc_id = version_id + '/' + cfr_part
            client.layer(layer_name, 'cfr', doc_id).write(layer)

    if only_title is None and only_part is None:
        non_cfr_doc_types = [doc_type for doc_type in entry.Layer()
                             if doc_type != 'cfr']
        for doc_type in non_cfr_doc_types:
            for doc_id in entry.Layer(doc_type):
                for layer_name in entry.Layer(doc_type, doc_id):
                    layer = entry.Layer(doc_type, doc_id, layer_name).read()
                    client.layer(layer_name, doc_type, doc_id).write(layer)


def write_notices(client, only_title, only_part):
    """
    :param int or None only_title: Filter results to one title
    :param int or None only_part: Filter results to one part
    """
    notice_dir = entry.Notice()
    for version_id in notice_dir:
        notice_xml = (notice_dir / version_id).read()
        title_match = only_title is None or any(ref.title == only_title
                                                for ref in notice_xml.cfr_refs)
        # @todo - this doesn't confirm the part is within the title
        cfr_parts = [part for ref in notice_xml.cfr_refs for part in ref.parts]
        part_match = only_part is None or only_part in cfr_parts
        if title_match and part_match:
            as_dict = notice_xml.as_dict()
            # @todo - SxS and footnotes aren't used outside of CFPB
            add_footnotes(as_dict, notice_xml.xml)
            if cfr_parts:
                process_sxs(as_dict, notice_xml.xml)
            client.notice(version_id).write(as_dict)


def write_diffs(client, only_title, only_part):
    for diff_dir in utils.relevant_paths(entry.Diff(), only_title, only_part):
        cfr_title, cfr_part, lhs_id = diff_dir.path
        for rhs_id in diff_dir:
            diff = (diff_dir / rhs_id).read()
            client.diff(cfr_part, lhs_id, rhs_id).write(diff)


def write_preambles(client):
    for doc_id in entry.Preamble():
        preamble = entry.Preamble(doc_id).read()
        client.preamble(doc_id).write(preamble)


@click.command()
@click.argument('output', envvar='EREGS_OUTPUT_DIR')
@click.option('--cfr_title', type=int, help="Limit to one CFR title")
@click.option('--cfr_part', type=int, help="Limit to one CFR part")
def write_to(output, cfr_title, cfr_part):
    """Export data. Sends all data in the index to an external source.

    \b
    OUTPUT can be a
    * directory (if it does not exist, it will be created)
    * uri (the base url of an instance of regulations-core)
    * a directory prefixed with "git://". This will export to a git
      repository"""
    logger.info("Export output - %s CFR %s, Destination: %s",
                cfr_title, cfr_part, output)
    client = Client(output)
    write_trees(client, cfr_title, cfr_part)
    write_layers(client, cfr_title, cfr_part)
    write_notices(client, cfr_title, cfr_part)
    write_diffs(client, cfr_title, cfr_part)
    if cfr_title is None and cfr_part is None:
        write_preambles(client)
