from collections import namedtuple
import json


class Version(namedtuple('Version', ['identifier', 'published', 'effective'])):
    def json(self):
        return json.dumps({'identifier': self.identifier,
                           'published': self.published.isoformat(),
                           'effective': self.effective.isoformat()})
