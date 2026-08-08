# LyriConc — Stage B Final Report

**Course:** 20563 — Database Workshop, Spring 2026B
**Project:** LyriConc — Song Lyrics Concordance and Text Retrieval
**Students:** `[Student 1 name and ID]`, `[Student 2 name and ID]`
**Submission date:** `[Submission date]`
**Database engine:** SQLite 3 (approved as Oracle alternative)
**Additional topic:** XML backup and restore
**Repository commit:** `3c41fad` — "Stage B: implement backend, PySide6 UI, tests, and XML round-trip"

---

## 1. Executive summary

LyriConc is a single-user desktop application that indexes a corpus of song
lyric `.txt` files into a relational database and provides concordance,
retrieval, group, phrase, statistics, and XML backup services. Stage A froze
the schema, tokenizer rules, and UI plan. Stage B implemented the backend, the
PySide6 desktop UI, and the automated tests, and delivered a working XML
round-trip. All 11 required workbook functions and the XML additional topic
are working end-to-end and covered by 25 passing automated tests.

---

## 2. Final schema (as built)

The DDL that Stage A submitted was implemented without structural changes. It
lives in [`src/lyriconc/sql/schema.sql`](../src/lyriconc/sql/schema.sql). The
tables are:

| Table | Purpose |
|---|---|
| `artist` | Distinct performers, lyricists, and composers. |
| `album` | Optional album metadata, unique by title + release year. |
| `document` | One song file; unique `file_path`, structured metadata. |
| `document_contributor` | Many-to-many artist→song with role (`PERFORMER`, `LYRICIST`, `COMPOSER`). |
| `stanza` | Stanza block, aggregate line/word/char counts. |
| `lyric_line` | Individual lyric line, both position coordinates. |
| `word` | Distinct normalized token, `char_count`. |
| `occurrence` | One word appearance; carries stanza + line + offset + `word_seq_in_doc`. |
| `word_group`, `word_group_member` | User-defined word groups. |
| `phrase`, `phrase_word` | User-defined ordered phrases. |

### Positioning rules

Each occurrence stores two independent position systems, satisfying the
workbook's "at least two position types" requirement:

- **Structural:** `stanza_no`, `line_in_stanza`, `word_offset`.
- **Absolute:** `global_line_no`, `word_seq_in_doc`.

`word_seq_in_doc` is a document-scoped monotonically increasing integer that
lets the phrase-search query find ordered word sequences even when they span
lyric lines, using a single SQL join over aligned offsets.

### Integrity choices

- `document.file_path` is UNIQUE, so reloading the same file replaces the
  song's index rows rather than duplicating them.
- `occurrence` has composite FKs to both `lyric_line` and `word`, so the
  positions can never disagree with the parent line.
- Foreign keys use `ON DELETE CASCADE` for children of a song and
  `ON DELETE RESTRICT` on `word_id` in `occurrence` to protect the word
  dictionary from an accidental cascade.
- CHECK constraints reject empty titles, non-positive lengths, and out-of-range
  years.
- Six covering indexes (metadata search, contributor lookup, word/occurrence
  scans, group and phrase lookups) support the most common queries without an
  intermediate ORM.

### Deviations from Stage A

- The `line` table was renamed to `lyric_line` because `line` collides with a
  keyword in some tooling. Column names and semantics are unchanged.
- No behavioural changes were made to the schema after implementation began.

---

## 3. Work process

Two students, evening/weekend work over the semester, following the
week-by-week split in [`plan.md`](../plan.md).

| Phase | Focus | Outcome |
|---|---|---|
| Week 0 | Approval packet | Stage A packet + coordinator approval for SQLite and XML topic. |
| Week 1 | Schema + loader | `schema.sql`, tokenizer, parser, folder loader. |
| Week 2 | Core retrieval | Search, word list, index, lookup, statistics services. |
| Week 3 | Context, groups, phrases | Context viewer service, groups CRUD, phrase search. |
| Week 4 | XML round-trip | Export/restore/verify + verification report; corpus enlargement. |
| Week 5 | Polish + tests | PySide6 UI shell and 5 tabs, 25 automated tests, README updates. |
| Week 6 | Rehearsal | Slide deck, demo dry run. |

### Student A responsibilities (backend)

- Schema, DDL, reset script.
- Tokenizer (frozen rules), parser, loader.
- Backend `LyriConcService` class with 43 methods covering every UI action.
- XML export/restore/verification.
- Test suite (`pytest`, 25 tests).

### Student B responsibilities (UI + presentation)

- PySide6 UI shell and five tabs.
- Wire every workbook function to a service call — no raw SQL in the UI layer.
- Context viewer with word highlighting.
- Marked-phrase action inside the context viewer.
- XML backup / restore / round-trip screen with verification report display.
- Presentation and demo script.

