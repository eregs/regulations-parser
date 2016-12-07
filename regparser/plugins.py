from collections import defaultdict

from stevedore import extension
from stevedore.exception import NoMatches


def update_dictionary(namespace, original):
    """
        Use the extension manager to update a dictionary.
        Assumes the keys are strings and the values are lists.
    """
    def handle_plugin(ext):
        # Because the extension is not a class, we can just access ext.plugin
        plugin = ext.plugin
        assert isinstance(plugin, dict)
        for key in plugin:
            original[key].extend(plugin[key])

    original = defaultdict(list, original)

    try:
        mgr = extension.ExtensionManager(namespace=namespace,
                                         invoke_on_load=False)
        mgr.map(handle_plugin)
        return dict(original)
    except NoMatches:
        return dict(original)
