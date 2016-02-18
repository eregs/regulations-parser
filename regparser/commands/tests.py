import click
import requests_cache
from stevedore import extension
from stevedore.exception import NoMatches


def get_stevedore_module_names(namespace):
    names = []

    def extension_adder(ext):
        if len(ext.entry_point.attrs) == 0:  # account for case without :
            test_name = ext.entry_point.module_name
        else:
            test_name = ext.entry_point_target
        names.append(test_name)

    try:
        stevedore_mgr = extension.ExtensionManager(
            namespace=namespace, invoke_on_load=False)
        stevedore_mgr.map(extension_adder)
    except NoMatches:
        pass

    return names


@click.command()
def tests():
    import nose

    mymods = ["", "tests"]  # nose essentially ignores the first arg to argv.
    mymods.extend(get_stevedore_module_names("eregs_ns.parser.test_suite"))

    requests_cache.uninstall_cache()

    nose.run(argv=mymods)

if __name__ == '__main__':
    tests()
