import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


# ==================== Исключения ====================


class ParseEngineError(Exception):
    """Базовое исключение движка."""

    pass


class RuleValidationError(ParseEngineError):
    """Правило некорректно сконфигурировано."""

    pass


# ==================== Модели ====================


@dataclass(frozen=True, slots=True)
class LineSpec:
    """
    Один шаг последовательности: строка в блоке или токен внутри строки.
    """

    name: str
    pattern: str
    optional: bool = False
    extract_groups: bool = True
    match_mode: str = "match"
    store: bool = True
    terminator: bool = False

    def compile(self) -> re.Pattern:
        return re.compile(self.pattern)


@dataclass(frozen=True, slots=True)
class BlockRule:
    """
    Правило для многострочного блока.
    """

    name: str
    lines: tuple[LineSpec, ...]
    max_lines: int
    mode: str = "sequential"  # "sequential" | "unordered"


@dataclass(frozen=True, slots=True)
class LineRule:
    """Простое однострочное правило."""

    name: str
    pattern: str
    extract_groups: bool = True
    match_mode: str = "match"

    def compile(self) -> re.Pattern:
        return re.compile(self.pattern)


@dataclass(frozen=True, slots=True)
class SequentialLineRule:
    """Последовательный парсинг токенов внутри одной строки."""

    name: str
    lines: tuple[LineSpec, ...]
    strict_end: bool = True


class MatchResult:
    """Результат парсинга одного блока / строки."""

    __slots__ = ("rule_name", "matches", "line_start", "line_end")

    def __init__(
        self, rule_name: str, matches: dict[str, Any], line_start: int, line_end: int
    ):
        self.rule_name = rule_name
        self.matches = matches
        self.line_start = line_start
        self.line_end = line_end

    def __repr__(self) -> str:
        return (
            f"MatchResult(rule={self.rule_name!r}, lines={self.line_start}-{self.line_end}, "
            f"keys={list(self.matches.keys())})"
        )


# ==================== Валидатор правил ====================


class RuleValidator:
    _VALID_MODES = frozenset(("match", "search"))

    @classmethod
    def validate_block(cls, config: dict) -> None:
        name = config.get("rule_name")
        if not name or not isinstance(name, str):
            raise RuleValidationError(
                f"Block rule must have non-empty string 'rule_name'. Got: {name!r}"
            )

        lines_cfg = config.get("rules")
        if not lines_cfg or not isinstance(lines_cfg, dict):
            raise RuleValidationError(
                f"Rule '{name}': 'rules' must be a non-empty dict of line specs."
            )

        seen_names: set[str] = set()
        for line_name, spec in lines_cfg.items():
            if not isinstance(spec, dict):
                raise RuleValidationError(
                    f"Rule '{name}', line '{line_name}': spec must be dict, got {type(spec).__name__}"
                )
            cls._validate_line_spec(name, line_name, spec, seen_names)

        max_lines = config.get("max_lines")
        if max_lines is None:
            raise RuleValidationError(
                f"Rule '{name}': 'max_lines' is required. "
                f"Set max_lines > 0 to limit block length."
            )
        if not isinstance(max_lines, int) or max_lines <= 0:
            raise RuleValidationError(
                f"Rule '{name}': 'max_lines' must be a positive integer (> 0), got {max_lines!r}."
            )

        mode = config.get("mode", "sequential")
        if mode not in ("sequential", "unordered"):
            raise RuleValidationError(
                f"Rule '{name}': mode must be 'sequential' or 'unordered', got {mode!r}"
            )

    @classmethod
    def _validate_line_spec(
        cls,
        rule_name: str,
        line_name: str,
        spec: dict,
        seen: set[str],
    ) -> None:
        if line_name in seen:
            raise RuleValidationError(
                f"Rule '{rule_name}': duplicate line name '{line_name}'. Names must be unique."
            )
        seen.add(line_name)

        pattern = spec.get("pattern")
        if not pattern or not isinstance(pattern, str):
            raise RuleValidationError(
                f"Rule '{rule_name}', line '{line_name}': "
                f"'pattern' must be a non-empty string, got {pattern!r}."
            )

        try:
            re.compile(pattern)
        except re.error as exc:
            raise RuleValidationError(
                f"Rule '{rule_name}', line '{line_name}': invalid regex '{pattern}': {exc}"
            ) from exc

        mode = spec.get("match_mode", "match")
        if mode not in cls._VALID_MODES:
            raise RuleValidationError(
                f"Rule '{rule_name}', line '{line_name}': "
                f"match_mode must be 'match' or 'search', got {mode!r}."
            )

        terminator = spec.get("terminator", False)
        if not isinstance(terminator, bool):
            raise RuleValidationError(
                f"Rule '{rule_name}', line '{line_name}': "
                f"'terminator' must be bool, got {terminator!r}."
            )

    @classmethod
    def validate_line(cls, config: dict) -> None:
        name = config.get("rule_name")
        if not name or not isinstance(name, str):
            raise RuleValidationError(
                f"Line rule must have non-empty string 'rule_name'. Got: {name!r}"
            )

        if "rules" in config:
            lines_cfg = config["rules"]
            if not lines_cfg or not isinstance(lines_cfg, dict):
                raise RuleValidationError(
                    f"Rule '{name}': 'rules' must be a non-empty dict of token specs."
                )
            seen: set[str] = set()
            for line_name, spec in lines_cfg.items():
                if not isinstance(spec, dict):
                    raise RuleValidationError(
                        f"Rule '{name}', token '{line_name}': spec must be dict."
                    )
                cls._validate_line_spec(name, line_name, spec, seen)
        elif "pattern" in config:
            pattern = config["pattern"]
            if not pattern or not isinstance(pattern, str):
                raise RuleValidationError(
                    f"Rule '{name}': 'pattern' must be a non-empty string."
                )
            try:
                re.compile(pattern)
            except re.error as exc:
                raise RuleValidationError(
                    f"Rule '{name}': invalid regex '{pattern}': {exc}"
                ) from exc
        else:
            raise RuleValidationError(
                f"Rule '{name}': config must contain either 'rules' (sequential) "
                f"or 'pattern' (simple regex)."
            )


