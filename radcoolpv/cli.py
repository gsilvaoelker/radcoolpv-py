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
    run_p.add_argument(
        "--case", action="append", metavar="NAME",
        help="Run only this case from a multi-case file. Repeatable.",
    )

    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            configs = config_module.load_cases(args.config)
        except ConfigError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.case:
            names = {cfg.case_name for cfg in configs}
            unknown = [n for n in args.case if n not in names]
            if unknown:
                print(f"error: no such case {unknown}; the file defines "
                      f"{sorted(names)}", file=sys.stderr)
                return 2
            configs = [cfg for cfg in configs if cfg.case_name in args.case]

        # One failing case must not cost the student the others. A multi-case
        # file typically mixes cases that need a compiled S4 with cases that do
        # not, and without S4 the first kind would otherwise abort the run
        # before any of the second kind executed.
        failed = []
        for cfg in configs:
            if len(configs) > 1:
                print(f"\n=== case: {cfg.case_name} ===")
            if args.print_config:
                pipeline.print_resolved(cfg)
                continue
            try:
                pipeline.run(cfg)
            except Exception as exc:
                if len(configs) == 1:
                    raise
                failed.append((cfg.case_name, exc))
                print(f"[skipped] {cfg.case_name}: {exc}", file=sys.stderr)

        if failed:
            print(f"\n{len(configs) - len(failed)} of {len(configs)} cases "
                  f"completed. Not run:", file=sys.stderr)
            for name, exc in failed:
                print(f"  {name}: {str(exc).splitlines()[0]}", file=sys.stderr)
            return 1
        return 0

    parser.error("unknown command")  # pragma: no cover
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