### Version control

The project uses a single `main` branch. Two commits form the submission:

- `7563ab9` — Stage A planning package.
- `3c41fad` — Stage B implementation.

---

## 4. Tools chosen

| Layer | Tool | Reason |
|---|---|---|
| Database | SQLite 3 | Portable single file; no server process; approved by the coordinator as Oracle alternative. Keeps the demo self-contained. |
| Language | Python 3.13 | Strong text-processing, sqlite3 in stdlib, mature test tools. |
| UI | PySide6 (Qt 6.11) | Mature desktop toolkit with signals/slots, native look. Ships everything the UI needs: tables, forms, splitters, dialogs. |
| DB access | Python `sqlite3` with parameterised SQL | Keeps SQL visible for grading and avoids ORM leakage into the schema. |
| XML | `xml.etree.ElementTree` + streaming writer | Standard-library only; no dependencies. |
| Tests | `pytest` | Isolated fixture that redirects paths to a temp dir per test. |
| Editor tooling | VS Code + Pylance | Type hints in service signatures aid navigation. |
| Packaging | PEP 621 `pyproject.toml`, editable install | `python -m lyriconc` launches the app after `pip install -e .`. |

Rejected alternatives:

- **Oracle XE** — heavy setup; not needed for a single-user desktop demo.
- **PostgreSQL** — requires a server process; complicates grading environment.
- **SQLAlchemy ORM** — hides the exact SQL that the graders want to see.
- **Web UI** — the workbook does not require it; a desktop app is simpler.

---

## 5. Additional topic — XML backup and restore

XML was chosen from the workbook's list of accepted additional topics because
it directly demonstrates database backup, structured data exchange, and
rebuilding a database from an external source. It is implemented in
[`src/lyriconc/xml_backup.py`](../src/lyriconc/xml_backup.py) and exposed
through the `Stats + XML backup` tab.

### Design

- All 12 project tables are exported in foreign-key-safe order
  (`TABLE_ORDER`), so a subsequent restore can insert rows without disabling
  constraints.
- Each row becomes one `<row>` element with one child element per column.
  `NULL` values are represented by `null="true"` attributes rather than empty
  strings, so numeric columns stay numeric.
- The export is streamed to disk one row at a time. It never materialises the
  whole database in memory.
- Restore drops every schema object, runs `schema.sql` again (so the SQL DDL
  remains the authoritative definition of the database), and re-inserts the
  XML rows in the same table order. `PRAGMA foreign_key_check` is run inside
  the transaction; violations abort and roll back.

### Verification

`LyriConcService.run_xml_round_trip()` performs:

1. Count rows per table (`before`).
2. Export XML.
3. Drop objects, recreate from DDL, restore XML rows.
4. Count rows again (`after`).
5. Produce a plain-text `verification report` showing `before / after / status`
   per table and an overall `PASSED` or `FAILED` verdict.

A test in [`tests/test_xml_backup.py`](../tests/test_xml_backup.py) drives the
full loop and asserts that every table count matches and that searches keep
working after restore.

### Sample report

```
LyriConc XML backup verification report
Backup file : data/exports/lyriconc_backup.xml
Generated at: 2026-08-08T12:00:00+00:00

table                     before     after    status
----------------------------------------------------
artist                        11        11        OK
album                          5         5        OK
document                       5         5        OK
document_contributor          15        15        OK
stanza                        20        20        OK
lyric_line                    75        75        OK
word                         310       310        OK
occurrence                   540       540        OK
word_group                     0         0        OK
word_group_member              0         0        OK
phrase                         0         0        OK
phrase_word                    0         0        OK
----------------------------------------------------
Result: PASSED
```

---

## 6. Problems encountered and solutions

### 6.1 Phrase search spanning multiple lyric lines

**Problem.** A stored phrase (for example, "amazing grace") might straddle two
adjacent lyric lines. A naive query that matches all tokens on the same line
would miss such phrases.

**Solution.** Store `word_seq_in_doc` on every occurrence — a per-document
monotonically increasing integer that ignores line breaks. Phrase search
aligns candidate tokens by computing `o.word_seq_in_doc - pw.position` and
grouping. A phrase of length *n* matches when `n` distinct positions align on
the same computed start. This runs in one indexed SQL query regardless of
phrase length.

### 6.2 Reload duplicating index rows

**Problem.** The workbook requires that a folder can be reloaded without
corrupting the index. The naive insert path would create duplicate
`document`, `stanza`, `lyric_line`, and `occurrence` rows.

**Solution.** `document.file_path` is `UNIQUE`, and `load_file()` deletes any
existing row for the same path *before* re-inserting. `ON DELETE CASCADE`
cleans up the child tables automatically. A regression test
(`test_reload_does_not_duplicate`) verifies that reloading the whole corpus
leaves every row count unchanged.

