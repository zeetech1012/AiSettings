#!/usr/bin/env python3
"""Markdown → Jira wiki markup.

Консервативный конвертер: правила выведены из замеров порчи mcp-atlassian
(`~/.claude/skills/service-issue/jira/notes.md`). Что не переживает конвертацию —
не пытаемся сохранить любой ценой, а приводим к безопасной форме.

Порядок важен: код вырезается в плейсхолдеры первым, ссылки собираются до
инлайнового форматирования, HTML вычищается до всего остального.
"""
import re

CODE_MARK = "\x00CODE%d\x00"
LINK_MARK = "\x00LINK%d\x00"


def _strip_html(text):
    """Huly кладёт в markdown куски HTML — Jira их не рендерит."""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</?(?:span|div|p|font|u|em|strong|b|i)\b[^>]*>", "", text, flags=re.I)
    return text


def convert(md, link_map=None):
    """link_map: {старый_url: новый_url} — подмена ссылок (docmost → confluence)."""
    if not md:
        return ""
    text = md.replace("\r\n", "\n")
    codes, links = [], []

    # 1. блочный и инлайновый код — в плейсхолдеры
    def block(m):
        lang = (m.group(1) or "").strip()
        body = m.group(2)
        # решётка в начале строки внутри {code} читается как заголовок — сдвигаем
        body = re.sub(r"(?m)^#", " #", body)
        codes.append("{code%s}\n%s\n{code}" % (":" + lang if lang else "", body.rstrip("\n")))
        return CODE_MARK % (len(codes) - 1)

    text = re.sub(r"```(\w*)\n(.*?)```", block, text, flags=re.S)

    def inline(m):
        codes.append("{{%s}}" % m.group(1))
        return CODE_MARK % (len(codes) - 1)

    text = re.sub(r"`([^`\n]+)`", inline, text)

    text = _strip_html(text)

    # 2. ссылки — до инлайнового форматирования, иначе `_` в URL станет курсивом
    def sub_url(u):
        return (link_map or {}).get(u.rstrip("/"), u)

    def md_link(m):
        label, url = m.group(1).strip(), sub_url(m.group(2).strip())
        links.append(f"[{label}|{url}]" if label else f"[{url}]")
        return LINK_MARK % (len(links) - 1)

    text = re.sub(r"\[([^\]]*)\]\((https?://[^)\s]+)\)", md_link, text)

    def bare_url(m):
        links.append("[%s]" % sub_url(m.group(1)))
        return LINK_MARK % (len(links) - 1)

    text = re.sub(r"<(https?://[^>\s]+)>", bare_url, text)          # <url> — иначе Jira съест
    text = re.sub(r"(?<![|\[\x00])(https?://[^\s<>\)\]]+)", bare_url, text)

    # 3. блочные конструкции
    text = re.sub(r"(?m)^(#{1,6})\s+(.*)$", lambda m: "h%d. %s" % (len(m.group(1)), m.group(2)), text)
    text = re.sub(r"(?m)^\s*[-*+]\s+\[[ xX]\]\s+", "* ", text)       # чекбоксы не поддержаны
    text = re.sub(r"(?m)^(\s*)[-*+]\s+", lambda m: "*" * (len(m.group(1)) // 2 + 1) + " ", text)
    text = re.sub(r"(?m)^(\s*)\d+[.)]\s+", lambda m: "#" * (len(m.group(1)) // 2 + 1) + " ", text)
    text = re.sub(r"(?m)^>\s?(.*)$", r"bq. \1", text)
    text = re.sub(r"(?m)^\s*(?:---+|\*\*\*+|___+)\s*$", "----", text)

    # markdown-таблица → ||заголовок|| / |ячейка|
    def table(m):
        rows = [r for r in m.group(0).strip().split("\n") if r.strip()]
        out = []
        for i, row in enumerate(rows):
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            if i == 1 and all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                continue
            sep = "||" if i == 0 else "|"
            out.append(sep + sep.join(cells) + sep)
        return "\n".join(out)

    text = re.sub(r"(?m)^\|.*\|\s*$(?:\n^\|.*\|\s*$)+", table, text)

    # 4. инлайн: жирный/курсив (двойное экранирование ломает **, поэтому только одинарные)
    text = re.sub(r"\*\*([^*\n]+)\*\*", r"*\1*", text)
    text = re.sub(r"(?<![\w*])_([^_\n]+)_(?![\w*])", r"_\1_", text)

    # 5. плюсы = подчёркивание в wiki, схлопываются парами — прячем в monospace
    text = re.sub(r"(?<![{\w])\+{1}(?=\w)", "{{+}}", text)

    for i, l in enumerate(links):
        text = text.replace(LINK_MARK % i, l)
    for i, c in enumerate(codes):
        text = text.replace(CODE_MARK % i, c)
    return text.strip()


if __name__ == "__main__":
    import sys
    print(convert(sys.stdin.read()))
