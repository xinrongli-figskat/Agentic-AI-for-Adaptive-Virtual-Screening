"""Read-only integrity check; prints no hidden outcomes."""

import argparse
import json
from pathlib import Path

from oracle_boundary import verify_prepared


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-dir", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify_prepared(args.public_dir, args.private_dir), indent=2))


if __name__ == "__main__":
    main()
