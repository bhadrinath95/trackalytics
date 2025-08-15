#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import sys
from dotenv import load_dotenv 
from pathlib import Path
import os

def main():
    """Run administrative tasks."""
    DOT_ENV_PATH = Path(__file__).resolve().parent / '.env'
    if DOT_ENV_PATH.exists():
        load_dotenv(dotenv_path=DOT_ENV_PATH)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trackalytics.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
