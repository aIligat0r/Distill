"""
pytest tests for Lapidary
"""

from pathlib import Path
from typing import Any

import pytest

from src.distill import (
    BlockFSM,
    BlockRule,
    LineRule,
    LineSpec,
    MatchResult,
    RuleBuilder,
    RuleValidationError,
    RuleValidator,
    SequentialLineFSM,
    SequentialLineRule,
    StreamingBlockParser,
    StreamingLineExtractor,
    UnorderedBlockFSM,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sequential_block_config() -> dict[str, Any]:
    return {
        "rule_name": "receipt",
        "mode": "sequential",
        "max_lines": 5,
        "rules": {
            "order_id": {"pattern": r"^ORDER# (\d+)$"},
            "date": {"pattern": r"^DATE: (.+)$"},
            "total": {"pattern": r"^TOTAL: (\d+)\$$"},
        },
    }


@pytest.fixture
def unordered_block_config() -> dict[str, Any]:
    return {
        "rule_name": "server",
        "mode": "unordered",
        "max_lines": 10,
        "rules": {
            "host": {"pattern": r"^HOST: (.+)$"},
            "port": {"pattern": r"^PORT: (\d+)$"},
            "ssl": {"pattern": r"^SSL: (true|false)$", "optional": True},
            "end": {"pattern": r"^---$", "store": False, "terminator": True},
        },
    }


@pytest.fixture
def sequential_line_config() -> dict[str, Any]:
    return {
        "rule_name": "version",
        "strict_end": True,
        "rules": {
            "prefix": {"pattern": r"^v", "store": False},
            "major": {"pattern": r"(\d+)"},
            "dot1": {"pattern": r"\.", "store": False},
            "minor": {"pattern": r"(\d+)"},
            "patch": {"pattern": r"(\d+)", "optional": True},
        },
    }


@pytest.fixture
def simple_line_config() -> dict[str, Any]:
    return {
        "rule_name": "email",
        "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "extract_groups": False,
        "match_mode": "match",
    }


# ============================================================================
# RuleValidator
# ============================================================================


class TestRuleValidator:
    def test_validate_block_success(self, sequential_block_config: dict) -> None:
        RuleValidator.validate_block(sequential_block_config)

    def test_validate_block_missing_rule_name(self) -> None:
        with pytest.raises(RuleValidationError, match="rule_name"):
            RuleValidator.validate_block({"max_lines": 5, "rules": {}})

    def test_validate_block_empty_rule_name(self) -> None:
        with pytest.raises(RuleValidationError, match="rule_name"):
            RuleValidator.validate_block({"rule_name": "", "max_lines": 5, "rules": {}})

    def test_validate_block_missing_rules(self) -> None:
        with pytest.raises(RuleValidationError, match="rules"):
            RuleValidator.validate_block({"rule_name": "test", "max_lines": 5})

    def test_validate_block_empty_rules(self) -> None:
        with pytest.raises(RuleValidationError, match="rules"):
            RuleValidator.validate_block(
                {"rule_name": "test", "max_lines": 5, "rules": {}}
            )

    def test_validate_block_missing_max_lines(self) -> None:
        with pytest.raises(RuleValidationError, match="max_lines"):
            RuleValidator.validate_block(
                {"rule_name": "test", "rules": {"a": {"pattern": ".*"}}}
            )

    def test_validate_block_zero_max_lines(self) -> None:
        with pytest.raises(RuleValidationError, match="positive integer"):
            RuleValidator.validate_block(
                {"rule_name": "test", "max_lines": 0, "rules": {"a": {"pattern": ".*"}}}
            )

    def test_validate_block_invalid_mode(self) -> None:
        cfg = {
            "rule_name": "test",
            "mode": "invalid",
            "max_lines": 5,
            "rules": {"a": {"pattern": ".*"}},
        }
        with pytest.raises(RuleValidationError, match="mode"):
            RuleValidator.validate_block(cfg)

    def test_validate_block_duplicate_line_name(self) -> None:
        cfg = {
            "rule_name": "test",
            "max_lines": 5,
            "rules": {
                "a": {"pattern": ".*"},
                "b": {"pattern": ".*"},
            },
        }
        # no duplicate yet
        RuleValidator.validate_block(cfg)

        cfg["rules"]["a2"] = cfg["rules"]["a"]
        # still no duplicate names
        RuleValidator.validate_block(cfg)

    def test_validate_block_invalid_regex(self) -> None:
        cfg = {
            "rule_name": "test",
            "max_lines": 5,
            "rules": {"a": {"pattern": r"["}},
        }
        with pytest.raises(RuleValidationError, match="invalid regex"):
            RuleValidator.validate_block(cfg)

    def test_validate_block_invalid_match_mode(self) -> None:
        cfg = {
            "rule_name": "test",
            "max_lines": 5,
            "rules": {"a": {"pattern": ".*", "match_mode": "findall"}},
        }
        with pytest.raises(RuleValidationError, match="match_mode"):
            RuleValidator.validate_block(cfg)

    def test_validate_block_terminator_not_bool(self) -> None:
        cfg = {
            "rule_name": "test",
            "max_lines": 5,
            "rules": {"a": {"pattern": ".*", "terminator": "yes"}},
        }
        with pytest.raises(RuleValidationError, match="terminator"):
            RuleValidator.validate_block(cfg)

    def test_validate_line_simple_success(self, simple_line_config: dict) -> None:
        RuleValidator.validate_line(simple_line_config)

    def test_validate_line_sequential_success(
        self, sequential_line_config: dict
    ) -> None:
        RuleValidator.validate_line(sequential_line_config)

    def test_validate_line_missing_rule_name(self) -> None:
        with pytest.raises(RuleValidationError, match="rule_name"):
            RuleValidator.validate_line({"pattern": ".*"})

    def test_validate_line_neither_pattern_nor_rules(self) -> None:
        with pytest.raises(RuleValidationError, match="either 'rules'"):
            RuleValidator.validate_line({"rule_name": "test"})

    def test_validate_line_empty_rules(self) -> None:
        with pytest.raises(RuleValidationError, match="non-empty dict"):
            RuleValidator.validate_line({"rule_name": "test", "rules": {}})


# ============================================================================
# RuleBuilder
# ============================================================================


class TestRuleBuilder:
    def test_block_sequential(self, sequential_block_config: dict) -> None:
        rule = RuleBuilder.block(sequential_block_config)
        assert isinstance(rule, BlockRule)
        assert rule.name == "receipt"
        assert rule.mode == "sequential"
        assert rule.max_lines == 5
        assert len(rule.lines) == 3
        assert rule.lines[0].name == "order_id"
        assert rule.lines[0].optional is False

    def test_block_unordered(self, unordered_block_config: dict) -> None:
        rule = RuleBuilder.block(unordered_block_config)
        assert isinstance(rule, BlockRule)
        assert rule.mode == "unordered"
        assert len(rule.lines) == 4
        # terminator defaults to optional=True
        end_spec = next(s for s in rule.lines if s.name == "end")
        assert end_spec.terminator is True
        assert end_spec.optional is True
        assert end_spec.store is False

    def test_block_terminator_explicit_optional_false(self) -> None:
        cfg = {
            "rule_name": "t",
            "mode": "unordered",
            "max_lines": 5,
            "rules": {
                "a": {"pattern": r"^A$"},
                "end": {"pattern": r"^END$", "terminator": True, "optional": False},
            },
        }
        rule = RuleBuilder.block(cfg)
        end_spec = next(s for s in rule.lines if s.name == "end")
        assert end_spec.optional is False  # explicit override

    def test_blocks(self) -> None:
        configs = [
            {"rule_name": "a", "max_lines": 3, "rules": {"x": {"pattern": ".*"}}},
            {"rule_name": "b", "max_lines": 3, "rules": {"y": {"pattern": ".*"}}},
        ]
        rules = RuleBuilder.blocks(configs)
        assert len(rules) == 2
        assert rules[0].name == "a"
        assert rules[1].name == "b"

    def test_line_simple(self, simple_line_config: dict) -> None:
        rule = RuleBuilder.line(simple_line_config)
        assert isinstance(rule, LineRule)
        assert rule.name == "email"
        assert rule.pattern == simple_line_config["pattern"]

    def test_line_sequential(self, sequential_line_config: dict) -> None:
        rule = RuleBuilder.line(sequential_line_config)
        assert isinstance(rule, SequentialLineRule)
        assert rule.name == "version"
        assert rule.strict_end is True
        assert len(rule.lines) == 5
        assert rule.lines[0].store is False  # prefix

    def test_line_terminator_defaults_optional(self) -> None:
        cfg = {
            "rule_name": "csv",
            "strict_end": True,
            "rules": {
                "a": {"pattern": r"(\d+)"},
                "sep": {"pattern": r",", "store": False, "terminator": True},
            },
        }
        rule = RuleBuilder.line(cfg)
        assert isinstance(rule, SequentialLineRule)
        sep_spec = next(s for s in rule.lines if s.name == "sep")
        assert sep_spec.terminator is True
        assert sep_spec.optional is True  # default for terminator

    def test_lines(self) -> None:
        configs = [
            {"rule_name": "a", "pattern": r"^\d+$"},
            {"rule_name": "b", "strict_end": True, "rules": {"x": {"pattern": r"."}}},
        ]
        rules = RuleBuilder.lines(configs)
        assert len(rules) == 2
        assert isinstance(rules[0], LineRule)
        assert isinstance(rules[1], SequentialLineRule)


# ============================================================================
# BlockFSM (sequential)
# ============================================================================


class TestBlockFSM:
    def test_simple_match(self) -> None:
        rule = BlockRule(
            name="seq",
            lines=(
                LineSpec(name="a", pattern=r"^A: (.+)$"),
                LineSpec(name="b", pattern=r"^B: (.+)$"),
            ),
            max_lines=5,
            mode="sequential",
        )
        fsm = BlockFSM(rule)
        assert fsm.feed("A: hello", 0) is None
        res = fsm.feed("B: world", 1)
        assert isinstance(res, MatchResult)
        assert res.rule_name == "seq"
        assert res.matches == {"a": "A: hello", "b": "B: world"}
        assert res.line_start == 0
        assert res.line_end == 1

    def test_optional_skip(self) -> None:
        rule = BlockRule(
            name="seq",
            lines=(
                LineSpec(name="a", pattern=r"^A$"),
                LineSpec(name="b", pattern=r"^B$", optional=True),
                LineSpec(name="c", pattern=r"^C$"),
            ),
            max_lines=5,
            mode="sequential",
        )
        fsm = BlockFSM(rule)
        assert fsm.feed("A", 0) is None
        # skip optional B, match C immediately
        res = fsm.feed("C", 1)
        assert res is not None
        assert res.matches["a"] == "A"
        assert res.matches["b"] is None
        assert res.matches["c"] == "C"

    def test_wrong_order_resets(self) -> None:
        rule = BlockRule(
            name="seq",
            lines=(
                LineSpec(name="a", pattern=r"^A$"),
                LineSpec(name="b", pattern=r"^B$"),
            ),
            max_lines=5,
            mode="sequential",
        )
        fsm = BlockFSM(rule)
        assert fsm.feed("A", 0) is None
        # wrong line resets and tries to start new block
        assert fsm.feed("X", 1) is None
        # now A again should start
        assert fsm.feed("A", 2) is None
        res = fsm.feed("B", 3)
        assert res is not None
        assert res.line_start == 2

    def test_max_lines_reset(self) -> None:
        rule = BlockRule(
            name="seq",
            lines=(
                LineSpec(name="a", pattern=r"^A$"),
                LineSpec(name="b", pattern=r"^B$"),
            ),
            max_lines=2,
            mode="sequential",
        )
        fsm = BlockFSM(rule)
        assert fsm.feed("A", 0) is None
        # line 2 is beyond max_lines (0 -> 2 >= 2), resets
        assert fsm.feed("X", 2) is None
        # now can start fresh
        assert fsm.feed("A", 3) is None
        res = fsm.feed("B", 4)
        assert res is not None

    def test_store_false(self) -> None:
        rule = BlockRule(
            name="seq",
            lines=(
                LineSpec(name="a", pattern=r"^A$"),
                LineSpec(name="sep", pattern=r"^--$", store=False),
                LineSpec(name="b", pattern=r"^B$"),
            ),
            max_lines=5,
            mode="sequential",
        )
        fsm = BlockFSM(rule)
        assert fsm.feed("A", 0) is None
        assert fsm.feed("--", 1) is None
        res = fsm.feed("B", 2)
        assert "a" in res.matches
        assert "sep" not in res.matches
        assert "b" in res.matches

    def test_finalize_eof_with_optional(self) -> None:
        rule = BlockRule(
            name="seq",
            lines=(
                LineSpec(name="a", pattern=r"^A$"),
                LineSpec(name="b", pattern=r"^B$", optional=True),
            ),
            max_lines=5,
            mode="sequential",
        )
        fsm = BlockFSM(rule)
        assert fsm.feed("A", 0) is None
        # EOF: optional b can be missing
        res = fsm.finalize_eof()
        assert res is not None
        assert res.matches["a"] == "A"
        assert res.matches["b"] is None

    def test_finalize_eof_required_missing(self) -> None:
        rule = BlockRule(
            name="seq",
            lines=(
                LineSpec(name="a", pattern=r"^A$"),
                LineSpec(name="b", pattern=r"^B$"),
            ),
            max_lines=5,
            mode="sequential",
        )
        fsm = BlockFSM(rule)
        assert fsm.feed("A", 0) is None
        assert fsm.finalize_eof() is None

    def test_no_match_returns_none(self) -> None:
        rule = BlockRule(
            name="seq",
            lines=(LineSpec(name="a", pattern=r"^A$"),),
            max_lines=5,
            mode="sequential",
        )
        fsm = BlockFSM(rule)
        assert fsm.feed("B", 0) is None


# ============================================================================
# UnorderedBlockFSM
# ============================================================================


class TestUnorderedBlockFSM:
    def test_simple_unordered(self) -> None:
        rule = BlockRule(
            name="uns",
            lines=(
                LineSpec(name="x", pattern=r"^X: (.+)$"),
                LineSpec(name="y", pattern=r"^Y: (.+)$"),
            ),
            max_lines=5,
            mode="unordered",
        )
        fsm = UnorderedBlockFSM(rule)
        assert fsm.feed("Y: second", 0) is None
        res = fsm.feed("X: first", 1)
        assert res is not None
        assert res.matches == {"x": "X: first", "y": "Y: second"}

    def test_optional_missing(self) -> None:
        rule = BlockRule(
            name="uns",
            lines=(
                LineSpec(name="x", pattern=r"^X$"),
                LineSpec(name="y", pattern=r"^Y$", optional=True),
            ),
            max_lines=5,
            mode="unordered",
        )
        fsm = UnorderedBlockFSM(rule)
        res = fsm.feed("X", 0)
        assert res is not None
        assert res.matches["x"] == "X"
        assert res.matches["y"] is None

    def test_terminator_finalize(self) -> None:
        rule = BlockRule(
            name="uns",
            lines=(
                LineSpec(name="x", pattern=r"^X$"),
                LineSpec(name="end", pattern=r"^END$", terminator=True, store=False),
            ),
            max_lines=5,
            mode="unordered",
        )
        fsm = UnorderedBlockFSM(rule)
        assert fsm.feed("X", 0) is None
        # terminator finalizes
        res = fsm.feed("END", 1)
        assert res is not None
        assert "x" in res.matches
        assert "end" not in res.matches  # store=False

    def test_terminator_store_true(self) -> None:
        rule = BlockRule(
            name="uns",
            lines=(
                LineSpec(name="x", pattern=r"^X$"),
                LineSpec(name="end", pattern=r"^END$", terminator=True, store=True),
            ),
            max_lines=5,
            mode="unordered",
        )
        fsm = UnorderedBlockFSM(rule)
        assert fsm.feed("X", 0) is None
        res = fsm.feed("END", 1)
        assert res is not None
        assert res.matches["end"] == "END"

    def test_terminator_resets_if_required_missing(self) -> None:
        rule = BlockRule(
            name="uns",
            lines=(
                LineSpec(name="x", pattern=r"^X$"),
                LineSpec(name="end", pattern=r"^END$", terminator=True, store=False),
            ),
            max_lines=5,
            mode="unordered",
        )
        fsm = UnorderedBlockFSM(rule)
        # END before X -> reset, no result
        assert fsm.feed("END", 0) is None
        assert fsm._active is False

    def test_terminator_waits_for_it(self) -> None:
        # If terminator exists, block should NOT finalize until terminator seen
        rule = BlockRule(
            name="uns",
            lines=(
                LineSpec(name="x", pattern=r"^X$"),
                LineSpec(name="y", pattern=r"^Y$", optional=True),
                LineSpec(name="end", pattern=r"^END$", terminator=True, store=False),
            ),
            max_lines=5,
            mode="unordered",
        )
        fsm = UnorderedBlockFSM(rule)
        # All required collected (x), but terminator exists -> wait
        assert fsm.feed("X", 0) is None
        # still waiting
        assert fsm.feed("Y", 1) is None
        # terminator comes -> finalize
        res = fsm.feed("END", 2)
        assert res is not None

    def test_no_terminator_finalizes_when_required_done(self) -> None:
        rule = BlockRule(
            name="uns",
            lines=(
                LineSpec(name="x", pattern=r"^X$"),
                LineSpec(name="y", pattern=r"^Y$", optional=True),
            ),
            max_lines=5,
            mode="unordered",
        )
        fsm = UnorderedBlockFSM(rule)
        res = fsm.feed("X", 0)
        assert res is not None  # immediately finalized

    def test_max_lines_reset(self) -> None:
        rule = BlockRule(
            name="uns",
            lines=(LineSpec(name="x", pattern=r"^X$"),),
            max_lines=2,
            mode="unordered",
        )
        fsm = UnorderedBlockFSM(rule)
        assert fsm.feed("A", 0) is None
        assert fsm.feed("B", 2) is None  # 2-0 >= 2 -> reset
        # can match now
        res = fsm.feed("X", 3)
        assert res is not None

    def test_unknown_lines_ignored(self) -> None:
        rule = BlockRule(
            name="uns",
            lines=(LineSpec(name="x", pattern=r"^X$"),),
            max_lines=5,
            mode="unordered",
        )
        fsm = UnorderedBlockFSM(rule)
        assert fsm.feed("garbage", 0) is None
        assert fsm.feed("more garbage", 1) is None
        res = fsm.feed("X", 2)
        assert res is not None


# ============================================================================
# SequentialLineFSM
# ============================================================================


class TestSequentialLineFSM:
    def test_simple_parse(self) -> None:
        rule = SequentialLineRule(
            name="ver",
            lines=(
                LineSpec(name="prefix", pattern=r"^v", store=False),
                LineSpec(name="major", pattern=r"(\d+)"),
                LineSpec(name="dot", pattern=r"\.", store=False),
                LineSpec(name="minor", pattern=r"(\d+)"),
            ),
            strict_end=True,
        )
        fsm = SequentialLineFSM(rule)
        res = fsm.parse("v2.14", 0)
        assert res is not None
        assert res.matches["major"] == "2"
        assert res.matches["minor"] == "14"
        assert "prefix" not in res.matches
        assert "dot" not in res.matches

    def test_strict_end_fail(self) -> None:
        rule = SequentialLineRule(
            name="ver",
            lines=(LineSpec(name="a", pattern=r"^A"),),
            strict_end=True,
        )
        fsm = SequentialLineFSM(rule)
        assert fsm.parse("AB", 0) is None

    def test_strict_end_false_allows_tail(self) -> None:
        rule = SequentialLineRule(
            name="ver",
            lines=(LineSpec(name="a", pattern=r"^A"),),
            strict_end=False,
        )
        fsm = SequentialLineFSM(rule)
        res = fsm.parse("ABC", 0)
        assert res is not None

    def test_optional_missing(self) -> None:
        rule = SequentialLineRule(
            name="ver",
            lines=(
                LineSpec(name="a", pattern=r"^v(\d+)"),
                LineSpec(name="b", pattern=r"-beta", optional=True),
            ),
            strict_end=True,
        )
        fsm = SequentialLineFSM(rule)
        res = fsm.parse("v1", 0)
        assert res is not None
        assert res.matches["a"] == "v1"
        assert res.matches["b"] is None

    def test_optional_present(self) -> None:
        rule = SequentialLineRule(
            name="ver",
            lines=(
                LineSpec(name="a", pattern=r"^v(\d+)"),
                LineSpec(name="b", pattern=r"-beta", optional=True),
            ),
            strict_end=True,
        )
        fsm = SequentialLineFSM(rule)
        res = fsm.parse("v1-beta", 0)
        assert res is not None
        assert res.matches["a"] == "v1"
        assert res.matches["b"] == "-beta"

    def test_required_missing_returns_none(self) -> None:
        rule = SequentialLineRule(
            name="ver",
            lines=(
                LineSpec(name="a", pattern=r"^A"),
                LineSpec(name="b", pattern=r"B"),
            ),
            strict_end=True,
        )
        fsm = SequentialLineFSM(rule)
        assert fsm.parse("AX", 0) is None

    def test_named_groups(self) -> None:
        rule = SequentialLineRule(
            name="coord",
            lines=(
                LineSpec(name="lat", pattern=r"^(?P<lat>-?\d+\.\d+)"),
                LineSpec(name="sep", pattern=r",", store=False),
                LineSpec(name="lon", pattern=r"(?P<lon>-?\d+\.\d+)"),
            ),
            strict_end=True,
        )
        fsm = SequentialLineFSM(rule)
        res = fsm.parse("55.7558,37.6173", 0)
        assert res is not None
        assert res.matches["lat"] == {"lat": "55.7558"}
        assert res.matches["lon"] == {"lon": "37.6173"}


# ============================================================================
# StreamingBlockParser
# ============================================================================


class TestStreamingBlockParser:
    def test_parse_stream_sequential(self) -> None:
        rule = RuleBuilder.block(
            {
                "rule_name": "r",
                "mode": "sequential",
                "max_lines": 5,
                "rules": {
                    "a": {"pattern": r"^A$"},
                    "b": {"pattern": r"^B$"},
                },
            }
        )
        parser = StreamingBlockParser([rule])
        lines = ["X", "A", "B", "A", "X", "A", "B"]
        results = list(parser.parse_stream(iter(lines)))
        assert len(results) == 2
        assert results[0].line_start == 1
        assert results[0].line_end == 2
        assert results[1].line_start == 5
        assert results[1].line_end == 6

    def test_parse_stream_unordered_with_terminator(self) -> None:
        rule = RuleBuilder.block(
            {
                "rule_name": "cfg",
                "mode": "unordered",
                "max_lines": 10,
                "rules": {
                    "host": {"pattern": r"^HOST: (.+)$"},
                    "port": {"pattern": r"^PORT: (\d+)$"},
                    "end": {"pattern": r"^END$", "store": False, "terminator": True},
                },
            }
        )
        parser = StreamingBlockParser([rule])
        lines = [
            "PORT: 8080",
            "HOST: localhost",
            "END",
            "HOST: other",
            "PORT: 9090",
            "END",
        ]
        results = list(parser.parse_stream(iter(lines)))
        assert len(results) == 2
        assert results[0].matches["host"] == "HOST: localhost"
        assert results[0].matches["port"] == "PORT: 8080"
        assert results[1].matches["host"] == "HOST: other"

    def test_parse_stream_eof_finalize(self) -> None:
        rule = RuleBuilder.block(
            {
                "rule_name": "cfg",
                "mode": "unordered",
                "max_lines": 10,
                "rules": {
                    "x": {"pattern": r"^X$"},
                },
            }
        )
        parser = StreamingBlockParser([rule])
        lines = ["X"]
        results = list(parser.parse_stream(iter(lines)))
        assert len(results) == 1
        assert results[0].matches["x"] == "X"

    def test_parse_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("A\nB\n", encoding="utf-8")
        rule = RuleBuilder.block(
            {
                "rule_name": "r",
                "mode": "sequential",
                "max_lines": 5,
                "rules": {
                    "a": {"pattern": r"^A$"},
                    "b": {"pattern": r"^B$"},
                },
            }
        )
        parser = StreamingBlockParser([rule])
        results = list(parser.parse_file(f))
        assert len(results) == 1
        assert results[0].matches["a"] == "A"
        assert results[0].matches["b"] == "B"

    def test_on_match_callback(self) -> None:
        rule = RuleBuilder.block(
            {
                "rule_name": "r",
                "mode": "unordered",
                "max_lines": 5,
                "rules": {"x": {"pattern": r"^X$"}},
            }
        )
        parser = StreamingBlockParser([rule])
        called: list[MatchResult] = []

        def cb(res: MatchResult) -> None:
            called.append(res)

        lines = ["X", "X"]
        results = list(parser.parse_stream(iter(lines), on_match=cb))
        assert len(results) == 2
        assert len(called) == 2


# ============================================================================
# StreamingLineExtractor
# ============================================================================


class TestStreamingLineExtractor:
    def test_simple_line_rule(self) -> None:
        rule = RuleBuilder.line(
            {
                "rule_name": "digits",
                "pattern": r"^\d+$",
                "extract_groups": False,
                "match_mode": "match",
            }
        )
        parser = StreamingLineExtractor([rule])
        lines = ["123", "abc", "456"]
        results = list(parser.parse_stream(iter(lines)))
        assert len(results) == 2
        assert results[0].matches == {"value": "123"}
        assert results[1].matches == {"value": "456"}

    def test_sequential_line_rule(self) -> None:
        rule = RuleBuilder.line(
            {
                "rule_name": "ver",
                "strict_end": True,
                "rules": {
                    "prefix": {"pattern": r"^v", "store": False},
                    "major": {"pattern": r"(\d+)"},
                    "dot": {"pattern": r"\.", "store": False},
                    "minor": {"pattern": r"(\d+)"},
                },
            }
        )
        parser = StreamingLineExtractor([rule])
        lines = ["v1.2", "bad", "v3.4"]
        results = list(parser.parse_stream(iter(lines)))
        assert len(results) == 2
        assert results[0].matches["major"] == "1"
        assert results[0].matches["minor"] == "2"

    def test_search_mode(self) -> None:
        rule = RuleBuilder.line(
            {
                "rule_name": "ip",
                "pattern": r"\d+\.\d+\.\d+\.\d+",
                "extract_groups": False,
                "match_mode": "search",
            }
        )
        parser = StreamingLineExtractor([rule])
        lines = ["Connection from 192.168.1.1 port 22"]
        results = list(parser.parse_stream(iter(lines)))
        assert len(results) == 1
        assert results[0].matches["value"] == "Connection from 192.168.1.1 port 22"

    def test_named_groups_simple(self) -> None:
        rule = RuleBuilder.line(
            {
                "rule_name": "user",
                "pattern": r"^User: (?P<name>\S+), Age: (?P<age>\d+)$",
                "extract_groups": True,
                "match_mode": "match",
            }
        )
        parser = StreamingLineExtractor([rule])
        lines = ["User: Alice, Age: 30"]
        results = list(parser.parse_stream(iter(lines)))
        assert len(results) == 1
        assert results[0].matches == {"name": "Alice", "age": "30"}

    def test_parse_file(self, tmp_path: Path) -> None:
        f = tmp_path / "lines.txt"
        f.write_text("v1.2\nbad\nv3.4\n", encoding="utf-8")
        rule = RuleBuilder.line(
            {
                "rule_name": "ver",
                "strict_end": True,
                "rules": {
                    "prefix": {"pattern": r"^v", "store": False},
                    "major": {"pattern": r"(\d+)"},
                    "dot": {"pattern": r"\.", "store": False},
                    "minor": {"pattern": r"(\d+)"},
                },
            }
        )
        parser = StreamingLineExtractor([rule])
        results = list(parser.parse_file(f))
        assert len(results) == 2
        assert results[0].matches["major"] == "1"
        assert results[1].matches["major"] == "3"

    def test_on_match_callback(self) -> None:
        rule = RuleBuilder.line(
            {
                "rule_name": "digits",
                "pattern": r"^\d+$",
                "extract_groups": False,
            }
        )
        parser = StreamingLineExtractor([rule])
        called: list[MatchResult] = []

        def cb(res: MatchResult) -> None:
            called.append(res)

        lines = ["1", "a", "2"]
        results = list(parser.parse_stream(iter(lines), on_match=cb))
        assert len(results) == 2
        assert len(called) == 2


# ============================================================================
# Integration / Edge cases
# ============================================================================


class TestIntegration:
    def test_multiple_block_rules(self) -> None:
        configs = [
            {
                "rule_name": "type_a",
                "mode": "sequential",
                "max_lines": 3,
                "rules": {
                    "a": {"pattern": r"^A:(.+)$"},
                    "b": {"pattern": r"^B:(.+)$"},
                },
            },
            {
                "rule_name": "type_x",
                "mode": "sequential",
                "max_lines": 3,
                "rules": {
                    "x": {"pattern": r"^X:(.+)$"},
                    "y": {"pattern": r"^Y:(.+)$"},
                },
            },
        ]
        parser = StreamingBlockParser(RuleBuilder.blocks(configs))
        lines = [
            "A:1",
            "B:2",
            "X:10",
            "Y:20",
        ]
        results = list(parser.parse_stream(iter(lines)))
        assert len(results) == 2
        assert results[0].rule_name == "type_a"
        assert results[1].rule_name == "type_x"

    def test_extract_groups_fallback_to_group1(self) -> None:
        # unnamed group -> group(1)
        rule = BlockRule(
            name="t",
            lines=(
                LineSpec(
                    name="val", pattern=r"^VAL: (?P<val>\d+)$", extract_groups=True
                ),
            ),
            max_lines=3,
            mode="sequential",
        )
        fsm = BlockFSM(rule)
        res = fsm.feed("VAL: 42", 0)
        assert res is not None
        assert res.matches["val"]["val"] == "42"

    def test_extract_groups_no_groups_full_line(self) -> None:
        # no groups at all -> full line
        rule = BlockRule(
            name="t",
            lines=(LineSpec(name="val", pattern=r"^VAL: \d+$", extract_groups=True),),
            max_lines=3,
            mode="sequential",
        )
        fsm = BlockFSM(rule)
        res = fsm.feed("VAL: 42", 0)
        assert res is not None
        assert res.matches["val"] == "VAL: 42"

    def test_empty_stream(self) -> None:
        parser = StreamingBlockParser(
            [
                RuleBuilder.block(
                    {
                        "rule_name": "r",
                        "mode": "unordered",
                        "max_lines": 5,
                        "rules": {"x": {"pattern": r"^X$"}},
                    }
                )
            ]
        )
        assert list(parser.parse_stream(iter([]))) == []

    def test_only_terminator_no_result(self) -> None:
        # terminator before any required field -> reset, no MatchResult
        rule = RuleBuilder.block(
            {
                "rule_name": "t",
                "mode": "unordered",
                "max_lines": 5,
                "rules": {
                    "x": {"pattern": r"^X$"},
                    "end": {"pattern": r"^END$", "terminator": True, "store": False},
                },
            }
        )
        fsm = UnorderedBlockFSM(rule)
        assert fsm.feed("END", 0) is None
        assert fsm._active is False
