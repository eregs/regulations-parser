import os
import sys

from click import ClickException


def runner(argv):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                          "regparser.web.settings.dev")

    from django.core.management import execute_from_command_line

    try:
        execute_from_command_line(argv)
    except ClickException as e:
        e.show()
        sys.exit(e.exit_code)


def eregs():
    args = ['manage.py', 'eregs'] + sys.argv[1:]
    runner(args)
