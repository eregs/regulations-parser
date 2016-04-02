"""This will be deleted soon -- we just need to migrate atf-eregs and
fec-eregs to use NodeAccessor directly"""
from regparser.test_utils.node_accessor import NodeAccessor


class NodeAccessorMixin(object):
    """Mix in to tests to setup and test a root"""
    def node_accessor(self, root, root_label):
        self.assertEqual(root.label, root_label)
        return NodeAccessor(root)
