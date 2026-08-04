#!/usr/bin/env python3
"""Markdown (Obsidian) -> Confluence wiki markup.

Порядок преобразований важен: сначала вырезаются код-блоки и inline-код
в плейсхолдеры, чтобы их содержимое не трогали остальные правила, затем
работают блочные правила, и только в самом конце экранируются квадратные
скобки — иначе они сломают уже созданный синтаксис ссылок Confluence.

Ключевое ограничение Confluence, проверенное на живом инстансе 2026-07-28:
  * `[текст]` — это ССЫЛКА на страницу, а не литерал. Любые квадратные скобки
    в содержимом обязаны стать `&#91;` / `&#93;`, причём `{{...}}` от этого
    НЕ защищает.
  * обратный слэш не экранирует: он ломает разбор целиком, и Confluence
    выбрасывает весь текст в макрос `unmigrated-wiki-markup`.

Использование:
    md2wiki.py <файл.md>            печатает wiki-разметку в stdout
    md2wiki.py --title <файл.md>    печатает только заголовок из H1
"""
import re
import sys

LB, RB = "&#91;", "&#93;"
LC, RC = "&#123;", "&#125;"

# Плейсхолдер собственных макросов: их фигурные скобки не должны попасть
# под общее экранирование, иначе {quote} превратится в текст.
MACRO_MARK = "\x03"

# Callout Obsidian -> панель Confluence. Цвета панелей: info синий,
# note жёлтый, warning красный.
CALLOUTS = {
    "note": "info",
    "info": "info",
    "important": "note",
    "warning": "warning",
    "caution": "warning",
}


def esc(s):
    """Экранирует все четыре опасных символа Confluence."""
    return (s.replace("[", LB).replace("]", RB)
             .replace("{", LC).replace("}", RC))


def _protect(text, blocks):
    """Вырезает fenced-код в плейсхолдеры."""
    def repl(m):
        lang = (m.group(1) or "").strip()
        body = m.group(2)
        blocks.append(("code", lang, body))
        return f"\x00BLOCK{len(blocks) - 1}\x00"

    return re.sub(r"```([\w+-]*)\n(.*?)```", repl, text, flags=re.S)


def _protect_inline(text, spans):
    """Вырезает inline-код в плейсхолдеры."""
    def repl(m):
        spans.append(m.group(1))
        return f"\x00SPAN{len(spans) - 1}\x00"

    return re.sub(r"`([^`\n]+)`", repl, text)


def _macro(macros, tag):
    """Прячет готовый макрос в плейсхолдер, минуя esc()."""
    macros.append(tag)
    return f"{MACRO_MARK}{len(macros) - 1}{MACRO_MARK}"


def _quote_open(first, spans):
    """Выбирает обёртку блока по его первой строке.

    Возвращает (открывающий тег, закрывающий тег, остаток первой строки);
    остаток None — строка целиком ушла в заголовок панели.
    """
    m = re.match(r"^\[!(\w+)\]\s*(.*)$", first)
    kind = CALLOUTS.get(m.group(1).lower()) if m else None
    if not kind:                              # тип вне таблицы — обычная цитата
        return "{quote}", "{quote}", first
    # в параметре макроса разметка не работает, нужен обычный текст
    title = re.sub(r"\x00SPAN(\d+)\x00",
                   lambda s: spans[int(s.group(1))], m.group(2)).strip()
    if re.search(r"[{}\[\]|]", title):
        # такой заголовок сломал бы разбор параметров — уводим его в тело
        return "{" + kind + "}", "{" + kind + "}", "**" + m.group(2) + "**"
    if not title:
        return "{" + kind + "}", "{" + kind + "}", None
    return "{" + kind + ":title=" + title + "}", "{" + kind + "}", None


def _table(lines, i, out):
    """Преобразует markdown-таблицу начиная со строки i. Возвращает новый i."""
    header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
    out.append("||" + "||".join(header) + "||")
    i += 2  # шапка и разделитель
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        out.append("|" + "|".join(cells) + "|")
        i += 1
    return i


