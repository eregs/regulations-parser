from datetime import date

import pytest

from regparser.history.versions import Version
from regparser.index import entry


@pytest.mark.django_db
def test_iterator():
    """Versions should be correctly linearized"""
    path = entry.Version("12", "1000")
    v1 = Version('1111', effective=date(2004, 4, 4),
                 published=date(2004, 4, 4))
    v2 = Version('2222', effective=date(2002, 2, 2),
                 published=date(2004, 4, 4))
    v3 = Version('3333', effective=date(2004, 4, 4),
                 published=date(2003, 3, 3))
    (path / '1111').write(v1)
    (path / '2222').write(v2)
    (path / '3333').write(v3)

    actual = [child.path[-1] for child in path.sub_entries()]

    assert ['2222', '3333', '1111'] == actual
