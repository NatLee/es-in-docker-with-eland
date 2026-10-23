#!/usr/bin/env python3
"""Create local configuration with random secrets; never overwrite an existing file."""

import argparse
import os
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[1]
SECRET_KEYS = (
    "ELASTIC_PASSWORD", "KIBANA_PASSWORD", "KIBANA_SECURITY_KEY",
    "KIBANA_SAVED_OBJECTS_KEY", "KIBANA_REPORTING_KEY",
)


def init_env(output: Path) -> None:
    template = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in SECRET_KEYS:
        template = template.replace(f"{key}=\n", f"{key}={secrets.token_hex(24)}\n")
    # O_EXCL also guards against races and existing symlinks. No secrets printed.
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as config:
        config.write(template)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".env")
    args = parser.parse_args()
    try:
        init_env(args.output)
    except FileExistsError:
        parser.exit(1, f"{args.output} already exists; left unchanged. Use --output .env.v9 for a separate configuration.\n")
    print(f"Created {args.output}. Review ports and versions before starting Docker.")


if __name__ == "__main__":
    main()
