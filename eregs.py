import sys

import manage


def main():
    """Defer to manage.py"""
    args = ['manage.py', 'eregs'] + sys.argv[1:]
    manage.main(args)


if __name__ == '__main__':
    main()
