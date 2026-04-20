#!/usr/bin/env python3
"""
Distill CLI — command-line interface for FSM streaming parser.

Usage:
    python cli.py -i logs.txt -r rules.json -m block
    python cli.py -i data.csv -r rules.json -m line -o result.jsonl
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from src.distill import RuleBuilder, StreamingBlockParser, StreamingLineExtractor


def load_rules(path: Path) -> list[dict[str, Any]]:
    """
    Load rule configuration from JSON or Python file.

    JSON: must contain a single rule dict or a list of rule dicts.
    Python: must define a `RULES` variable (dict or list).
    """
    suffix = path.suffix.lower()

    if suffix == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [raw] if isinstance(raw, dict) else raw

    if suffix in (".py", ".pyw"):
        spec = importlib.util.spec_from_file_location("rules_module", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load Python rules from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, "RULES"):
            raise ValueError(f"Python rules file must define 'RULES' variable: {path}")
        raw = getattr(module, "RULES")
        return [raw] if isinstance(raw, dict) else raw

    raise ValueError(f"Unsupported rules format: {suffix}. Use .json or .py")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="distill",
        description="FSM-driven streaming parser for structured text extraction.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i ssh.log -r ssh_rules.json -m block
  %(prog)s -i data.txt -r line_rules.json -m line -o out.jsonl
  cat huge.log | %(prog)s -r rules.json -m block
        """,
    )

    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=None,
        help="Path to input file (default: stdin)",
    )
    parser.add_argument(
        "-r",
        "--rules",
        type=Path,
        required=True,
        help="Path to rules config (.json or .py with RULES variable)",
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=["block", "line"],
        required=True,
        help="Parser mode: 'block' for multi-line blocks, 'line' for single-line rules",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output file (default: stdout). Writes JSON Lines format.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=None,
        help="JSON indent (pretty print). Default: compact single-line JSON.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Load rules
    try:
        raw_rules = load_rules(args.rules)
    except Exception as exc:
        print(f"[ERROR] Failed to load rules: {exc}", file=sys.stderr)
        return 1

    # Build rules
    try:
        if args.mode == "block":
            rules = RuleBuilder.blocks(raw_rules)
            parser = StreamingBlockParser(rules)
        else:
            rules = RuleBuilder.lines(raw_rules)
            parser = StreamingLineExtractor(rules)
    except Exception as exc:
        print(f"[ERROR] Invalid rule configuration: {exc}", file=sys.stderr)
        return 1

    # Open streams
    in_stream = open(args.input, "r", encoding="utf-8") if args.input else sys.stdin
    out_stream = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout

    try:
        count = 0
        for result in parser.parse_stream(in_stream):
            payload = {
                "rule": result.rule_name,
                "lines": [result.line_start, result.line_end],
                "matches": result.matches,
            }
            json.dump(payload, out_stream, ensure_ascii=False, indent=args.indent)
            out_stream.write("\n")
            count += 1

        if args.output:
            print(f"[OK] Parsed {count} results -> {args.output}", file=sys.stderr)
        else:
            print(f"[OK] Parsed {count} results", file=sys.stderr)

    except KeyboardInterrupt:
        print("\n[ABORT] Interrupted by user", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"[ERROR] Parsing failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if in_stream is not sys.stdin:
            in_stream.close()
        if out_stream is not sys.stdout:
            out_stream.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