# ==================== FSM: sequential многострочные блоки ====================


class BlockFSM:
    __slots__ = ("rule", "_specs", "_state", "_buffer", "_start_line", "_active")

    def __init__(self, rule: BlockRule) -> None:
        self.rule = rule
        self._specs: list[tuple[LineSpec, re.Pattern]] = [
            (spec, spec.compile()) for spec in rule.lines
        ]
        self.reset()

    def reset(self) -> None:
        self._state: int = 0
        self._buffer: dict[str, Any] = {}
        self._start_line: int = -1
        self._active: bool = False

    def feed(self, line: str, line_idx: int) -> MatchResult | None:
        if self._active and self.rule.max_lines > 0:
            if line_idx - self._start_line >= self.rule.max_lines:
                self.reset()
                return self._try_start(line, line_idx)

        if not self._active:
            return self._try_start(line, line_idx)
        return self._try_continue(line, line_idx)

    def _try_start(self, line: str, line_idx: int) -> MatchResult | None:
        spec, pattern = self._specs[0]
        m = pattern.match(line) if spec.match_mode == "match" else pattern.search(line)
        if m:
            self._active = True
            self._start_line = line_idx
            self._capture(spec, m, line)
            self._state = 1
            if self._state >= len(self._specs):
                return self._finalize(line_idx)
        return None

    def _try_continue(self, line: str, line_idx: int) -> MatchResult | None:
        if self._state >= len(self._specs):
            return self._finalize(line_idx - 1)

        spec, pattern = self._specs[self._state]
        m = pattern.match(line) if spec.match_mode == "match" else pattern.search(line)

        if m:
            self._capture(spec, m, line)
            self._state += 1
            if self._state >= len(self._specs):
                return self._finalize(line_idx)
            return None

        if spec.optional:
            self._state += 1
            return self._try_continue(line, line_idx)

        self.reset()
        return self._try_start(line, line_idx)

    def _capture(self, spec: LineSpec, match: re.Match, line: str) -> None:
        if not spec.store:
            return
        if spec.extract_groups:
            groups = match.groupdict()
            self._buffer[spec.name] = dict(groups) if groups else line
        else:
            self._buffer[spec.name] = line

    def _finalize(self, end_line: int) -> MatchResult:
        matches = self._buffer.copy()
        # Заполняем пропущенные optional-поля None
        for spec, _ in self._specs:
            if spec.optional and spec.store and spec.name not in matches:
                matches[spec.name] = None

        result = MatchResult(
            rule_name=self.rule.name,
            matches=matches,
            line_start=self._start_line,
            line_end=end_line,
        )
        self.reset()
        return result

    def finalize_eof(self) -> MatchResult | None:
        if not self._active:
            return None
        for i in range(self._state, len(self._specs)):
            if not self._specs[i][0].optional:
                return None
        # Если _buffer пуст, используем _start_line как line_end
        end_line = (
            self._start_line
            if not self._buffer
            else self._start_line + len(self._buffer) - 1
        )
        return self._finalize(end_line)


# ==================== FSM: unordered многострочные блоки ====================


