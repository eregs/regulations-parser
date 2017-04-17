import json
import logging

import click

from regparser.diff.tree import changes_between
from regparser.tree.struct import frozen_node_decode_hook
from regparser.web.index.models import Diff, Document

logger = logging.getLogger(__name__)


def decode(doc):
    as_text = bytes(doc.contents).decode('utf-8')
    return json.loads(as_text, object_hook=frozen_node_decode_hook)


def encode(diff):
    encoder = json.JSONEncoder(sort_keys=True, indent=4)
    as_text = encoder.encode(diff)
    return as_text.encode('utf-8')     # as bytes


@click.command()
@click.argument('cfr_title', type=int)
@click.argument('cfr_part', type=int)
def diffs(cfr_title, cfr_part):
    """Construct diffs between known trees."""
    logger.info("Build diffs - %s Part %s", cfr_title, cfr_part)

    docs = Document.objects.select_related('version').filter(
        version__cfr_title=cfr_title, version__cfr_part=cfr_part)
    pairs = [(lhs, rhs) for lhs in docs for rhs in docs]
    trees = {}

    for lhs, rhs in pairs:
        lhs_id = lhs.version.identifier
        rhs_id = rhs.version.identifier
        if not Diff.objects.filter(left_document=lhs, right_document=rhs):
            if lhs_id not in trees:
                trees[lhs_id] = decode(lhs)
            if rhs_id not in trees:
                trees[rhs_id] = decode(rhs)

            diff = dict(changes_between(trees[lhs_id], trees[rhs_id]))
            Diff.objects.create(left_document=lhs, right_document=rhs,
                                contents=encode(diff))
