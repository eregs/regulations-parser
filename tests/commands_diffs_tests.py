from contextlib import contextmanager
from datetime import timedelta
from unittest import TestCase

import pytest
import six
from click.testing import CliRunner
from django.utils import timezone

from regparser.commands.diffs import diffs
from regparser.index import entry
from regparser.tree.struct import Node
from regparser.web.index.models import Entry as DBEntry


@pytest.mark.django_db
class CommandsDiffsTests(TestCase):
    @contextmanager
    def integration_setup(self):
        self.cli = CliRunner()
        with self.cli.isolated_filesystem():
            self.tree_dir = entry.Tree('12', '1000')
            self.diff_dir = entry.Diff('12', '1000')
            (self.tree_dir / 'v1').write(Node(text='V1V1V1', label=['1000']))
            (self.tree_dir / 'v2').write(Node(text='V2V2V2', label=['1000']))
            yield

    def assert_diff_keys(self, lhs_id, rhs_id, keys):
        entry = self.diff_dir / lhs_id / rhs_id
        six.assertCountEqual(self, keys, entry.read().keys())

    def test_diffs_generated(self):
        """Diffs are calculated -- they will be empty between the same
        version, though"""
        with self.integration_setup():
            self.cli.invoke(diffs, ['12', '1000'])

            self.assert_diff_keys('v1', 'v1', [])
            self.assert_diff_keys('v2', 'v2', [])
            self.assert_diff_keys('v1', 'v2', ['1000'])
            self.assert_diff_keys('v2', 'v1', ['1000'])

    def test_diffs_regeneration(self):
        """Diffs won't get recalculated if their underlying tree hasn't
        changed"""
        with self.integration_setup():
            self.cli.invoke(diffs, ['12', '1000'])
            # change the output
            (self.diff_dir / 'v1' / 'v2').write({'update': 'update'})
            # this *won't* recalculate the output; input trees haven't changed
            self.cli.invoke(diffs, ['12', '1000'])

            self.assert_diff_keys('v1', 'v2', ['update'])

            # declare an input tree stale
            label_id = str(self.tree_dir / 'v1')
            new_time = timezone.now() + timedelta(hours=1)
            DBEntry.objects.filter(label_id=label_id).update(modified=new_time)
            self.cli.invoke(diffs, ['12', '1000'])
            self.assert_diff_keys('v1', 'v2', ['1000'])
