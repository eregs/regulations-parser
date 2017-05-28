# vim: set encoding=utf-8
from datetime import date
from unittest import TestCase

from regparser.history.versions import Version
from regparser.layer.meta import Meta
from regparser.tree.struct import Node
from regparser.web.settings import parser as settings


class LayerMetaTest(TestCase):
    def setUp(self):
        self.old_meta = settings.META
        settings.META = {}

    def tearDown(self):
        settings.META = self.old_meta

    def test_process_cfr(self):
        m = Meta(None, cfr_title=3, version=None)
        result = m.process(Node(label=['a']))
        self.assertEqual(1, len(result))
        self.assertTrue('cfr_title_number' in result[0])
        self.assertEqual(3, result[0]['cfr_title_number'])
        self.assertTrue('cfr_title_text' in result[0])
        self.assertEqual('The President', result[0]['cfr_title_text'])

    def test_process_effective_date(self):
        """The effective date is derived from a Version object"""
        version = Version('v1', date(2004, 4, 4), date(2004, 4, 4))
        m = Meta(None, cfr_title=8, version=version)
        result = m.process(Node(label=['a']))
        self.assertEqual(1, len(result))
        self.assertEqual('2004-04-04', result[0].get('effective_date'))

    def test_process_extra(self):
        settings.META = {'some': 'setting', 'then': 42}
        m = Meta(None, cfr_title=19, version=None)
        result = m.process(Node(label=['a']))
        self.assertEqual(1, len(result))
        self.assertTrue('some' in result[0])
        self.assertEqual('setting', result[0]['some'])
        self.assertTrue('then' in result[0])
        self.assertEqual(42, result[0]['then'])

    def test_process_not_root(self):
        m = Meta(None, cfr_title=19, version=None)
        result = m.process(Node(label=['111', '22']))
        self.assertEqual(None, result)

    def test_process_statutory_letter(self):
        m = Meta(None, cfr_title=19, version=None)
        result = m.process(Node(label=['1111']))
        self.assertFalse('statutory_name' in result[0])
        self.assertFalse('reg_letter' in result[0])

        result = m.process(Node(label=['1111'],
                           title=u"PART 1111—RAGGEDY REG (REGULATION R)"))
        self.assertEqual('RAGGEDY REG', result[0]['statutory_name'])
        self.assertEqual('R', result[0]['reg_letter'])
