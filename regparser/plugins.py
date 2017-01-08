import inspect
from collections import defaultdict

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


def instantiate_if_possible(namespace, method_name=None):
    """We'll sometimes want to mix pure functions with state-holding object
    instances. This functions combines the two into a single interface."""
    extensions = []
    for extension in ExtensionManager(namespace):
        if inspect.isclass(extension.plugin) and method_name is None:
            # assume the plugin object is a callable
            extensions.append(extension.plugin())
        elif inspect.isclass(extension.plugin):
            extensions.append(getattr(extension.plugin(), method_name))
        else:
            extensions.append(extension.plugin)
    extensions = list(sorted(extensions,
                             key=lambda e: getattr(e, 'plugin_order', 0)))
    return extensions
