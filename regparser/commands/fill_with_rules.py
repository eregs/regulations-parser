import json
import logging
from collections import defaultdict
from itertools import dropwhile

import click

from regparser.notice.compiler import compile_regulation
from regparser.notice.xml import NoticeXML
from regparser.tree.struct import FullNodeEncoder, frozen_node_decode_hook
from regparser.web.index.models import CFRVersion, Document

logger = logging.getLogger(__name__)


def build_pairs(cfr_title, cfr_part):
    """Find all pairs of versions such that the first of each pair needs to
    (and can) be built and the second is the version that it builds on."""
    query = CFRVersion.objects.select_related('source').filter(
        cfr_title=cfr_title, cfr_part=cfr_part)

    versions = [v for v in sorted(query)]
    version_pairs = zip(versions, CFRVersion.parents_of(versions))
    version_pairs = dropwhile(lambda (v, p): p is None, version_pairs)
    version_pairs = dropwhile(lambda (v, p): not p.has_doc(), version_pairs)
    return [(v, p) for v, p in version_pairs if not v.has_doc()]


def doc_to_tree(doc):
    as_text = bytes(doc.contents).decode('utf-8')
    return json.loads(as_text, object_hook=frozen_node_decode_hook)


def tree_to_bytes(tree):
    encoder = FullNodeEncoder(sort_keys=True, indent=4)
    return encoder.encode(tree).encode('utf-8')     # as bytes


def save_tree(version, parent_doc):
    """Given a CFRVersion and the document of the version it builds off,
    compile a new version of the tree and save it"""
    notice = NoticeXML(version.source.xml())
    notice_changes = defaultdict(list)
    for amendment in notice.amendments:
        for label, change_list in amendment.get('changes', []):
            notice_changes[label].extend(change_list)
    prev_tree = doc_to_tree(parent_doc)
    new_tree = compile_regulation(prev_tree, notice_changes)
    version.doc = Document.objects.create(
        collection='gpo_cfr', label=new_tree.label[0],
        source=version.source, version=version, previous_document=parent_doc,
        contents=tree_to_bytes(new_tree))


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
def fill_with_rules(cfr_title, cfr_part):
    """Fill in missing trees using data from rules. When a regulation tree
    cannot be derived through annual editions, it must be built by parsing the
    changes in final rules. This command builds those missing trees"""
    logger.info("Fill with rules - %s CFR %s", cfr_title, cfr_part)

    for version, parent_version in build_pairs(cfr_title, cfr_part):
        save_tree(version, parent_version.doc)
