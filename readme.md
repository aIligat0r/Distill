# Distill

<div align="center">

[English](readme.md) | [Русский](readme.ru.md)
</div>

<div align="center">

![](assets/pic_gif.gif)
</div>

<div align="center">

**A parser based on finite automata**

[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style](https://img.shields.io/badge/formatted-blue?style=for-the-badge&logo=ruff&logoColor=white&label=ruff&color=%23d7ff64)](https://github.com/astral-sh/ruff)
</div>

---


## 📋 Content

- [🎯 Review](#-review)
- [✨ Features](#-features)
- [🚀 Quick start](#-quick-start)
    - [Installation](#installation)
- [🏗️ Architecture](#architecture)
    - [Main components](#main-components)
- [📚 Detailed documentation](#-detailed-documentation)
    - [🧱 Multi-line blocks (_StreamingBlockParser_)](#multi-line-blocks-streamingblockparser)
        - [Sequential Mode (strict order)](#sequential-mode-strict-order)
        - [Unordered Mode (arbitrary order)](#unordered-mode-arbitrary-order)
        - [Terminators](#terminators)
        - [Max Lines — protection from "hung" blocks](#max-lines--protection-from-hung-blocks)
        - [Rule Parameters _StreamingBlockParser_](#rule-parameters-streamingblockparser)
        - [BlockRule Operating Modes](#blockrule-operating-modes)
        - [⚠️ Terminator Features](#️-terminator-features)
        - [💡 Configuration examples _StreamingBlockParser_](#-configuration-examples-streamingblockparser)
            - [Sequential — receipt/order parsing](#sequential--receiptorder-parsing-strict-row-order)
            - [Unordered — application configuration (any order + terminator)](#unordered--application-configuration-any-order--terminator)
            - [Unordered — system metrics (optional fields)](#unordered--system-metrics-optional-fields)
            - [Sequential — IoT device parsing (skipping optional lines)](#sequential--iot-device-parsing-skipping-optional-lines)

    - [✎_ Parsing inside a string (_StreamingLineExtractor_)](#parsing-inside-a-string-streaminglineextractor)
        - [Simple one-line rules](#simple-one-line-rules)
        - [Rule Parameters (_StreamingLineExtractor_)](#rule-parameters-streaminglineextractor)
        - [Key differences from _StreamingBlockParser_](#key-differences-from-streamingblockparser)
        - [💡 Configuration examples _StreamingLineExtractor_](#-configuration-examples-streaminglineextractor)
            - [Example 1: Software version](#example-1-software-version)
            - [Example 2: Inventory Entry](#example-2-inventory-entry)
            - [Example 3: Coordinates](#example-3-coordinates)
- [💡 Usage examples](#-usage-examples)
    - [An example of extraction from a single line (_StreamingLineExtractor_)](#an-example-of-extraction-from-a-single-line-streaminglineextractor)
    - [An example of a block approach (_StreamingBlockParser_)](#an-example-of-a-block-approach-streamingblockparser)
- [🎮 CLI](#-cli)
- [🕵🏼‍♀️ Forensics](#️-forensics)
- [🔧 Requirements](#-requirements)

---

## 🎯 Review

**Distill** is a finite state machine parsing engine (FSM) designed for:

- **Streaming** large files with O(1) memory consumption
- **Extraction of structured data** from unstructured text streams
- **Multiline block parsing** with strict and non-strict order support
- **Sequential parsing of** tokens within a single string

**Suitable for**:
- Log files and system logs
- Configuration files
- Output of CLI commands
- ETL processes
- Forecasting and data analysis

---

# ✨ Features

| Opportunity | Description |
|-------------|----------|
| 🔄 **Sequential Mode** | Strict order of lines in the block — each line must follow in a given sequence |
| 🔀 **Unordered Mode** | The rows in the block can go in any order — flexible parsing of unstructured data |
| ⏹️ **Terminators** | Forced block completion by separator or reset in case of mismatch |
| 📏 **Max Lines** | Forced row limit — the block is reset if it is not completed in N rows |
| 🎯 **Match/Search Modes** | `match` (from the beginning of the line) or `search` (anywhere in the line) |
| 📝 **Group Extraction** | Automatic extraction of named groups from regex or saving the entire string |
| 🔄 **Streaming** | Streaming processing without loading the entire file into memory |
| ✅ **Validation** | Checking all the rules at startup — configuration errors are caught immediately |


# 🚀 Quick start

### Installation

```bash
# Cloning the repository
git clone https://github.com/yourusername/distill.git
cd Distill

pip install -e .

# Installation (no PyPI yet)
```

# 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Distill Architecture                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌──────────────┐      ┌──────────────┐      ┌─────────────────┐   │
│   │  Raw Text    │─────▶│  RuleBuilder │─────▶│  StreamingBlock │   │
│   │   Stream     │      │  (validate)  │      │     Parser      │   │
│   └──────────────┘      └──────────────┘      │  (LineExtractor)│   │
│                                               └────────┬────────┘   │
│                                                        │            │
│                               ┌────────────────────────┘            │
│                               ▼                                     │
│                    ┌─────────────────────┐                          │
│                    │     Finite State    │                          │
│                    │       Machines      │                          │
│                    ├────────────┬────────┤                          │
│                    │            │        │                          │
│             ┌──────▼───┐  ┌─────▼─────┐  │  ┌──────────────────┐    │
│             │ BlockFSM │  │ Unordered │  │  │ SequentialLine   │    │
│             │sequential│  │  BlockFSM │  │  │      FSM         │    │
│             └─────┬────┘  └─────┬─────┘  │  └────────┬─────────┘    │
│                   │             │        │           │              │
│                   └─────────────┴────────┴───────────┘              │
│                                 │                                   │
│                                 ▼                                   │
│                      ┌─────────────────────┐                        │
│                      │     MatchResult     │                        │
│                      │ (rule, matches,     │                        │
│                      │  line_start, end)   │                        │
│                      └─────────────────────┘                        │
│                                                                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Main components

| Component | Purpose |
| ------------------------ | ------------------------------------------------------- |
| `RuleBuilder`            | Factory for creating rules from dict configurations |
| `RuleValidator`          | Validation of configurations before creating an FSM |
| `BlockFSM`               | FSM for sequential parsing of multi-line blocks |
| `UnorderedBlockFSM`      | FSM for unordered block parsing |
| `SequentialLineFSM` | FSM for sequential token parsing in a string |
| `StreamingBlockParser` | Streaming parser for multi-line blocks |
| `StreamingLineExtractor` | Streaming parser for single-line rules |
| `MatchResult` | Result of parsing with metadata |


# 📚 Detailed documentation

### Multi-line blocks (StreamingBlockParser)
#### Sequential Mode (strict order)

In this mode, the lines in the block must **follow strictly** in the specified order.:

```python
# sample data
"""
PRICE: 10$
COUNT: 5
ID: a8a89cf1-9d0d-4b7c-92bd-7a62667f5664
======
PRICE: 10$
COUNT: 5
ID: a8a89cf1-9d0d-4b7c-92bd-7a62667f5664
COMMENT: Important
======

....

PRICE: 10$
COUNT: 5
ID: a8a89cf1-9d0d-4b7c-92bd-7a62667f5664
======
"""


config = {
    "rule_name": "logs_rule",
    "mode": "sequential",  # Strict order!
    "max_lines": 5,
    "rules": {
        "price":    {"pattern": r"^PRICE: (\d*)$"},
        "count":    {"pattern": r"^COUNT: (\d{3})$"},
        "id":       {"pattern": r"^ID: (.+)$"},
        "comment":  {"pattern": r"[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$", "optional": True}
    }
}
```

#### Behaviour:
1. The line "PRICE:" should be the first
2. The string "COUNT:" should be the second one.
3. The line "ID:" should be the third
4. If the order is broken, the block is reset and a new one begins.

### Unordered Mode (arbitrary order)
The lines can go in **any order**, but all the required ones must be present:
```python
config = {
    "rule_name": "server_config",
    "mode": "unordered",
    "max_lines": 20,
    "rules": {
        "host":     {"pattern": r"^HOST: (.+)$"},
        "port":     {"pattern": r"^PORT: (\d+)$"},
        "username": {"pattern": r"^USER: (.+)$"},
        "ssl":      {"pattern": r"^SSL: (true|false)$", "optional": True},
    }
}
```

#### Behavior:
1. The lines can go in any order
2. HOST, PORT, AND USER are required
3. SSL is optional
4. The block is finalized when all required fields are collected.

### Terminators

Terminators allow you to **forcibly end a block** when a certain line is encountered.:
```python
config = {
    "rule_name": "log_entry",
    "mode": "unordered",
    "max_lines": 50,
    "rules": {
        "timestamp": {"pattern": r"^\[(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\]"},
        "level":     {"pattern": r"^LEVEL: (INFO|WARN|ERROR)$"},
        "message":   {"pattern": r"^MSG: (.+)$"},
        "end":       {"pattern": r"^=+$", "store": False, "terminator": True},
    }
}
```

The logic of the terminator:
1. If all required fields are collected → finalize the block
2. If not all required data is collected → reset the block (invalid data)

Max Lines — protection from "stuck" blocks
```python
config = {
    "rule_name": "transaction",
    "mode": "sequential",
    "max_lines": 100,  # If the block is not assembled in 100 lines, it is reset.
    "rules": {
        # ... rules
    }
}
```

#### Behavior:
1. If the FSM is active for more than max_lines lines, force reset
2. Prevents endless waiting in case of corrupted data


#### Rule Parameters **StreamingBlockParser**
| Parameter | Type | Default | Description |
| ----------- | ------ | -------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `rule_name` | `str` | — | Unique name of the rule (block)                                                                                                    |
| `mode`      | `str`  | `sequential' | Block parsing mode: `sequential' (strict line order) or `unordered` (lines in any order)                           |
| `max_lines` | `int` | — | **Required**. The maximum number of lines that a block can occupy. If the block is not assembled in `N` lines, the FSM is reset |
| `rules`     | `dict` | — | Dictionary of string specifications `{name: spec}`. The order of the keys is important for the `sequential` mode |

Each element of the rules dictionary is a specification of a single line in a multi—line block.
| Parameter | Type | Default | Description |
| ---------------- | ------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`           | `str` | — | Unique string name (taken from dictionary key)                                                                                                                          |
| `pattern`        | `str` | — | Regex template for matching with a string |
| `optional`       | `bool` | `False` | Whether the string can be missing from the block. In `sequential`, it is skipped with an attempt to match the following specification. In `unordered' — not included in the required list |
| `extract_groups` | `bool` | `True`       | Extract `named groups` (`(?P<name>...)`) to the dictionary. If there are no named groups, `match.group(1)` (the first group) is taken. If there are no groups, the entire string is saved |
| `match_mode`     | `str`  | `"match"`    | `"match"` — matching from the beginning of the line (`pattern.match(line)`). `"search"` — search for a pattern anywhere in a line (`pattern.search(line)`)                               |
| `store`          | `bool` | `True`       | Whether to save the value in the final `matches'. If `False', the string is included in the block structure, but is not included in the result (for example, delimiters)                         |
| `terminator`     | `bool` | `False` | **Only for `unordered`**. If `True', if this string matches, the block is forcibly finalized (if all required ones are collected) or reset (if not collected) |

#### BlockRule Operating Modes
| Mode | Description | Mismatch behavior | `optional` behavior                                                                                        |
| ---------------- | ------------------------------------------------ | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| **`sequential`** | The lines must go **strictly in the specified order** | The block is reset, the parser tries to start a new block from the current line | The specification is skipped, an attempt is made to match the next one |
| **`unordered`**  | The lines can go in **any order**            | The line is skipped (we are waiting for another one), the block remains active | The field is not included in the required set. With `finalize_eof`, missing optional fields get `None' |

#### ⚠️ Terminator Features
| Situation | Result |
| -------------------------------------------------- | ------------------------------------------------------------ |
| `terminator: True` + all required fields have been collected | The block ** is being finalized** immediately |
| `terminator: True` + not all required data has been collected | The **block is being reset** (invalid data)                    |
| `terminator: True` in `sequential` mode | **Is ignored** (terminators only work in `unordered`) |


### 💡 Configuration examples **StreamingBlockParser**
#### Sequential — receipt/order parsing (strict row order)

Data:
```
ORDER# 1042
DATE: 2024-11-15
ITEM: Wireless Mouse MX3
QTY: 2
DISCOUNT: 10%
======
```

Rules:
```python
{
    "rule_name": "receipt",
    "mode": "sequential",
    "max_lines": 6,
    "rules": {
        "order_id":  {"pattern": r"^ORDER# (\d+)$"},
        "date":      {"pattern": r"^DATE: (\d{4}-\d{2}-\d{2})$"},
        "item":      {"pattern": r"^ITEM: (.+)$"},
        "qty":       {"pattern": r"^QTY: (\d+)$"},
        "discount":  {"pattern": r"^DISCOUNT: (\d+)%$", "optional": True},
        "separator": {"pattern": r"^={6,}$", "store": False}
    }
}
```
Result:
```python
{'order_id': 'ORDER# 1042', 'date': 'DATE: 2024-11-15', 'item': 'ITEM: Wireless Mouse MX3', 'qty': 'QTY: 2', 'discount': 'DISCOUNT: 10%'}
```

#### Unordered — application configuration (any order + terminator)
Data:
```
VERSION: 2.4.1
WORKERS: 8
APP_NAME: DataProcessor
LOG_LEVEL: INFO
[END]
```
Rules:
```python
{
    "rule_name": "app_config",
    "mode": "unordered",
    "max_lines": 15,
    "rules": {
        "app_name":    {"pattern": r"^APP_NAME: (.+)$"},
        "version":     {"pattern": r"^VERSION: (\d+\.\d+\.\d+)$"},
        "workers":     {"pattern": r"^WORKERS: (\d+)$"},
        "debug":       {"pattern": r"^DEBUG: (true|false)$", "optional": True},
        "log_level":   {"pattern": r"^LOG_LEVEL: (DEBUG|INFO|WARN|ERROR)$", "optional": True},
        "end_marker":  {"pattern": r"^\[END\]$", "store": False, "terminator": True}
    }
}
```
Result:
```python
{'version': 'VERSION: 2.4.1', 'workers': 'WORKERS: 8', 'app_name': 'APP_NAME: DataProcessor', 'log_level': 'LOG_LEVEL: INFO', 'debug': None}
```

#### Unordered — system metrics (optional fields)
Data:
```
TS: 1713456789
MEM: 42.5%
CPU: 12.3%
```
Rules:
```python
{
    "rule_name": "system_metrics",
    "mode": "unordered",
    "max_lines": 8,
    "rules": {
        "timestamp": {"pattern": r"^TS: (?P<ts>\d{10,13})$"},
        "cpu":       {"pattern": r"^CPU: (?P<cpu>\d+\.?\d*)%$"},
        "memory":    {"pattern": r"^MEM: (?P<memory>\d+\.?\d*)%$"},
        "disk":      {"pattern": r"^DISK: (?P<disk>\d+\.?\d*)%$", "optional": True},
        "network":   {"pattern": r"^NET: (?P<network>\d+)KB/s$", "optional": True}
    }
}
```
Result:
```python
{'timestamp': {'ts': '1713456789'}, 'memory': {'memory': '42.5'}, 'cpu': {'cpu': '12.3'}, 'network': None, 'disk': None}
```

#### Sequential — IoT device parsing (skipping optional lines)
Data (без humidity): 
```
DEVICE: A1B2C3D4
TEMP: 23.5C
PRESSURE: 1013hPa
CRC: 8F2A
```
Rules:
```python
{
    "rule_name": "sensor_reading",
    "mode": "sequential",
    "max_lines": 5,
    "rules": {
        "device_id": {"pattern": r"^DEVICE: ([A-Z0-9]{8})$"},
        "temp":      {"pattern": r"^TEMP: (-?\d+\.?\d*)C$"},
        "humidity":  {"pattern": r"^HUMIDITY: (\d+\.?\d*)%$", "optional": True},
        "pressure":  {"pattern": r"^PRESSURE: (\d+)hPa$", "optional": True},
        "checksum":  {"pattern": r"^CRC: ([A-F0-9]{4})$"}
    }
}
```

Result:
```python
{'device_id': 'DEVICE: A1B2C3D4', 'temp': 'TEMP: 23.5C', 'pressure': 'PRESSURE: 1013hPa', 'checksum': 'CRC: 8F2A'}
```


### Parsing inside a string (StreamingLineExtractor)
For parsing CSV (or similar formats), logs with a fixed structure, and other formats.:
```python
config = [
    {
        "rule_name": "csv_record",
        "strict_end": True,  # The string must end after the last token.
        "rules": {
            "domain":   {"pattern": r"^(?P<domain>(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]*),"},
            "username": {"pattern": r"(?P<username>[^,]+)$"},
        }
    }
]

rule = RuleBuilder.line(config)
parser = StreamingLineExtractor([rule])

# Parsing
data = "example.com,User123"
for result in parser.parse_stream([data]):
    print(result)
    # MatchResult(rule='csv_record', lines=0-0, keys=['domain', 'username'])
    print(result.rule_name, "-", result.matches)
    # csv_record - {'domain': {'domain': 'example.com'}, 'username': {'username': 'User123'}}
```

### Simple one-line rules
For easy data extraction from individual rows:
```python
config = {
    "rule_name": "email",
    "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "extract_groups": False,  # Save the entire line
    "match_mode": "match"
}

rule = RuleBuilder.line(config)
parser = StreamingLineExtractor([rule])
```


#### Rule Parameters (_StreamingLineExtractor_)

It is used when the config has the key `"pattern"` — one regular expression for the entire string.
| Parameter | Type | Default | Description |
| ---------------- | ------ | ------------ | ------------------------------------------------------------------------------------------------------------------------- |
| `rule_name`      | `str` | — | Unique name of the rule |
| `pattern`        | `str` | — | Regex template for matching with a string |
| `extract_groups` | `bool` | `True`       | Extract `named groups` (`(?P<name>...)`) to the dictionary. If there are no named groups, the entire string is saved with the key `"value"` |
| `match_mode`     | `str`  | `"match"`    | `"match"` — from the beginning of the string (`^...`), `"search"` — search anywhere |

It is used when the config has the `"rules"` key — sequential parsing of tokens inside one line from left to right.
| Parameter | Type | Default | Description |
| ------------ | ------ | ------------ | --------------------------------------------------------------------------------------------------------------------- |
| ` rule_name` | `str` | — | Unique rule name |
| `rules`      | `dict` | — | Dictionary of tokens `{name: spec}`. Key order = parsing order!                                                     |
| `strict_end` | `bool` | `True`       | If `True', the string must end with **strictly** after the last token. If `False', the tail of the string is ignored |

Each element of the rules dictionary in the SequentialLineRule is a token specification.
| Parameter | Type | Default | Description |
| ---------------- | ------ | ------------ | ------------------------------------------------------------------------------------------------------------------------ |
| `name`           | `str` | — | The unique name of the token (taken from the dictionary key)                                                                         |
| `pattern`        | `str` | — | Regex template for this token. For sequential, a `match' is recommended (from the current cursor position)                          |
| `optional`       | `bool` | `False` | Whether the token can be missing. If `True` is not found, `None` is written to the result.                                  |
| `extract_groups` | `bool` | `True`       | Extract `named groups'. If there are none, `match.group(1)` (the first group) is taken. If there are no groups, the entire text matches |
| `match_mode`     | `str`  | `"match"`    | For sequential, `match` is always used (matching with the current cursor position). `search` is not applicable |
| `store`          | `bool` | `True`       | Whether to save the token value in the final `matches'. If `False`, the token participates in parsing, but is not included in the result |
| `terminator`     | `bool` | `False`      | ⚠️ **Not used** in `StreamingLineExtractor' (works only in block parsers)                                  |

#### Key differences from **StreamingBlockParser**

| Feature | StreamingBlockParser | LineRule / SequentialLineRule |
| ------------ | ------------------------------ | ----------------------------- |
| ` max_lines`  | ✅ Yes | ❌ No (always one line)    |
| `mode`       | `"sequential"` / `"unordered"` | ❌ None |
| `terminator` | ✅ Is working | ❌ Is ignored |
| `optional`   | ✅ In sequential/unordered | ✅ Only in sequential |
| `strict_end` | ❌ No | ✅ Only in sequential |

### 💡 Configuration examples **StreamingLineExtractor**

#### Example 1: Software Version
Data:
```
v2.14.3-beta+20241115
v1.0.0
v3.5.2-alpha
invalid string
```

Rules:
```python
{
    "rule_name": "version_string",
    "strict_end": True,
    "rules": {
        "prefix": {"pattern": r"^v", "store": False},
        "major":  {"pattern": r"(\d+)"},
        "dot1":   {"pattern": r"\.", "store": False},
        "minor":  {"pattern": r"(\d+)"},
        "dot2":   {"pattern": r"\.", "store": False},
        "patch":  {"pattern": r"(\d+)"},
        "pre":    {"pattern": r"-([a-z]+)", "optional": True},
        "build":  {"pattern": r"\+(\d+)", "optional": True}
    }
}
```

Result:
```python
{'major': '2', 'minor': '14', 'patch': '3', 'pre': '-beta', 'build': '+20241115'}
{'major': '1', 'minor': '0', 'patch': '0', 'pre': None, 'build': None}
{'major': '3', 'minor': '5', 'patch': '2', 'pre': '-alpha', 'build': None}
```

#### Example 2: Inventory Entry
Data:
```
INV-2024-001 | 150 | Electronics | Warehouse-A
INV-2024-002 | 42 | | Warehouse-B
```

Rules:
```python
{
    "rule_name": "inventory_record",
    "strict_end": True,
    "rules": {
        "doc_id":   {"pattern": r"^INV-(\d{4}-\d{3})"},
        "sep1":     {"pattern": r" \| ", "store": False},
        "quantity": {"pattern": r"(\d+)"},
        "sep2":     {"pattern": r" \| ", "store": False},
        "category": {"pattern": r"([^|]+?) \| ", "store": True, "optional": True},
        "location": {"pattern": r"(\| )?(?P<loc>\S*)$"}  # именованный regex
    }
}
```

Result:
```python
{'doc_id': 'INV-2024-001', 'quantity': '150', 'category': 'Electronics | ', 'location': {'loc': 'Warehouse-A'}}
{'doc_id': 'INV-2024-002', 'quantity': '42', 'category': None, 'location': {'loc': 'Warehouse-B'}}
```

#### Example 3: Coordinates
Data:
```
55.7558, 37.6173, 144m
48.8566, 2.3522
-33.8688, 151.2093, 58m
```

Rules:
```python
{
    "rule_name": "coordinates",
    "strict_end": True,
    "rules": {
        "lat":      {"pattern": r"^(-?\d+\.\d+)"},
        "sep1":     {"pattern": r",\s*", "store": False},
        "lon":      {"pattern": r"(-?\d+\.\d+)"},
        "sep2":     {"pattern": r",\s*", "store": False},
        "altitude": {"pattern": r"(-?\d+\.?\d*)m", "optional": True}
    }
}
```

Result:
```python
{'lat': '55.7558', 'lon': '37.6173', 'altitude': '144'}
{'lat': '48.8566', 'lon': '2.3522', 'altitude': None}
{'lat': '-33.8688', 'lon': '151.2093', 'altitude': '58'}
```


# 💡 Usage examples

### An example of extraction from a single line (_StreamingLineExtractor_)

Sample data (file 'ssh_logs.txt'):
```txt
Dec 24 06:55:46 LabSZ sshd[24200]: pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost=12.13.14.15 
Dec 24 06:55:48 LabSZ sshd[24200]: Failed password for invalid user webmaster from 12.13.14.15 port 22 ssh2
Dec 24 06:55:48 LabSZ sshd[24200]: Connection closed by 12.13.14.15 [preauth]
...
```

Example of extracting **Username/IP/Port** Failed password connection attempts:
```python
config = {
    "rule_name": "ssh_log_failed_pass",
    "pattern": r"Failed password for invalid user (?P<username>\S+) from (?P<ip>\d+\.\d+\.\d+\.\d+) port (?P<port>\d+)",
    "extract_groups": True,
    "match_mode": "search"
}

rule = RuleBuilder.line(config)
parser = StreamingLineExtractor([rule])


with open("ssh_logs.txt") as ssh_log_file:
    for result in parser.parse_stream(ssh_log_file):
        print(result)
        print(result.rule_name, "-", result.matches)
        # out:
        # MatchResult(rule='ssh_log_failed_pass', lines=2-2, keys=['username', 'ip', 'port'])
        # ssh_log_failed_pass - {'username': 'webmaster', 'ip': '12.13.14.15', 'port': '22'}
```

### An example of a block approach (_StreamingBlockParser_)

```python
DATA = """
...

PRICE: 10$
COUNT: 5
ID: a8a89cf1-9d0d-4b7c-92bd-7a62667f5664
======
test strings ... 
...


...

/12321//ad/as/qwe/qw/eq/we/qwe/ qw qw - test strings

PRICE: 150$
COUNT: 10
ID: a8a89cf1-9d0d-4b7c-92bd-7a62667f5664
COMMENT: Important
======

....

PRICE: 5$
COUNT: 11
ID: a8a89cf1-9d0d-4b7c-92bd-7a62667f5664
======
    """.splitlines()

block_configs = [
    {
        "rule_name": "logs_rule",
        "mode": "sequential",  # Strict order!
        "max_lines": 5,
        "rules": {
            "price":    {"pattern": r"^PRICE: (\d*)\$$"},
            "count":    {"pattern": r"^COUNT: (\d*)$"},
            "id":       {"pattern": r"^ID: (\S*)$"},
            "comment":  {"pattern": r"^COMMENT: (.*)$", "optional": True}
        }
    }
]

parser = StreamingBlockParser(RuleBuilder.blocks(block_configs))
for res in parser.parse_stream(iter(DATA)):
    print(res.matches)
```
Result:
```json
{"price": "PRICE: 10$", "count": "COUNT: 5", "id": "ID: a8a89cf1-9d0d-4b7c-92bd-7a62667f5664"}
{"price": "PRICE: 150$", "count": "COUNT: 10", "id": "ID: a8a89cf1-9d0d-4b7c-92bd-7a62667f5664", "comment": "COMMENT: Important"}
{"price": "PRICE: 5$", "count": "COUNT: 11", "id": "ID: a8a89cf1-9d0d-4b7c-92bd-7a62667f5664"}"
```

#### Using named capture groups:
```python
block_configs = [
    {
        "rule_name": "logs_rule",
        "mode": "sequential",
        "max_lines": 5,
        "rules": {
            "price": {"pattern": r"^PRICE: (?P<price>\d*)\$$"},
            "count":  {"pattern": r"^COUNT: (?P<count>\d*)$"},
            "id": {"pattern": r"^ID: (?P<id>\S*)$"},
            "comment": {"pattern": r"^COMMENT: (?P<comment>.*)$", "optional": True}
        }
    }
]
```
Result:
```json
{"price": {"price": "10"}, "count": {"count": "5"}, "id": {"id": "a8a89cf1-9d0d-4b7c-92bd-7a62667f5664"}}
{"price": {"price": "150"}, "count": {"count": "10"}, "id": {"id": "a8a89cf1-9d0d-4b7c-92bd-7a62667f5664"}, "comment": {"comment": "Important"}}
{"price": {"price": "5"}, "count": {"count": "11"}, "id": {"id": "a8a89cf1-9d0d-4b7c-92bd-7a62667f5664"}}
```


# 🎮 CLI

Launch (after installation `pip install -e .`):
```bash
distill -i <path to file for parse> -r <rules file JSON> -m line -o <result JSONL>
```

Example:

Data file ( `/tmp/input.txt` ):
```txt
example.com,User123
example2.com,User1234
```

Rules file ( `/tmp/rules.json` ):
```json
[
    {
    "rule_name": "test_rule",
    "strict_end": true,
    "rules": {
        "domain":   {"pattern": "^(?P<domain>(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]*),"},
        "username": {"pattern": "(?P<username>[^,]+)$"}
    }
}
```

Launch:
```bash
$ distill -i /tmp/input.txt -r /tmp/rules.json -m line -o /tmp/distill_result.jsonl
# [OK] Parsed 2 results -> /tmp/distill_result.jsonl
```

Results:
```bash
$ cat /tmp/distill_result.jsonl

{"rule": "csv_record", "lines": [0, 0], "matches": {"domain": {"domain": "example.com"}, "username": {"username": "User123"}}}
{"rule": "csv_record", "lines": [1, 1], "matches": {"domain": {"domain": "example2.com"}, "username": {"username": "User1234"}}}
```


---
# 🕵🏼‍♀️ Forensics
### 📢❗🚨 Possibilities will be expanded in the future...

Example script for searching data in bytes (script - `/scripts/dump_carving.py`):
```bash
python scripts/dump_carving.py path/to/your/dump/pagefile.sys
```

Results:
```
=== URL Carving from Memory Dump ===

[url_plain           ] offset=0x00023ba8 (ascii   ) | http://crl.microsoft.com/pki/crl/prod
[url_plain           ] offset=0x00063661 (ascii   ) | https://jinohu.cc/
[url_plain           ] offset=0x000a2812 (ascii   ) | http://www.microsoft.com/pki/crl/products/MicCerTruLisPCA_2009-04-02.crlJ
[url_plain           ] offset=0x00111968 (ascii   ) | https://github.com/benjamin3346/playit/releases/S
[url_plain           ] offset=0x0011400b (ascii   ) | https://api.judicial.it.com/bypass_extreme_2_x86_fac0c5.exe'-outfile'%temp%\dian_sec1
```
---

<div align="right">

### Enjoying the tool? Drop a Star. Thanks and good luck!

</div>

---

# 🔧 Requirements
- Python 3.13+ (see also the versions below)
- Standard libraries only (no external dependencies)


---
# 📜 License

### MIT License
