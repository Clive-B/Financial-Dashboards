#!/usr/bin/env python3
import os
import sys


def read_env():
    try:
        with open(os.path.join(os.path.dirname(__file__), ".env")) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("=", 1)
                if len(parts) == 2:
                    key, val = parts
                    key = key.strip()
                    val = val.strip()
                    if key not in os.environ:
                        os.environ[key] = val
    except IOError:
        pass


def main():
    read_env()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
