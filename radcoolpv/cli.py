"""Command-line entry point: ``radcoolpv run config.yaml``."""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from . import config as config_module
from . import pipeline
from .config import ConfigError


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="radcoolpv",
        description="YAML-driven radiative-cooling photovoltaics simulator.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run a simulation from a YAML config.")
    run_p.add_argument("config", help="Path to the YAML configuration file.")
    run_p.add_argument(
        "--print-config", action="store_true",
        help="Parse and print the resolved settings, then exit (no computation).",
    )

    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            configs = config_module.load_cases(args.config)
        except ConfigError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        for cfg in configs:
            if len(configs) > 1:
                print(f"\n=== case: {cfg.case_name} ===")
            if args.print_config:
                pipeline.print_resolved(cfg)
            else:
                pipeline.run(cfg)
        return 0

    parser.error("unknown command")  # pragma: no cover
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
