from __future__ import annotations

import argparse
import json

from .db import init_db
from .health import status


def main() -> None:
    parser = argparse.ArgumentParser(prog="youtubarr")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("doctor")
    args = parser.parse_args()
    init_db()
    if args.command == "doctor":
        report = status()
        print(json.dumps(report, indent=2))
        raise SystemExit(0 if report["ok"] else 1)
    parser.print_help()


if __name__ == "__main__":
    main()
