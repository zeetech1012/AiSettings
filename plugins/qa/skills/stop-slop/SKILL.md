---
name: stop-slop
description: Убирает из прозы характерные AI-паттерны письма. Используй при написании, редактировании или ревью текста, чтобы устранить предсказуемые «AI-tells».
metadata:
  trigger: Написание прозы, редактирование черновиков, ревью текста на AI-паттерны
  author: Hardik Pandya (https://hvpandya.com)
---

# Stop Slop

Eliminate predictable AI writing patterns from prose.

## Core Rules

1. **Cut filler phrases.** Remove throat-clearing openers, emphasis crutches, and all adverbs. See [references/phrases.md](references/phrases.md).

2. **Break formulaic structures.** Avoid binary contrasts, negative listings, dramatic fragmentation, rhetorical setups, false agency. See [references/structures.md](references/structures.md).

3. **Use active voice.** Every sentence needs a human subject doing something. No passive constructions. No inanimate objects performing human actions ("the complaint becomes a fix").

4. **Be specific.** No vague declaratives ("The reasons are structural"). Name the specific thing. No lazy extremes ("every," "always," "never") doing vague work.

5. **Put the reader in the room.** No narrator-from-a-distance voice. "You" beats "People." Specifics beat abstractions.

6. **Vary rhythm.** Mix sentence lengths. Two items beat three. End paragraphs differently. No em dashes.

7. **Trust readers.** State facts directly. Skip softening, justification, hand-holding.

8. **Cut quotables.** If it sounds like a pull-quote, rewrite it.

## Quick Checks

Before delivering prose:

- Any adverbs? Kill them.
- Any passive voice? Find the actor, make them the subject.
- Inanimate thing doing a human verb ("the decision emerges")? Name the person.
- Sentence starts with a Wh- word? Restructure it.
- Any "here's what/this/that" throat-clearing? Cut to the point.
- Any "not X, it's Y" contrasts? State Y directly.
- Three consecutive sentences match length? Break one.
- Paragraph ends with punchy one-liner? Vary it.
- Em-dash anywhere? Remove it.
- Vague declarative ("The implications are significant")? Name the specific implication.
- Narrator-from-a-distance ("Nobody designed this")? Put the reader in the scene.
- Meta-joiners ("The rest of this essay...")? Delete. Let the essay move.

## Scoring

Rate 1-10 on each dimension:

| Dimension | Question |
|-----------|----------|
| Directness | Statements or announcements? |
| Rhythm | Varied or metronomic? |
| Trust | Respects reader intelligence? |
| Authenticity | Sounds human? |
| Density | Anything cuttable? |

Below 35/50: revise.

## Examples

See [references/examples.md](references/examples.md) for before/after transformations.

## Русскоязычная проза (командные правила)

Дополнительно к правилам выше — для текста на русском (документация, баг-репорты, тикеты, заметки):

1. **Без гибридных транслитераций-жаргонизмов.** Не писать «дедуп», «синк», «репро», «пуш», «коннект», «флоу». Либо полное русское слово (дедупликация, синхронизация, воспроизведение), либо оригинальный английский термин латиницей (dedup, sync, push) — но не русское окончание на урезанном английском корне.
2. **Без сленга и сокращений ролей.** «разраб» → «разработчик»; роли называть полностью (разработчик, QA-инженер, администратор рабочего пространства, владелец репозитория).
3. **Формальные документы — нейтрально, без первого лица.** Не «мой набор», «я сделал», «снято с моей машины». Безличные или ролевые формулировки: «набор включает», «выполняется».
4. **Технические термины — в оригинале латиницей** (MCP, token, config, commit, merge request), не транслитерировать кириллицей.
5. **Структура объяснения подхода/инструмента (по запросу):** зачем → что решает → если есть проблема → решение.
6. **Контуры и стенды в документах — формальными названиями.** Не «боевое облако», «боевой контур», «прод», «продакшен»,
   «живой стенд», «домик». Словарь: `prod` → «производственный контур облачной платформы <компании>» (далее по тексту —
   «производственный контур»); `staging` → «предпроизводственный контур»; `test` → «тестовый контур»; станция или УСПД →
   «испытательный стенд: УСПД ‹обозначение›, bs_id ‹номер›»; станция, передающая данные в облако, → «подключена к
   производственному контуру облачной платформы». Технические имена контуров (`prod`, `uspd`, `<COMPANY>_CONTOUR`) остаются в
   коде, профилях и командах; в прозе документов (ПМИ, протокол, тикет, письмо) — только формальное название.

## License

MIT