def convert(md):
    blocks, spans, macros = [], [], []
    md = _protect(md, blocks)
    md = _protect_inline(md, spans)

    lines = md.split("\n")
    out, i, in_quote, quote_close = [], 0, False, ""

    while i < len(lines):
        ln = lines[i]

        # таблица: строка на | и следующая — разделитель
        if (ln.lstrip().startswith("|") and i + 1 < len(lines)
                and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1])):
            if in_quote:
                out.append(quote_close)
                in_quote = False
            i = _table(lines, i, out)
            continue

        # цитата; первая строка вида "[!тип] Заголовок" даёт панель Confluence
        if ln.startswith(">"):
            body = ln.lstrip(">").strip()
            if not in_quote:
                open_tag, close_tag, body = _quote_open(body, spans)
                out.append(_macro(macros, open_tag))
                quote_close = _macro(macros, close_tag)
                in_quote = True
                if body is None:             # строка ушла в title=
                    i += 1
                    continue
            out.append(body)
            i += 1
            continue
        if in_quote:
            out.append(quote_close)
            in_quote = False

        # заголовки: H1 съедается вызывающим кодом, здесь H2 и глубже
        m = re.match(r"^(#{2,6})\s+(.*)$", ln)
        if m:
            out.append(f"h{len(m.group(1))}. {m.group(2).strip()}")
            i += 1
            continue

        # горизонтальная линия
        if re.match(r"^\s*(---|\*\*\*|___)\s*$", ln):
            out.append("----")
            i += 1
            continue

        # списки: отступ определяет уровень
        m = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", ln)
        if m:
            indent, marker, body = m.group(1), m.group(2), m.group(3)
            level = len(indent.replace("\t", "    ")) // 2 + 1
            bullet = "#" if re.match(r"\d+\.", marker) else "*"
            # чекбоксы markdown Confluence не понимает
            body = re.sub(r"^\[[ xX]\]\s*", "", body)
            out.append(bullet * level + " " + body)
            i += 1
            continue

        out.append(ln)
        i += 1

    if in_quote:
        out.append(quote_close)

    text = "\n".join(out)

    # инлайновая типографика (после блочной, до экранирования скобок)
    text = re.sub(r"\*\*([^*\n]+)\*\*", r"*\1*", text)          # жирный
    text = re.sub(r"(?<![\w*])_([^_\n]+)_(?![\w*])", r"_\1_", text)  # курсив

    # ссылки: markdown -> confluence, обе формы wikilink.
    # \x01 и \x02 — временные маркеры настоящих ссылок, чтобы их скобки
    # не попали под общее экранирование ниже. В шаблоне replace такие
    # escape-последовательности не работают, поэтому только через лямбду.
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]",
                  lambda m: "\x01" + m.group(2) + "|" + m.group(1) + "\x02", text)
    text = re.sub(r"\[\[([^\]]+)\]\]",
                  lambda m: "\x01" + m.group(1) + "\x02", text)
    text = re.sub(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)",
                  lambda m: "\x01" + m.group(1) + "|" + m.group(2) + "\x02", text)

    # ВСЕ оставшиеся квадратные И фигурные скобки -> сущности.
    # Квадратные Confluence читает как ссылку, фигурные — как вызов макроса,
    # причём неизвестный макрос валит запрос с HTTP 500.
    text = esc(text)

    # возвращаем скобки настоящим ссылкам и своим макросам
    text = text.replace("\x01", "[").replace("\x02", "]")
    text = re.sub(MACRO_MARK + r"(\d+)" + MACRO_MARK,
                  lambda m: macros[int(m.group(1))], text)

    # восстанавливаем inline-код; содержимое экранируется, обёртка {{...}}
    # добавляется уже после экранирования, поэтому сама не портится
    def restore_span(m):
        return "{{" + esc(spans[int(m.group(1))]) + "}}"

    text = re.sub(r"\x00SPAN(\d+)\x00", restore_span, text)

    # восстанавливаем код-блоки; их содержимое НЕ экранируется (уходит в CDATA).
    # mermaid — особый случай: сам Confluence его не рисует, поэтому вместо
    # кода вставляется отрисованный SVG (вложение diagram-N.svg, его кладёт
    # upload.py), а исходник убирается под {expand}, чтобы остался копируемым.
    counter = {"mermaid": 0}

    def restore_block(m):
        kind, lang, body = blocks[int(m.group(1))]
        code = ("{code:" + lang + "}" if lang else "{code}") + \
               "\n" + body.rstrip("\n") + "\n{code}"
        if lang.lower() == "mermaid":
            counter["mermaid"] += 1
            n = counter["mermaid"]
            return (f"!diagram-{n}.svg|width=900!\n"
                    "{expand:Исходник диаграммы (Mermaid)}\n" + code + "\n{expand}")
        return code

    text = re.sub(r"\x00BLOCK(\d+)\x00", restore_block, text)

    # три и более пустых строк подряд не нужны
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def split_title(md):
    """Отделяет frontmatter и H1. Возвращает (заголовок, тело)."""
    if md.startswith("---\n"):
        end = md.find("\n---", 4)
        if end != -1:
            md = md[end + 4:].lstrip("\n")
    m = re.match(r"^#\s+(.*)\n", md)
    if m:
        return m.group(1).strip(), md[m.end():]
    return "", md


if __name__ == "__main__":
    args = sys.argv[1:]
    only_title = "--title" in args
    if only_title:
        args.remove("--title")
    raw = open(args[0], encoding="utf-8").read()
    title, body = split_title(raw)
    if only_title:
        print(title)
    else:
        sys.stdout.write(convert(body))
