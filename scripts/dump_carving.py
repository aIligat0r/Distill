"""
URL Carving from Memory Dump via FSM
Supports: ASCII, UTF-16LE (Windows), raw bytes with context
"""

from sys import argv
import mmap
import re
from typing import Iterator

from distill import StreamingLineExtractor, RuleBuilder


# ==================== 1. Extracting strings from a dump ====================


def extract_ascii_strings(data: bytes, min_len: int = 4) -> Iterator[tuple[int, str]]:
    """Extracts ASCII strings (32-126) with their offsets."""
    pattern = re.compile(rb"[\x20-\x7e]{" + str(min_len).encode() + rb",}")
    for m in pattern.finditer(data):
        yield m.start(), m.group(0).decode("ascii")


def extract_utf16le_strings(data: bytes, min_len: int = 4) -> Iterator[tuple[int, str]]:
    """
    Extracts UTF-16LE strings (Windows-style).
    Searches for [ASCII][\x00][ASCII][\x00]...
    """
    pattern = re.compile(rb"(?:[\x20-\x7e]\x00){" + str(min_len).encode() + rb",}")
    for m in pattern.finditer(data):
        raw = m.group(0)
        text = raw.decode("utf-16le", errors="ignore")
        yield m.start(), text


def extract_strings_from_dump(path: str) -> Iterator[tuple[int, str, str]]:
    """
    Generator: (offset, encoding, string)
    Processes the dump via mmap — O(1) memory.
    """
    with open(path, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

        # ASCII
        for off, s in extract_ascii_strings(mm):
            yield off, "ascii", s

        # UTF-16LE
        for off, s in extract_utf16le_strings(mm):
            yield off, "utf16le", s

        mm.close()


# ==================== 2. Rules for URL ====================

# Rules for StreamingLineExtractor (work on extracted lines)

RULES = [
    # --- Scenario 1: URL in key=value style config ---
    {
        "rule_name": "url_in_config",
        "rules": {
            "key": {
                "pattern": r"^(?P<key>[A-Za-z_]+)\s*[=:]\s*",
                "extract_groups": True,
            },
            "url": {"pattern": r"(?P<url>https?://[^\s\"<>]+)", "extract_groups": True},
            "trash": {"pattern": r".*", "store": False, "optional": True},
        },
    },
    # --- Scenario 2: JSON Debris in Memory ---
    {
        "rule_name": "url_in_json",
        "rules": {
            "prefix": {"pattern": r'^"?url"?\s*[:=]\s*["\']?', "store": False},
            "url": {"pattern": r"(?P<url>https?://[^\s\"<>]+)", "extract_groups": True},
            "suffix": {"pattern": r'["\']?.*', "store": False, "optional": True},
        },
    },
    # --- Scenario 3: Simple URL (clean, no context) ---
    {
        "rule_name": "url_plain",
        "pattern": r"(?P<url>https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(?:/[^\s\"<>]*)?)",
        "match_mode": "search",
        "extract_groups": True,
    },
    # --- Scenario 4: C2-style (host, server, c2) ---
    {
        "rule_name": "c2_url",
        "rules": {
            "label": {
                "pattern": r"^(?i:host|server|c2|address|gateway)[\s:=]+",
                "store": False,
            },
            "url": {"pattern": r"(?P<url>https?://[^\s\"<>]+)", "extract_groups": True},
        },
    },
    # --- Scenario 5: URL with credentials (e.g. in browser/FTP client memory) ---
    {
        "rule_name": "url_with_creds",
        "rules": {
            "proto": {"pattern": r"^(?P<proto>https?)://", "extract_groups": True},
            "user": {"pattern": r"(?P<user>[^\s:@]+)", "extract_groups": True},
            "sep1": {"pattern": r":", "store": False},
            "pass": {"pattern": r"(?P<password>[^\s@]+)", "extract_groups": True},
            "at": {"pattern": r"@", "store": False},
            "host": {"pattern": r"(?P<host>[a-zA-Z0-9\-\.]+)", "extract_groups": True},
            "uri": {
                "pattern": r"(?P<uri>/[^\s\"]*)?",
                "extract_groups": True,
                "optional": True,
            },
        },
    },
]


# ==================== 3. Launch ====================

if __name__ == "__main__":
    DUMP_PATH = argv[1]  # <-- memory dump

    parser = StreamingLineExtractor(RuleBuilder.lines(RULES))

    print("=== URL Carving from Memory Dump ===\n")

    for offset, encoding, text in extract_strings_from_dump(DUMP_PATH):
        for res in parser.parse_stream(iter([text + "\n"])):
            url = res.matches.get("url")
            if url:
                print(
                    f"[{res.rule_name:20}] offset=0x{offset:08x} ({encoding:8}) | {url}"
                )
