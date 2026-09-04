#!/usr/bin/env python3
"""Validate social-copy character ceilings for a J33 blog promo kit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


LIMITS = {"instagram": 2200, "linkedin": 3000, "x": 280}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", type=Path)
    args = parser.parse_args()

    data = json.loads(args.json_file.read_text(encoding="utf-8"))
    failed = False
    for platform, limit in LIMITS.items():
        value = data.get(platform)
        if not isinstance(value, str) or not value.strip():
            print(f"FAIL {platform}: missing non-empty text")
            failed = True
            continue
        count = len(value)
        status = "OK" if count <= limit else "FAIL"
        print(f"{status} {platform}: {count}/{limit} characters")
        failed = failed or count > limit
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

