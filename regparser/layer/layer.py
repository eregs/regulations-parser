import abc
from collections import defaultdict, namedtuple


SearchReplace = namedtuple('SearchReplace',
                           ['text', 'locations', 'representative'])


class Layer(object):
    """Base class for all of the Layer generators. Defines the interface they
    must implement"""
    __metaclass__ = abc.ABCMeta

    def __init__(self, tree, cfr_title=None, version_id=None, notices=None,
                 version=None):
        self.tree = tree
        self.notices = notices or []
        self.cfr_title = cfr_title
        self.version_id = version_id
        self.version = version
        if version:
            self.version_id = version.identifier
        self.layer = {}

    def pre_process(self):
        """ Take the whole tree and do any pre-processing """
        pass

    @abc.abstractmethod
    def process(self, node):
        """ Construct the element of the layer relevant to processing the given
        node, so it returns (pargraph_id, layer_content) or None if there is no
        relevant information. """

        raise NotImplementedError()

    def builder(self, node, cache=None):
        if cache:
            layer_element = cache.fetch_or_process(self, node)
        else:
            layer_element = self.process(node)
        if layer_element:
            self.layer[node.label_id()] = layer_element

        for c in node.children:
            self.builder(c, cache)

    def build(self, cache=None):
        self.pre_process()
        self.builder(self.tree, cache)
        return self.layer

    @staticmethod
    def convert_to_search_replace(matches, text, start_fn, end_fn):
        """We'll often have a bunch of text matches based on offsets. To use
        the "search-replace" encoding (which is a bit more resilient to minor
        variations in text), we need to convert these offsets into "locations"
        -- i.e. of all of the instances of a string in this text, which should
        be matched. Yields `SearchReplace` tuples"""
        text_to_matches = defaultdict(list)
        for match in matches:
            text_to_matches[text[start_fn(match):end_fn(match)]].append(match)

        for match_text, matches in text_to_matches.items():
            locations, location = [], 0
            idx = text.find(match_text)
            while idx != -1:
                if any(start_fn(match) == idx for match in matches):
                    locations.append(location)
                location += 1
                idx = text.find(match_text, idx + 1)

            yield SearchReplace(match_text, locations,
                                representative=matches[0])
