import os


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                          "regparser.web.settings.dev")

    from regparser.web.management.commands.eregs import cli

    cli.main()


if __name__ == '__main__':
    main()
