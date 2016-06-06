from collections import OrderedDict, defaultdict

from importlib import import_module

from stevedore import extension
from stevedore.exception import NoMatches


def extend_list(namespace, original_list):
    """Use the plugin manager to tack on extra entries to a list of strings"""
    try:
        results = list(original_list)   # shallow copy
        mgr = extension.ExtensionManager(namespace=namespace,
                                         invoke_on_load=False)
        mgr.map(lambda ext: results.append(ext.entry_point_target))
        return results
    except NoMatches:
        return original_list


def update_dictionary(namespace, original):
    """
        Use the extension manager to update a dictionary.
        Assumes the keys are strings and the values are lists.
    """
    def handle_plugin(ext):
        # Because the extension is not a class, we can just access ext.plugin
        plugin = ext.plugin
        if not isinstance(plugin, dict):
            raise Exception("Plugin must be a dict: %s", plugin)
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


def class_paths_to_classes(class_paths):
    """We use an idiom of a list of class paths relatively often. This
    function will convert that list into the appropriate classes"""
    results = []
    for class_path in class_paths:
        split_char = ':' if ':' in class_path else '.'
        mod_string, class_name = class_path.rsplit(split_char, 1)
        mod = import_module(mod_string)
        results.append(getattr(mod, class_name))
    return results


def classes_by_shorthand(class_paths):
    """We often give our plugin entities specific names, indicated by their
    "shorthand" field. This creates an (ordered) dictionary, mapping the
    constructed classes by their shorthand name"""
    return OrderedDict([(cls.shorthand, cls)
                        for cls in class_paths_to_classes(class_paths)])
