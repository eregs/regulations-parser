import json
from collections import namedtuple
from datetime import datetime

from regparser.notice.citation import Citation


class Version(namedtuple('Version',
                         ['identifier', 'effective', 'fr_citation'])):
    @property
    def is_final(self):
        return bool(self.effective)

    @property
    def is_proposal(self):
        return not self.is_final

    def json(self):
        result = {'identifier': self.identifier,
                  'fr_citation': self.fr_citation.asdict()}
        if self.is_final:
            result['effective'] = self.effective.isoformat()

        return json.dumps(result)

    @staticmethod
    def from_json(json_str):
        json_dict = json.loads(json_str)
        effective = json_dict.get('effective')
        if effective:
            effective = datetime.strptime(effective, '%Y-%m-%d').date()
        return Version(json_dict['identifier'], effective,
                       Citation(**json_dict['fr_citation']))

    def __lt__(self, other):
        """Linearizing versions requires knowing not only relevant dates and
        identifiers, but also which versions are from final rules and which
        are just proposals"""
        if self.is_final and other.is_final:
            left = (self.effective, self.fr_citation, self.identifier)
            right = (other.effective, other.fr_citation, other.identifier)
            return left < right
        else:   # at least one of the two is a proposal
            left = (self.fr_citation, self.identifier)
            right = (other.fr_citation, other.identifier)
            return left < right

    @staticmethod
    def parents_of(versions):
        """A "parent" of a version is the version which it builds atop.
        Versions can only build on final versions. Assume the versions are
        already sorted"""
        current_parent = None
        for version in versions:
            yield current_parent
            if version.is_final:
                current_parent = version
