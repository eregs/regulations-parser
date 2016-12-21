from collections import defaultdict
import inspect

from stevedore.extension import ExtensionManager


def update_dictionary(namespace, original):
    """
        Use the extension manager to update a dictionary.
        Assumes the keys are strings and the values are lists.
    """
    result = defaultdict(list, original)

    for extension in ExtensionManager(namespace):
        assert isinstance(extension.plugin, dict)
        for key, value in extension.plugin.items():
            result[key].extend(value)
    return dict(result)


def instatiate_if_possible(namespace, method_name=None):
    """We'll sometimes want to mix pure functions with state-holding object
    instances. This functions combines the two into a single interface."""
    for extension in ExtensionManager(namespace):
        if inspect.isclass(extension.plugin) and method_name is None:
            # assume the plugin object is a callable
            yield extension.plugin()
        elif inspect.isclass(extension.plugin):
            yield getattr(extension.plugin(), method_name)
        else:
            yield extension.plugin
