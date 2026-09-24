#!/usr/bin/env python3
"""Rebuild index/cycle_info.json from the first pages of each volume.

Run this after changing how cycle labels are formatted:

    python scripts/refresh_cycle_info.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cycle_info import refresh_all


def main():
    labels = refresh_all()
    print(f"Wrote {len(labels)} cycle labels to index/cycle_info.json")


if __name__ == '__main__':
    main()
