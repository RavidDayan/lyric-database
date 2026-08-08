---
title: "LyriConc"
subtitle: "Song Lyrics Concordance & Text Retrieval"
author: "Course 20563 — Database Workshop, Spring 2026B"
---

<!--
Rendering options:

* Preview in VS Code (Ctrl+K V) - reads as ordinary markdown.
* Convert to slides with Marp:
    marp stage-b/slides.md -o stage-b/slides.pdf
  or with Pandoc + Beamer / reveal.js.

Each `---` line marks the boundary between slides.
Speaker cues are in italics under each bullet list.
-->

# LyriConc
### Song Lyrics Concordance & Text Retrieval

Course 20563 — Database Workshop, Spring 2026B

`[Student 1 name and ID]` · `[Student 2 name and ID]`

Submission: `[Date]`

*Opening (30 s): "We built a desktop concordance system for song lyrics.
SQLite, Python, PySide6, XML backup as the additional topic. Everything runs
locally from one command."*

---

## Agenda

1. Schema
2. Work process
3. Tools chosen
4. Additional topic — XML backup/restore
5. Problems & solutions
6. Live demo

*Mention: this deck matches the five bullets required by the workbook,
plus the demo.*

---

## 1. Schema — Core idea

**song → stanza → lyric line → word occurrence**

- 12 tables, all built from a single frozen `schema.sql`
- Raw lyric text is **never** stored — only file path + index rows
- Each occurrence carries **two** independent position systems
  - Structural: `stanza_no`, `line_in_stanza`, `word_offset`
  - Absolute: `global_line_no`, `word_seq_in_doc`

*This is the "at least two position types" the workbook explicitly requires.*

---

## 1. Schema — Highlights

- `document.file_path` **UNIQUE** → safe reload without duplicates
- Composite FK from `occurrence` to `lyric_line` — positions can't drift from
  the parent line
- `ON DELETE CASCADE` for children of a song, `RESTRICT` on the word
  dictionary
- CHECK constraints reject empty titles, negative counts, absurd years
- 6 covering indexes tuned to the actual query paths

*Show the ER diagram slide next.*

---

## 1. Schema — ER diagram

![ER diagram](../stage-a/er_diagram.md)

*Point to the two edges into `occurrence` — this is where the two
position systems meet.*

---

## 2. Work process

- Two students, evening/weekend work over 6 weeks
- Weekly checkpoints from [plan.md](../plan.md)
- Student A owned backend + tests
- Student B owned UI + presentation + XML round-trip UX
- Single `main` branch, two commits: Stage A, Stage B

**Cadence per week:** design → implement → test → demo dry-run

*Emphasise: contract between A and B was frozen early —
`LyriConcService` has 43 methods, and the UI never writes SQL.*

---

## 3. Tools chosen

| Layer | Tool | Why |
|---|---|---|
| DB | SQLite 3 | Approved as Oracle alt; single file; demo-safe |
| Lang | Python 3.13 | Text handling + sqlite3 in stdlib |
| UI | PySide6 (Qt 6.11) | Native desktop widgets, no browser |
| DB access | `sqlite3` + bound params | Grader sees the actual SQL |
| XML | `xml.etree.ElementTree` | Stdlib only, no dependency |
| Tests | `pytest` | 25 tests, temp-dir fixtures |

*Rejected: Oracle XE (heavy), Postgres (server), SQLAlchemy (hides SQL),
web UI (unnecessary).*

---

## 4. Additional topic — XML backup/restore

**Goal:** demonstrate DB backup, external exchange, and rebuild-from-file.

Three actions, one file:

1. **Export** — every table → one `<lyriconcBackup>` XML file, streamed.
2. **Restore** — drop all objects, run `schema.sql`, re-insert rows in
   foreign-key-safe order.
3. **Verify** — count rows before/after and produce a plain-text report.

*Key point: XML **does not replace** the SQL DDL. The DDL stays the
authoritative source of the schema.*

---

## 4. XML — round-trip verification

```
table                     before     after    status
----------------------------------------------------
artist                        11        11        OK
document                       5         5        OK
lyric_line                    75        75        OK
word                         310       310        OK
occurrence                   540       540        OK
...
Result: PASSED
```

- One click in the Stats tab runs the entire round-trip.
- Automated test drives the same flow (`test_xml_round_trip_preserves_counts`).

*The demo will run this live in ~2 seconds against the loaded corpus.*

---

## 5. Problems & solutions (1/2)

**Phrase spans multiple lines**
→ Store `word_seq_in_doc` per occurrence; align `o.word_seq_in_doc - pw.position`.

**Reload duplicates rows**
→ `file_path` UNIQUE + delete-then-insert; cascade cleans children.

**Curly vs. ASCII apostrophes; `'tis`, `singin'`**
→ Single tokenizer normalises apostrophes and only accepts them *between* letters.

*Each fix has a regression test.*

---

## 5. Problems & solutions (2/2)

**Context without storing raw text**
→ Only `file_path` in DB; service re-reads and highlights on demand.

**SQL leaking into UI**
→ UI calls `LyriConcService` methods only; every value is bound.

**Restore vs. running foreign-key state**
→ Ordered `TABLE_ORDER` + final `PRAGMA foreign_key_check`; rollback on any violation.

**Path caching across tests**
→ Env-var overrides + fixture that reimports the package per test.

---

## 6. Live demo — 10 minutes

1. **Reset DB** from the Library tab (clean slate).
2. **Load** `data/corpus/` (5 songs, expandable).
3. **Edit metadata** on one song → save.
4. **Search** by artist / genre / word → context view with highlighted match.
5. **Word index** — show both position systems + reverse lookup.
6. **Group** = {grace, love}; add from Search word list; export TXT.
7. **Phrase** "amazing grace" — find matches; mark phrase from context.
8. **Statistics** by document + word frequency.
9. **XML round-trip** — export → restore → verification report.

*End state proves the DB rebuilt itself from the XML file and still answers queries.*

---

## Summary

- 11/11 workbook functions implemented and demoed.
- Additional topic (XML) implemented, tested, and instrumented with a
  verification report.
- Schema kept minimal and explicit; no ORM hiding it.
- 25 automated tests pass; UI covered by a smoke test.
- One command starts the app (`python -m lyriconc`).

**Repository state at submission:** commit `2491b92`, main branch.

*Thank you — happy to take questions.*

---

## Backup slide — Function ↔ code map

| Function | Screen | Service |
|---|---|---|
| Load / metadata | Library | `load_folder`, `update_document_metadata` |
| Search (meta + word) | Search | `search_documents`, `search_by_word` |
| Word list + context | Search | `get_word_list`, `get_context` |
| Index + lookup | Word Index | `get_word_index`, `locate_word` |
| Groups + phrases | Groups + Search | `add_word_id_to_group`, `search_phrase` |
| Group export | Groups | `export_group_index` |
| Statistics | Stats | `get_statistics` |
| XML | Stats | `run_xml_round_trip` |
