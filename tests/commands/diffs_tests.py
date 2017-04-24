import json

import pytest
from click.testing import CliRunner
from model_mommy import mommy

from regparser.commands import diffs
from regparser.web.index.models import CFRVersion, Diff, Document


@pytest.fixture
def two_versions():
    v1 = mommy.make(CFRVersion, identifier='v1', cfr_title=11, cfr_part=222)
    v2 = mommy.make(CFRVersion, identifier='v2', cfr_title=11, cfr_part=222)
    v1_content = dict(
        text="V1V1V1", children=[], label=["222"], title=None,
        node_type="regtext", source_xml=None, tagged_text="")
    v2_content = dict(v1_content)
    v2_content['text'] = "V2V2V2"
    mommy.make(Document, version=v1,
               contents=json.dumps(v1_content).encode('utf-8'))
    mommy.make(Document, version=v2,
               contents=json.dumps(v2_content).encode('utf-8'))


def diff_keys(left_id, right_id):
    diff = Diff.objects.get(left_document__version__identifier=left_id,
                            right_document__version__identifier=right_id)
    as_dict = json.loads(bytes(diff.contents).decode('utf-8'))
    return set(as_dict.keys())


@pytest.mark.django_db
@pytest.mark.usefixtures('two_versions')
def test_diffs_generated():
    """Diffs are calculated when needed"""
    assert Diff.objects.count() == 0

    CliRunner().invoke(diffs.diffs, ['11', '222'])

    assert Diff.objects.count() == 4
    assert diff_keys('v1', 'v1') == set()
    assert diff_keys('v1', 'v2') == {'222'}
    assert diff_keys('v2', 'v2') == set()
    assert diff_keys('v2', 'v1') == {'222'}
