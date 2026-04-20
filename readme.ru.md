# Distill

<div align="center">

[English](readme.md) | [Русский](readme.ru.md)

</div>

<div align="center">

![](assets/pic_gif.gif)
</div>

<div align="center">

**Парсер на основе конечных автоматов**

[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style](https://img.shields.io/badge/formatted-blue?style=for-the-badge&logo=ruff&logoColor=white&label=ruff&color=%23d7ff64)](https://github.com/astral-sh/ruff)

</div>

---


## 📋 Содержание

- [🎯 Обзор](#-обзор)
- [✨ Возможности](#-возможности)
- [🚀 Быстрый старт](#-быстрый-старт)
  - [Установка](#установка)
- [🏗️ Архитектура](#-архитектура)
  - [Основные компоненты](#основные-компоненты)
- [📚 Детальная документация](#-детальная-документация)
  - [🧱 Многострочные блоки (_StreamingBlockParser_)](#многострочные-блоки-streamingblockparser)
    - [Sequential Mode (строгий порядок)](#sequential-mode-строгий-порядок)
    - [Unordered Mode (произвольный порядок)](#unordered-mode-произвольный-порядок)
    - [Терминаторы](#терминаторы)
    - [Max Lines — защита от "зависших" блоков](#max-lines--защита-от-зависших-блоков)
    - [Параметры правил _StreamingBlockParser_](#параметры-правил-streamingblockparser)
    - [Режимы работы BlockRule](#режимы-работы-blockrule)
    - [⚠️ Особенности терминатора](#️-особенности-терминатора)
    - [💡 Примеры конфигураций _StreamingBlockParser_](#-примеры-конфигураций-streamingblockparser)
        - [Sequential — парсинг чека/заказа](#-sequential--парсинг-чеказаказа)
        - [Unordered — конфигурация приложения](#️-unordered--конфигурация-приложения)
        - [Unordered — системные метрики](#-unordered--системные-метрики)
        - [Sequential — парсинг устройства IoT](#-sequential--парсинг-устройства-iot)
  - [Парсинг внутри строки (_StreamingLineExtractor_)](#парсинг-внутри-строки-streaminglineextractor)
    - [Простые однострочные правила](#простые-однострочные-правила)
    - [Параметры правил (_StreamingLineExtractor_)](#параметры-правил-streaminglineextractor)
    - [Ключевые отличия от _StreamingBlockParser_](#ключевые-отличия-от-streamingblockparser)
    - [💡 Примеры конфигураций _StreamingLineExtractor_](#-примеры-конфигураций-streaminglineextractor)
        - [Пример 1: Версия ПО](#пример-1-версия-по)
        - [Пример 2: Запись инвентаря](#пример-2-запись-инвентаря)
        - [Пример 3: Координаты](#пример-3-координаты)
- [💡 Примеры использования](#-примеры-использования)
  - [Пример извлечения с одной строки (_StreamingLineExtractor_)](#пример-извлечения-с-одной-строки-streaminglineextractor)
  - [Пример блочного подхода (_StreamingBlockParser_)](#пример-блочного-подхода-streamingblockparser)
- [🎮 CLI](#-cli)
- [🕵🏼‍♀️ Forensics](#️-forensics)
- [🔧 Требования](#-требования)


---

## 🎯 Обзор

**Distill** — это движок парсинга на основе конечных автоматов (FSM), предназначенный для:

- **Потоковой обработки** больших файлов с O(1) потреблением памяти
- **Извлечения структурированных данных** из неструктурированных текстовых потоков
- **Парсинга многострочных блоков** с поддержкой строгого и нестрогого порядка
- **Последовательного разбора** токенов внутри одной строки

Идеально подходит для:
- Лог-файлов и системных журналов
- Конфигурационных файлов
- Вывода CLI-команд
- ETL-процессов
- Форензики и анализа данных

---

## ✨ Возможности

| Возможность | Описание |
|-------------|----------|
| 🔄 **Sequential Mode** | Строгий порядок строк в блоке — каждая строка должна следовать в заданной последовательности |
| 🔀 **Unordered Mode** | Строки в блоке могут идти в любом порядке — гибкий парсинг неструктурированных данных |
| ⏹️ **Терминаторы** | Принудительная финализация блока по разделителю или сброс при несовпадении |
| 📏 **Max Lines** | Принудительный лимит строк — блок сбрасывается, если не собрался за N строк |
| 🎯 **Match/Search Modes** | `match` (с начала строки) или `search` (где угодно в строке) |
| 📝 **Group Extraction** | Автоматическое извлечение named groups из regex или сохранение всей строки |
| 🔄 **Streaming** | Потоковая обработка без загрузки всего файла в память |
| ✅ **Валидация** | Проверка всех правил при старте — ошибки конфигурации ловятся сразу |

---

## 🚀 Быстрый старт

### Установка

```bash
# Клонирование репозитория
git clone https://github.com/yourusername/distill.git
cd Distill

pip install -e .

# Установка (пока нет PyPI)
```

## 🏗️ Архитектура

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

### Основные компоненты

| Компонент                | Назначение                                              |
| ------------------------ | ------------------------------------------------------- |
| `RuleBuilder`            | Фабрика для создания правил из dict-конфигураций        |
| `RuleValidator`          | Валидация конфигураций перед созданием FSM              |
| `BlockFSM`               | FSM для последовательного парсинга многострочных блоков |
| `UnorderedBlockFSM`      | FSM для неупорядоченного парсинга блоков                |
| `SequentialLineFSM`      | FSM для последовательного парсинга токенов в строке     |
| `StreamingBlockParser`   | Потоковый парсер для многострочных блоков               |
| `StreamingLineExtractor` | Потоковый парсер для однострочных правил                |
| `MatchResult`            | Результат парсинга с метаданными                        |

## 📚 Детальная документация

### Многострочные блоки (StreamingBlockParser)
### Sequential Mode (строгий порядок)

В этом режиме строки в блоке должны **следовать строго** в заданном порядке:

```python
# пример данных
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
    "mode": "sequential",  # Строгий порядок!
    "max_lines": 5,
    "rules": {
        "price":    {"pattern": r"^PRICE: (\d*)$"},
        "count":    {"pattern": r"^COUNT: (\d{3})$"},
        "id":       {"pattern": r"^ID: (.+)$"},
        "comment":  {"pattern": r"[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$", "optional": True}
    }
}
```

#### Поведение:
1. Строка "PRICE:" должна быть первой
2. Строка "COUNT:" должна быть второй
3. Строка "ID:" должна быть третьей
4. Если порядок нарушен — блок сбрасывается и начинается новый

### Unordered Mode (произвольный порядок)
Строки могут идти в **любом порядке**, но все обязательные должны присутствовать:
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

#### Поведение:
1. Строки могут идти в любом порядке
2. HOST, PORT, USER — обязательны
3. SSL — опционален
4. Блок финализируется, когда собраны все обязательные поля

### Терминаторы

Терминаторы позволяют **принудительно завершить блок** при встрече определенной строки:
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

Логика терминатора:
1. Если все обязательные поля собраны → финализировать блок
2. Если не все обязательные собраны → сбросить блок (невалидные данные)

### Max Lines — защита от "зависших" блоков
```python
config = {
    "rule_name": "transaction",
    "mode": "sequential",
    "max_lines": 100,  # Если блок не собрался за 100 строк — сброс
    "rules": {
        # ... правила
    }
}
```

#### Поведение:
1. Если FSM активен более max_lines строк — принудительный сброс
2. Предотвращает бесконечное ожидание в случае поврежденных данных


#### Параметры правил **StreamingBlockParser**
| Параметр    | Тип    | По умолчанию   | Описание                                                                                                                          |
| ----------- | ------ | -------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `rule_name` | `str`  | —              | Уникальное имя правила (блока)                                                                                                    |
| `mode`      | `str`  | `"sequential"` | Режим парсинга блока: `"sequential"` (строгий порядок строк) или `"unordered"` (строки в любом порядке)                           |
| `max_lines` | `int`  | —              | **Обязательный**. Максимальное количество строк, которое может занять блок. Если блок не собрался за `N` строк — FSM сбрасывается |
| `rules`     | `dict` | —              | Словарь спецификаций строк `{имя: spec}`. Порядок ключов важен для `sequential` режима                                            |

Каждый элемент словаря rules — это спецификация одной строки в многострочном блоке.
| Параметр         | Тип    | По умолчанию | Описание                                                                                                                                                                  |
| ---------------- | ------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`           | `str`  | —            | Уникальное имя строки (берётся из ключа словаря)                                                                                                                          |
| `pattern`        | `str`  | —            | Regex-шаблон для сопоставления со строкой                                                                                                                                 |
| `optional`       | `bool` | `False`      | Может ли строка отсутствовать в блоке. В `sequential` — пропускается с попыткой сопоставить следующую спецификацию. В `unordered` — не входит в список обязательных       |
| `extract_groups` | `bool` | `True`       | Извлекать `named groups` (`(?P<name>...)`) в словарь. Если named groups нет — берётся `match.group(1)` (первая группа). Если групп нет — сохраняется вся строка           |
| `match_mode`     | `str`  | `"match"`    | `"match"` — сопоставление с начала строки (`pattern.match(line)`). `"search"` — поиск паттерна где угодно в строке (`pattern.search(line)`)                               |
| `store`          | `bool` | `True`       | Сохранять ли значение в итоговый `matches`. Если `False` — строка участвует в структуре блока, но не попадает в результат (например, разделители)                         |
| `terminator`     | `bool` | `False`      | **Только для `unordered`**. Если `True` — при совпадении этой строки блок принудительно финализируется (если собраны все обязательные) или сбрасывается (если не собраны) |

#### Режимы работы BlockRule
| Режим            | Описание                                         | Поведение при несовпадении                                            | Поведение `optional`                                                                                        |
| ---------------- | ------------------------------------------------ | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| **`sequential`** | Строки должны идти **строго в заданном порядке** | Блок сбрасывается, парсер пытается начать новый блок с текущей строки | Пропускается спецификация, попытка сопоставить следующую                                                    |
| **`unordered`**  | Строки могут идти в **любом порядке**            | Строка пропускается (ожидаем другую), блок остаётся активным          | Поле не входит в множество обязательных. При `finalize_eof` отсутствующие опциональные поля получают `None` |

#### ⚠️ Особенности терминатора
| Ситуация                                           | Результат                                                    |
| -------------------------------------------------- | ------------------------------------------------------------ |
| `terminator: True` + все обязательные поля собраны | Блок **финализируется** немедленно                           |
| `terminator: True` + не все обязательные собраны   | Блок **сбрасывается** (невалидные данные)                    |
| `terminator: True` в `sequential` режиме           | **Игнорируется** (терминаторы работают только в `unordered`) |


### 💡 Примеры конфигураций **StreamingBlockParser**
##### Sequential — парсинг чека/заказа (строгий порядок строк)

Данные:
```
ORDER# 1042
DATE: 2024-11-15
ITEM: Wireless Mouse MX3
QTY: 2
DISCOUNT: 10%
======
```

Правила:
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
Результат:
```python
{'order_id': 'ORDER# 1042', 'date': 'DATE: 2024-11-15', 'item': 'ITEM: Wireless Mouse MX3', 'qty': 'QTY: 2', 'discount': 'DISCOUNT: 10%'}
```

##### Unordered — конфигурация приложения (любой порядок + терминатор)
Данные:
```
VERSION: 2.4.1
WORKERS: 8
APP_NAME: DataProcessor
LOG_LEVEL: INFO
[END]
```
Правила:
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
Результат:
```python
{'version': 'VERSION: 2.4.1', 'workers': 'WORKERS: 8', 'app_name': 'APP_NAME: DataProcessor', 'log_level': 'LOG_LEVEL: INFO', 'debug': None}
```

##### Unordered — системные метрики (опциональные поля)
Данные:
```
TS: 1713456789
MEM: 42.5%
CPU: 12.3%
```
Правила:
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
Результат:
```python
{'timestamp': {'ts': '1713456789'}, 'memory': {'memory': '42.5'}, 'cpu': {'cpu': '12.3'}, 'network': None, 'disk': None}
```

##### 🔧 Sequential — парсинг устройства IoT (с пропуском опциональных строк)
Данные (без humidity): 
```
DEVICE: A1B2C3D4
TEMP: 23.5C
PRESSURE: 1013hPa
CRC: 8F2A
```
Правила:
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

Результат:
```python
{'device_id': 'DEVICE: A1B2C3D4', 'temp': 'TEMP: 23.5C', 'pressure': 'PRESSURE: 1013hPa', 'checksum': 'CRC: 8F2A'}
```


### Парсинг внутри строки (StreamingLineExtractor)
Для разбора CSV (или подобных форматов), логов с фиксированной структурой и других форматов:
```python
config = [
    {
        "rule_name": "csv_record",
        "strict_end": True,  # Строка должна заканчиваться после последнего токена
        "rules": {
            "domain":   {"pattern": r"^(?P<domain>(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]*),"},
            "username": {"pattern": r"(?P<username>[^,]+)$"},
        }
    }
]

rule = RuleBuilder.line(config)
parser = StreamingLineExtractor([rule])

# Парсинг
data = "example.com,User123"
for result in parser.parse_stream([data]):
    print(result)
    # MatchResult(rule='csv_record', lines=0-0, keys=['domain', 'username'])
    print(result.rule_name, "-", result.matches)
    # csv_record - {'domain': {'domain': 'example.com'}, 'username': {'username': 'User123'}}
```

### Простые однострочные правила
Для простого извлечения данных из отдельных строк:
```python
config = {
    "rule_name": "email",
    "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "extract_groups": False,  # Сохранить всю строку
    "match_mode": "match"
}

rule = RuleBuilder.line(config)
parser = StreamingLineExtractor([rule])
```


#### Параметры правил (_StreamingLineExtractor_)

Используется, когда в конфиге есть ключ `"pattern"` — одно регулярное выражение на всю строку.
| Параметр         | Тип    | По умолчанию | Описание                                                                                                                  |
| ---------------- | ------ | ------------ | ------------------------------------------------------------------------------------------------------------------------- |
| `rule_name`      | `str`  | —            | Уникальное имя правила                                                                                                    |
| `pattern`        | `str`  | —            | Regex-шаблон для сопоставления со строкой                                                                                 |
| `extract_groups` | `bool` | `True`       | Извлекать `named groups` (`(?P<name>...)`) в словарь. Если named groups нет — сохраняется вся строка под ключом `"value"` |
| `match_mode`     | `str`  | `"match"`    | `"match"` — с начала строки (`^...`), `"search"` — поиск где угодно                                                       |

Используется, когда в конфиге есть ключ `"rules"` — последовательный разбор токенов внутри одной строки слева направо.
| Параметр     | Тип    | По умолчанию | Описание                                                                                                              |
| ------------ | ------ | ------------ | --------------------------------------------------------------------------------------------------------------------- |
| `rule_name`  | `str`  | —            | Уникальное имя правила                                                                                                |
| `rules`      | `dict` | —            | Словарь токенов `{имя: spec}`. Порядок ключов = порядок парсинга!                                                     |
| `strict_end` | `bool` | `True`       | Если `True`, строка должна заканчиваться **строго** после последнего токена. Если `False` — хвост строки игнорируется |

Каждый элемент словаря rules в SequentialLineRule — это спецификация токена.
| Параметр         | Тип    | По умолчанию | Описание                                                                                                                 |
| ---------------- | ------ | ------------ | ------------------------------------------------------------------------------------------------------------------------ |
| `name`           | `str`  | —            | Уникальное имя токена (берётся из ключа словаря)                                                                         |
| `pattern`        | `str`  | —            | Regex-шаблон для этого токена. Для sequential рекомендуется `match` (с текущей позиции курсора)                          |
| `optional`       | `bool` | `False`      | Может ли токен отсутствовать. Если `True` и не найден — в результат записывается `None`                                  |
| `extract_groups` | `bool` | `True`       | Извлекать `named groups`. Если их нет — берётся `match.group(1)` (первая группа). Если групп нет — весь текст совпадения |
| `match_mode`     | `str`  | `"match"`    | Для sequential всегда используется `match` (сопоставление с текущей позиции курсора). `search` не применим               |
| `store`          | `bool` | `True`       | Сохранять ли значение токена в итоговый `matches`. Если `False` — токен участвует в парсинге, но не попадает в результат |
| `terminator`     | `bool` | `False`      | ⚠️ **Не используется** в `StreamingLineExtractor` (работает только в блоковых парсерах)                                  |

##### Ключевые отличия от **StreamingBlockParser**

| Особенность  | StreamingBlockParser           | LineRule / SequentialLineRule |
| ------------ | ------------------------------ | ----------------------------- |
| `max_lines`  | ✅ Есть                        | ❌ Нет (всегда одна строка)    |
| `mode`       | `"sequential"` / `"unordered"` | ❌ Нет                         |
| `terminator` | ✅ Работает                    | ❌ Игнорируется                |
| `optional`   | ✅ В sequential/unordered      | ✅ Только в sequential         |
| `strict_end` | ❌ Нет                         | ✅ Только в sequential         |


#### 💡 Примеры конфигураций **StreamingLineExtractor**

##### Пример 1: Версия ПО
Данные:
```
v2.14.3-beta+20241115
v1.0.0
v3.5.2-alpha
invalid string
```

Правила:
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

Результат:
```python
{'major': '2', 'minor': '14', 'patch': '3', 'pre': '-beta', 'build': '+20241115'}
{'major': '1', 'minor': '0', 'patch': '0', 'pre': None, 'build': None}
{'major': '3', 'minor': '5', 'patch': '2', 'pre': '-alpha', 'build': None}
```

#### Пример 2: Запись инвентаря
Данные:
```
INV-2024-001 | 150 | Electronics | Warehouse-A
INV-2024-002 | 42 | | Warehouse-B
```

Правила:
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

Результат:
```python
{'doc_id': 'INV-2024-001', 'quantity': '150', 'category': 'Electronics | ', 'location': {'loc': 'Warehouse-A'}}
{'doc_id': 'INV-2024-002', 'quantity': '42', 'category': None, 'location': {'loc': 'Warehouse-B'}}
```

#### Пример 3: Координаты
Данные:
```
55.7558, 37.6173, 144m
48.8566, 2.3522
-33.8688, 151.2093, 58m
```

Правила:
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

Результат:
```python
{'lat': '55.7558', 'lon': '37.6173', 'altitude': '144'}
{'lat': '48.8566', 'lon': '2.3522', 'altitude': None}
{'lat': '-33.8688', 'lon': '151.2093', 'altitude': '58'}
```


# 💡 Примеры использования

### Пример извлечения с одной строки (_StreamingLineExtractor_)

Пример данных (файл ssh_logs.txt):
```txt
Dec 24 06:55:46 LabSZ sshd[24200]: pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost=12.13.14.15 
Dec 24 06:55:48 LabSZ sshd[24200]: Failed password for invalid user webmaster from 12.13.14.15 port 22 ssh2
Dec 24 06:55:48 LabSZ sshd[24200]: Connection closed by 12.13.14.15 [preauth]
...
```

Пример извлечения **Username/IP/Port** попыток "Failed password" попыток:
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

### Пример блочного подхода (_StreamingBlockParser_)

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
        "mode": "sequential",  # Строгий порядок!
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
Вывод:
```json
{"price": "PRICE: 10$", "count": "COUNT: 5", "id": "ID: a8a89cf1-9d0d-4b7c-92bd-7a62667f5664"}
{"price": "PRICE: 150$", "count": "COUNT: 10", "id": "ID: a8a89cf1-9d0d-4b7c-92bd-7a62667f5664", "comment": "COMMENT: Important"}
{"price": "PRICE: 5$", "count": "COUNT: 11", "id": "ID: a8a89cf1-9d0d-4b7c-92bd-7a62667f5664"}"
```

#### Используя именованные группы захвата:
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
Вывод:
```json
{"price": {"price": "10"}, "count": {"count": "5"}, "id": {"id": "a8a89cf1-9d0d-4b7c-92bd-7a62667f5664"}}
{"price": {"price": "150"}, "count": {"count": "10"}, "id": {"id": "a8a89cf1-9d0d-4b7c-92bd-7a62667f5664"}, "comment": {"comment": "Important"}}
{"price": {"price": "5"}, "count": {"count": "11"}, "id": {"id": "a8a89cf1-9d0d-4b7c-92bd-7a62667f5664"}}
```


# 🎮 CLI

Запуск (после установки `pip install -e .`):
```bash
distill -i <path to file for parse> -r <rules file JSON> -m line -o <result JSONL>
```

Пример:

Файл с данными ( `/tmp/input.txt` ):
```txt
example.com,User123
example2.com,User1234
```

Файл с правилами ( `/tmp/rules.json` ):
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

Запуск:
```bash
$ distill -i /tmp/input.txt -r /tmp/rules.json -m line -o /tmp/distill_result.jsonl
# [OK] Parsed 2 results -> /tmp/distill_result.jsonl
```

Результаты:
```bash
$ cat /tmp/distill_result.jsonl

{"rule": "csv_record", "lines": [0, 0], "matches": {"domain": {"domain": "example.com"}, "username": {"username": "User123"}}}
{"rule": "csv_record", "lines": [1, 1], "matches": {"domain": {"domain": "example2.com"}, "username": {"username": "User1234"}}}
```

---
# 🕵🏼‍♀️ Forensics
### 📢❗🚨 В будущем возможности возможно будут расширены...

Пример скрипта для поиска данных в байтах. (скрипт - `/scripts/dump_carving.py`):
```bash
python scripts/dump_carving.py path/to/your/dump/pagefile.sys
```

Результаты:
```
=== URL Carving from Memory Dump ===

[url_plain           ] offset=0x00023ba8 (ascii   ) | http://crl.microsoft.com/pki/crl/prod
[url_plain           ] offset=0x00063661 (ascii   ) | https://jinohu.cc/
[url_plain           ] offset=0x000a2812 (ascii   ) | http://www.microsoft.com/pki/crl/products/MicCerTruLisPCA_2009-04-02.crlJ
[url_plain           ] offset=0x00111968 (ascii   ) | https://github.com/benjamin3346/playit/releases/S
[url_plain           ] offset=0x0011400b (ascii   ) | https://api.judicial.it.com/bypass_extreme_2_x86_fac0c5.exe'-outfile'%temp%\dian_sec1
```
---


# 🔧 Требования
- Python 3.13+ (возможно и версии ниже)
- Только стандартные библиотеки (нет внешних зависимостей)

<div align="right">

### Резко урони звезду, если заюзал и была польза. Спасибо!

</div>

---
## 📜 License
MIT License
