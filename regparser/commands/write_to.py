import logging

import click

from regparser.api_writer import Client
from regparser.commands import utils
from regparser.history.versions import Version
from regparser.index import entry
from regparser.notice.build import add_footnotes, process_sxs

logger = logging.getLogger(__name__)


def write_trees(client, only_title, only_part):
    for tree_entry in utils.relevant_paths(entry.Tree(), only_title,
                                           only_part):
        _, cfr_part, version_id = tree_entry.path
        content = tree_entry.read()
        client.regulation(cfr_part, version_id).write(content)


def write_layers(client, only_title, only_part):
    """Write all layers that match the filtering criteria. If CFR title/part
    are used to filter, only process CFR layers. Otherwise, process all
    layers."""
    for layer_entry in utils.relevant_paths(entry.Layer.cfr(), only_title,
                                            only_part):
        _, _, cfr_part, version_id, layer_name = layer_entry.path
        layer = layer_entry.read()
        doc_id = version_id + '/' + cfr_part
        client.layer(layer_name, 'cfr', doc_id).write(layer)

    if only_title is None and only_part is None:
        for sub_entry in entry.Layer().sub_entries():
            if sub_entry.path[0] == 'cfr':
                continue
            doc_type, doc_id, layer_name = sub_entry.path
            layer = sub_entry.read()
            client.layer(layer_name, doc_type, doc_id).write(layer)


def transform_notice(notice_xml):
    """The API has a different format for notices than the local XML. We'll
    need to convert and add appropriate fields"""
    as_dict = notice_xml.as_dict()
    as_dict['versions'] = {}
    for cfr_title, cfr_part in notice_xml.cfr_ref_pairs:
        version_dir = entry.Version(cfr_title, cfr_part)
        versions = [v.read() for v in version_dir.sub_entries()]
        with_parents = zip(versions, Version.parents_of(versions))
        for version, parent in with_parents:
            if version.identifier == notice_xml.version_id and parent:
                as_dict['versions'][cfr_part] = {"left": parent.identifier,
                                                 "right": version.identifier}

    # @todo - SxS and footnotes aren't used outside of CFPB
    add_footnotes(as_dict, notice_xml.xml)
    if notice_xml.cfr_ref_pairs:
        process_sxs(as_dict, notice_xml.xml)
    return as_dict


def write_notices(client, only_title, only_part):
    """
    :param int or None only_title: Filter results to one title
    :param int or None only_part: Filter results to one part
    """
    for notice_entry in entry.Notice().sub_entries():
        notice_xml = notice_entry.read()
        title_match = only_title is None or any(ref.title == only_title
                                                for ref in notice_xml.cfr_refs)
        # @todo - this doesn't confirm the part is within the title
        cfr_parts = [part for ref in notice_xml.cfr_refs for part in ref.parts]
        part_match = only_part is None or only_part in cfr_parts
        if title_match and part_match:
            client.notice(notice_entry.path[-1]).write(
                transform_notice(notice_xml))


def write_diffs(client, only_title, only_part):
    for diff_entry in utils.relevant_paths(entry.Diff(), only_title,
                                           only_part):
        _, cfr_part, lhs_id, rhs_id = diff_entry.path
        diff = diff_entry.read()
        client.diff(cfr_part, lhs_id, rhs_id).write(diff)


def write_preambles(client):
    for preamble_entry in entry.Preamble().sub_entries():
        preamble = preamble_entry.read()
        client.preamble(preamble_entry.path[-1]).write(preamble)


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
    if cfr_title is None and cfr_part is None:
        write_preambles(client)
    # Note that layers must always be written _after_ the trees they reference
    write_layers(client, cfr_title, cfr_part)
    write_notices(client, cfr_title, cfr_part)
    write_diffs(client, cfr_title, cfr_part)