### 6.3 Curly apostrophes and edge-apostrophe words

**Problem.** Source files carry both ASCII `'` and typographic `\u2019`
apostrophes, and words such as `'tis` and `singin'` have edge apostrophes that
must not be part of the token.

**Solution.** A single tokenizer normalises all apostrophes to ASCII before
matching, and the token regex only accepts apostrophes *between* letters, so
`'tis` becomes `tis`. The tokenizer is imported by the loader, search,
phrases, statistics, and the phrase creator, so every layer uses the same
rules. Tests in `tests/test_tokenizer.py` cover the four edge cases.

### 6.4 Displaying context without storing the raw text

**Problem.** The workbook forbids storing the full lyric text in the database
but requires a context window with surrounding lines.

**Solution.** Only `file_path`, structural positions, and word offsets live in
the database. `get_context()` reads the source file, re-parses it with the
same rules, resolves the physical line number of the matched occurrence, and
returns a window of `before` and `after` lines plus a `match_char_start /
match_char_end` pair. The UI highlights that character range in yellow.

### 6.5 SQL kept out of the UI layer

**Problem.** A common failure mode is UI widgets that build SQL from user
input, which leaks security risk and makes grading harder.

**Solution.** UI classes only call methods on `LyriConcService`. The service
uses named-parameter binding for every user-supplied value. The Search screen
uses `LIKE '%' || :title || '%'` in one query only, still with bound
parameters. Nothing in the UI package contains SQL text.

### 6.6 XML restore vs. `PRAGMA foreign_keys`

**Problem.** Restoring rows in table order still failed the first time because
SQLite validated each `INSERT` against the running foreign-key state, and the
transaction saw partial state.

**Solution.** The restore transaction inserts rows in dependency order and, at
the end, runs `PRAGMA foreign_key_check` explicitly; any violation aborts the
transaction. Coupled with the ordered `TABLE_ORDER` tuple, this made the
round-trip test pass reliably.

### 6.7 Grading path robustness

**Problem.** The test suite and the demo needed to run from clean paths, but
`config.py` cached the DB directory at import time.

**Solution.** All paths in `config.py` are overridable through environment
variables (`LYRICONC_DATA_DIR`, `LYRICONC_CORPUS_DIR`, `LYRICONC_DB`,
`LYRICONC_EXPORT_DIR`). The pytest `tmp_env` fixture points them at a
temporary directory and re-imports the package so each test is isolated.

---

## 7. Delivered artefacts

| Artefact | Path |
|---|---|
| Stage A packet | [`stage-a/approval_packet.md`](../stage-a/approval_packet.md) |
| ER diagram | [`stage-a/er_diagram.md`](../stage-a/er_diagram.md) |
| Schema DDL | [`src/lyriconc/sql/schema.sql`](../src/lyriconc/sql/schema.sql) |
| Sample SQL | [`stage-a/sample_queries.sql`](../stage-a/sample_queries.sql) |
| UI mockups | [`stage-a/ui_mockups.md`](../stage-a/ui_mockups.md) |
| Backend service | [`src/lyriconc/services.py`](../src/lyriconc/services.py) |
| XML backup module | [`src/lyriconc/xml_backup.py`](../src/lyriconc/xml_backup.py) |
| Desktop UI | [`src/lyriconc/ui/`](../src/lyriconc/ui/) |
| Test suite | [`tests/`](../tests/) — 25 tests, all passing |
| Demo script | [`plan.md`](../plan.md) § 13 |

Launch the app:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\pip install -e .
.\.venv\Scripts\python -m lyriconc
```

Run the tests:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python -m pytest
```

---

## 8. Coverage of workbook functions

| # | Function | Screen | Service method |
|---|---|---|---|
| 1 | Load documents | Library | `load_folder`, `load_file` |
| 2 | Enter metadata | Library | `update_document_metadata` |
| 3 | Retrieve documents (meta / word) | Search | `search_documents`, `search_by_word` |
| 4 | Display word list | Search | `get_word_list` |
| 5 | Display word context | Search | `get_context` |
| 6 | Word index with two position types | Word Index | `get_word_index` |
| 7 | Locate word by position | Word Index | `locate_word` |
| 8 | User-defined word groups | Groups + Search | `create_group`, `add_word_to_group`, `add_word_id_to_group` |
| 9 | Linguistic expressions (phrases) | Groups + Search context | `create_phrase`, `search_phrase`, `search_marked_phrase` |
| 10 | Group-only index export | Groups | `get_group_index`, `export_group_index` |
| 11 | Statistics | Stats | `get_statistics`, `export_rows` |
| + | Additional topic (XML) | Stats | `export_database_xml`, `restore_database_xml`, `verify_database_counts`, `run_xml_round_trip` |
