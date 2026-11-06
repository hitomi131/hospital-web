"""Convenience entry point for the Django hospital website.

Run ``python app.py`` after installing the project dependencies and setting
the local development environment described in README.md.
"""

import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_web.settings')
    from django.core.management import execute_from_command_line

    arguments = sys.argv[1:] or ['runserver']
    execute_from_command_line(arguments)


if __name__ == '__main__':
    main()