class UnorderedBlockFSM:
    __slots__ = (
        "rule",
        "_specs",
        "_pending_required",
        "_pending_optional",
        "_collected",
        "_start_line",
        "_active",
        "_has_terminator",
    )

    def __init__(self, rule: BlockRule) -> None:
        self.rule = rule
        self._specs: list[tuple[LineSpec, re.Pattern]] = [
            (spec, spec.compile()) for spec in rule.lines
        ]
        self.reset()

    def reset(self) -> None:
        self._pending_required: set[str] = set()
        self._pending_optional: set[str] = set()
        for spec, _ in self._specs:
            (self._pending_optional if spec.optional else self._pending_required).add(
                spec.name
            )
        self._collected: dict[str, Any] = {}
        self._start_line: int = -1
        self._active: bool = False
        # ИЗМЕНЕНО: запоминаем, есть ли в правиле терминатор
        self._has_terminator: bool = any(spec.terminator for spec, _ in self._specs)

    def feed(self, line: str, line_idx: int) -> MatchResult | None:
        if self._active and self.rule.max_lines > 0:
            if line_idx - self._start_line >= self.rule.max_lines:
                self.reset()
                return self._try_capture(line, line_idx)
        return self._try_capture(line, line_idx)

    def _try_capture(self, line: str, line_idx: int) -> MatchResult | None:
        for spec, pattern in self._specs:
            if (
                spec.name not in self._pending_required
                and spec.name not in self._pending_optional
            ):
                continue

            m = (
                pattern.match(line)
                if spec.match_mode == "match"
                else pattern.search(line)
            )
            if not m:
                continue

            if not self._active:
                self._active = True
                self._start_line = line_idx

            # --- Терминатор: финализируем или сбрасываем ---
            if spec.terminator:
                self._capture(spec, m, line)

                if spec.name in self._pending_required:
                    self._pending_required.remove(spec.name)
                if spec.name in self._pending_optional:
                    self._pending_optional.remove(spec.name)

                if not self._pending_required:
                    return self._finalize(line_idx)
                else:
                    self.reset()
                    return None

            self._capture(spec, m, line)

            if spec.name in self._pending_required:
                self._pending_required.remove(spec.name)
            if spec.name in self._pending_optional:
                self._pending_optional.remove(spec.name)

            # ИЗМЕНЕНО: если есть терминатор, ждём его — не финализируем сразу
            if not self._pending_required:
                if self._has_terminator:
                    return None
                return self._finalize(line_idx)
            return None

        return None

    def _capture(self, spec: LineSpec, match: re.Match, line: str) -> None:
        if not spec.store:
            return
        if spec.extract_groups:
            groups = match.groupdict()
            self._collected[spec.name] = dict(groups) if groups else line
        else:
            self._collected[spec.name] = line

    def _finalize(self, end_line: int) -> MatchResult:
        for name in list(self._pending_optional):
            self._collected[name] = None
            self._pending_optional.remove(name)

        result = MatchResult(
            rule_name=self.rule.name,
            matches=self._collected.copy(),
            line_start=self._start_line,
            line_end=end_line,
        )
        self.reset()
        return result

    def finalize_eof(self) -> MatchResult | None:
        if not self._active or self._pending_required:
            return None
        return self._finalize(self._start_line)


# ==================== FSM: последовательный парсинг внутри строки ====================


class SequentialLineFSM:
    __slots__ = ("rule", "_specs")

    def __init__(self, rule: SequentialLineRule) -> None:
        self.rule = rule
        self._specs: list[tuple[LineSpec, re.Pattern]] = [
            (spec, spec.compile()) for spec in rule.lines
        ]

    def parse(self, line: str, line_idx: int) -> MatchResult | None:
        cursor = 0
        matches: dict[str, Any] = {}

        for spec, pattern in self._specs:
            m = pattern.match(line, cursor)
            if m:
                if spec.store:
                    if spec.extract_groups:
                        groups = m.groupdict()
                        matches[spec.name] = dict(groups) if groups else m.group(0)
                    else:
                        matches[spec.name] = m.group(0)
                cursor = m.end()
            elif spec.optional:
                if spec.store:
                    matches[spec.name] = None
            else:
                return None

        if self.rule.strict_end and cursor != len(line):
            return None

        return MatchResult(
            rule_name=self.rule.name,
            matches=matches,
            line_start=line_idx,
            line_end=line_idx,
        )


# ==================== Потоковые парсеры ====================


