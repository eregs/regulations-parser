class NodeAccessor(object):
    """Wrapper class around a node that allows us to navigate the tree via
    dictionary access"""
    def __init__(self, node):
        self.node = node
        self.child_labels = [c.label[-1] for c in node.children]
        self._memoized = {}

    def __getattr__(self, name):
        """Pass through to self.node"""
        return getattr(self.node, name)

    def __getitem__(self, label):
        """Access child labels as a dictionary. node['111']['a']['2'] would
        access the node with label '111-a-2'"""
        if label in self._memoized:
            return self._memoized[label]
        else:
            for child in self.node.children:
                if child.label[-1] == label:
                    return NodeAccessor(child)
        raise KeyError()
