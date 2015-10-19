import abc


class Layer(object):
    """Base class for all of the Layer generators. Defines the interface they
    must implement"""
    __metaclass__ = abc.ABCMeta

    def __init__(self, tree, cfr_title=None, version_id=None, notices=None,
                 act_citation=None, version=None):
        self.tree = tree
        self.notices = notices or []
        self.act_citation = act_citation or []
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