class StreamingBlockParser:
    def __init__(self, rules: list[BlockRule]) -> None:
        self.rules = rules
        self._fsms: list[BlockFSM | UnorderedBlockFSM] = []
        for r in rules:
            if r.mode == "unordered":
                self._fsms.append(UnorderedBlockFSM(r))
            else:
                self._fsms.append(BlockFSM(r))

    def parse_stream(
        self,
        lines: Iterator[str],
        *,
        on_match: None | Any = None,
    ) -> Iterator[MatchResult]:
        for idx, raw_line in enumerate(lines):
            line = raw_line.rstrip("\n")
            for fsm in self._fsms:
                res = fsm.feed(line, idx)
                if res:
                    if on_match:
                        on_match(res)
                    yield res

        for fsm in self._fsms:
            res = fsm.finalize_eof()
            if res:
                if on_match:
                    on_match(res)
                yield res

    def parse_file(
        self,
        path: str | Path,
        *,
        encoding: str = "utf-8",
        errors: str = "replace",
        on_match: Any | None = None,
    ) -> Iterator[MatchResult]:
        with open(path, "r", encoding=encoding, errors=errors) as f:
            yield from self.parse_stream(f, on_match=on_match)


class StreamingLineExtractor:
    def __init__(self, rules: list[LineRule | SequentialLineRule]) -> None:
        self.rules = rules
        self._simple: list[tuple[LineRule, re.Pattern]] = []
        self._sequential: list[SequentialLineFSM] = []

        for r in rules:
            if isinstance(r, SequentialLineRule):
                self._sequential.append(SequentialLineFSM(r))
            else:
                self._simple.append((r, r.compile()))

    def parse_stream(
        self,
        lines: Iterator[str],
        *,
        on_match: Any | None = None,
    ) -> Iterator[MatchResult]:
        for idx, raw_line in enumerate(lines):
            line = raw_line.rstrip("\n")
            yielded = False

            for fsm in self._sequential:
                res = fsm.parse(line, idx)
                if res:
                    if on_match:
                        on_match(res)
                    yield res
                    yielded = True
                    break

            if yielded:
                continue

            for rule, pattern in self._simple:
                m = (
                    pattern.match(line)
                    if rule.match_mode == "match"
                    else pattern.search(line)
                )
                if m:
                    if rule.extract_groups:
                        groups = m.groupdict()
                        matches: dict[str, Any] = (
                            dict(groups) if groups else {"value": line}
                        )
                    else:
                        matches = {"value": line}
                    res = MatchResult(rule.name, matches, idx, idx)
                    if on_match:
                        on_match(res)
                    yield res
                    break

    def parse_file(
        self,
        path: str | Path,
        *,
        encoding: str = "utf-8",
        errors: str = "replace",
        on_match: Any | None = None,
    ) -> Iterator[MatchResult]:
        with open(path, "r", encoding=encoding, errors=errors) as f:
            yield from self.parse_stream(f, on_match=on_match)


# ==================== Универсальный RuleBuilder ====================


class RuleBuilder:
    @staticmethod
    def block(config: dict) -> BlockRule:
        RuleValidator.validate_block(config)

        lines: list[LineSpec] = []
        for key, val in config["rules"].items():
            is_terminator = val.get("terminator", False)
            optional = (
                val.get("optional", True)
                if is_terminator
                else val.get("optional", False)
            )

            lines.append(
                LineSpec(
                    name=key,
                    pattern=val.get("pattern", ".*"),
                    optional=optional,
                    extract_groups=val.get("extract_groups", True),
                    match_mode=val.get("match_mode", "match"),
                    store=val.get("store", True),
                    terminator=is_terminator,
                )
            )

        return BlockRule(
            name=config["rule_name"],
            lines=tuple(lines),
            max_lines=config["max_lines"],
            mode=config.get("mode", "sequential"),
        )

    @staticmethod
    def blocks(configs: list[dict]) -> list[BlockRule]:
        return [RuleBuilder.block(c) for c in configs]

    @staticmethod
    def line(config: dict) -> LineRule | SequentialLineRule:
        RuleValidator.validate_line(config)

        if "rules" in config:
            specs: list[LineSpec] = []
            for key, val in config["rules"].items():
                is_terminator = val.get("terminator", False)
                optional = (
                    val.get("optional", True)
                    if is_terminator
                    else val.get("optional", False)
                )

                specs.append(
                    LineSpec(
                        name=key,
                        pattern=val.get("pattern", ".*"),
                        optional=optional,
                        extract_groups=val.get("extract_groups", True),
                        match_mode=val.get("match_mode", "match"),
                        store=val.get("store", True),
                        terminator=is_terminator,
                    )
                )
            return SequentialLineRule(
                name=config["rule_name"],
                lines=tuple(specs),
                strict_end=config.get("strict_end", True),
            )

        return LineRule(
            name=config["rule_name"],
            pattern=config["pattern"],
            extract_groups=config.get("extract_groups", True),
            match_mode=config.get("match_mode", "match"),
        )

    @staticmethod
    def lines(configs: list[dict]) -> list[LineRule | SequentialLineRule]:
        return [RuleBuilder.line(c) for c in configs]
