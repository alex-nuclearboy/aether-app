#!/usr/bin/env python
"""Command-line utility for the Aether Django project."""

import os
import sys


def main() -> None:
    """Run Django administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    try:
        # pylint: disable=import-outside-toplevel
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django could not be imported. Ensure the project dependencies "
            "are installed and the virtual environment is available."
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
