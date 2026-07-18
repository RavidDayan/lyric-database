# LyriConc Project Planning

**Project:** LyriConc - song lyrics concordance and text-retrieval system  
**Course:** 20563 - Database Workshop  
**Selected topic:** Song lyrics  
**Final stack:** SQLite 3, Python 3.12, PySide6 desktop UI, XML backup/restore  
**Planning status:** Active project plan  

---

## 1. Final project definition

LyriConc is a desktop concordance and text-retrieval system for a small corpus of song lyric text files.

Each input document is a plain `.txt` file representing one song. The system parses every song into:

```text
song -> stanza -> line -> word occurrence
```

In lyrics, a **stanza** means a verse/chorus block: a group of lyric lines separated from the next group by a blank line. For example:

```text
Line 1 of verse
Line 2 of verse

Line 1 of chorus
Line 2 of chorus
```

This example has two stanzas. Stanza structure is useful because the workbook requires two position types, and lyrics naturally provide them:

- Structural position: stanza number + line inside stanza.
- Absolute position: global line number + word offset inside the line.

The database stores structured metadata and word-position index data. It does **not** store the full lyric text. The original text remains on disk, and the database keeps only `file_path` so the app can read the relevant lines when showing context.

The project must demonstrate all 11 required workbook functions and one additional topic. The selected additional topic is **XML backup/restore**. The system will export the database content to an XML file, rebuild an empty database from the SQL schema, restore the data from XML, and verify that the restored database matches the original data counts.

---

## 2. Requirement summary

The requirement source is:

- `plan\projectRequriments.md`

The project must include:

| Requirement | LyriConc implementation |
|---|---|
| Multiple plain-text files | Load a folder of `.txt` lyric files. |
| Unique document IDs | `document.document_id` plus unique `file_path`. |
| Full text not stored | Store metadata, file path, words, and occurrences only. |
| Type-specific metadata | Title, performers, lyricists, composers, album, genre, language, release year. |
| Two position types | Structural: stanza + line in stanza. Absolute: global line + word offset. |
| User interface | One PySide6 desktop application. |
| Additional topic | XML backup/restore and data exchange. |
| Planning deliverables | Description, ER diagram, DDL, sample SQL, UI mockups, engine justification. |
| Final deliverables | Written document, working system, live demo, slides. |

---

## 3. Technology decisions

| Part | Technology | Reason |
|---|---|---|
| Database | SQLite 3 | Mainstream, simple, portable, no server setup. Must be approved as Oracle alternative. |
| Language | Python 3.12 | Good for text parsing, SQLite access, tests, and XML import/export. |
| UI | PySide6 / Qt | Desktop UI with tables, forms, file picker, scrollable context pane, exports. |
| DB access | Python `sqlite3` with parameterized SQL | Keeps SQL visible for grading; avoids ORM complexity. |
| Additional topic | XML backup/restore | Easy to explain, strongly connected to the database schema, and useful for backup/data exchange. |
| Exports | `.txt`, `.csv`, and `.xml` | `.txt`/`.csv` for reports, `.xml` for the additional topic. |
| Tests | `pytest` | Focus on loader, query, phrase search, and XML round-trip correctness. |

---

## 4. Application architecture

LyriConc is a **single-user local desktop application**, not a client-server system.

There is no web server, no REST API, and no always-running backend process. The visible PySide6 UI and the hidden Python application logic run inside the same desktop program. The SQLite database is a local `.db` file used by that program.

```text
User
  -> PySide6 desktop screens/buttons/forms
     -> internal Python service functions
        -> sqlite3 SQL queries
           -> local SQLite database file
        -> lyric .txt files on disk for context display
```

When the user clicks a button, the UI calls an internal Python function. That function performs application logic, such as validation, tokenization, file reading, XML export/restore, and deciding which SQL query to run. SQLite stores data and answers SQL queries; it is not responsible for all business logic.

Example flow:

```text
User clicks "Search word" and enters "love"
  -> PySide6 calls search_by_word("love")
  -> Python normalizes the token
  -> Python runs a parameterized SELECT query
  -> SQLite returns matching documents/positions
  -> Python formats the result
  -> UI displays the matching songs and context
```

This means each installation normally has its own app, its own local SQLite DB file, and its own lyric corpus folder:

```text
User A computer: LyriConc app + lyriconc.db + data\corpus\
User B computer: LyriConc app + lyriconc.db + data\corpus\
```

The system does not automatically share live data between users. If data needs to move between computers, the XML backup/restore feature can be used:

```text
User A exports XML -> User B imports XML
```

This architecture is intentional for the course project because it keeps the implementation simple and demo-safe. A multi-user version would require a different architecture:

```text
web/mobile UI -> API server -> shared DB server
```

That multi-user architecture is out of scope for the MVP.

### Layer responsibilities

| Layer | Responsibility |
|---|---|
| PySide6 UI | Screens, buttons, forms, tables, user interaction, showing results. |
| Python service layer | App logic: validation, tokenization, file reading, XML export/restore, and choosing SQL queries. |
| SQLite DB | Store structured metadata/index rows and answer SQL queries. |
| Lyric files on disk | Store the original full text; DB keeps only `file_path`. |

---

## 5. Key planning decisions

These are part of the plan itself, not reviewer notes.

| Decision | Project choice |
|---|---|
| DB engine | SQLite 3, with coordinator approval as an Oracle alternative. |
| Corpus | 12-18 legal lyric `.txt` files: public-domain, open-licensed, self-written, or explicitly permitted. |
| Full-text rule | The database stores only file path, metadata, words, and positions; raw lyrics stay in files. |
| Lyric structure | Blank line separates stanzas; each non-empty line is a lyric line. |
| Position types | Structural: stanza + line in stanza. Absolute: global line + word offset. |
| Statistics mapping | Line = sentence/page-like unit, stanza = chapter-like unit, song = file. |
| Additional topic | XML backup/restore of the database content. |
| XML scope | Export/import the same SQLite project data; no cross-engine migration in the MVP. |
| UI scope | One PySide6 desktop app only. |
| Tokenization | Freeze one tokenizer before loading the final corpus. |

---

## 6. Core database model

The schema is centered on the concordance index.

| Entity | Purpose |
|---|---|
| `artist` | Performer, lyricist, composer, or band. |
| `album` | Optional album metadata. |
| `document` | One song lyric file. Stores title, filename, filepath, genre, language, optional album. |
| `document_contributor` | Many-to-many link between song and artist with role. |
| `stanza` | Structural block inside a song. |
| `line` | One lyric line with `line_in_stanza`, `global_line_no`, `char_count`, `word_count`. |
| `word` | Distinct normalized token. |
| `occurrence` | One word appearance with both position types and `word_seq_in_doc`. |
| `word_group` | User-defined named group of words. |
| `word_group_member` | Words included in a group. |
| `phrase` | Stored multi-word expression. |
| `phrase_word` | Ordered words inside a phrase. |

### Most important schema rules

1. `document.file_path` is unique.
2. Raw lyric text is never stored in a table.
3. `occurrence` stores:
   - `stanza_no`
   - `line_in_stanza`
   - `global_line_no`
   - `word_offset`
   - `word_seq_in_doc`
4. `word_seq_in_doc` is computed during loading in document order and is used for cross-line phrase search.
5. XML backup/restore does not replace the SQL schema. The SQL DDL remains the source used to create the database, and XML is used to export/import the data.

---

## 7. Required functions and implementation plan

| # | Workbook function | Implementation |
|---|---|---|
| 1 | Load documents | Folder picker loads `.txt` files; backend parses and inserts metadata/index rows. |
| 2 | Enter metadata | UI form edits title, artist roles, album, genre, language, year. |
| 3 | Retrieve documents | Search by metadata or by token appearing in lyrics. |
| 4 | Display word list | Show global or per-document word frequency list. |
| 5 | Display word context | Click word occurrence; DB returns positions; app reads nearby lines from file path and highlights word. |
| 6 | Word index with positions | Grid shows token with structural and absolute positions. |
| 7 | Locate word by position | User enters document, stanza, line, offset; query returns the word. |
| 8 | User word groups | Create/edit groups and add words by typing or from UI selection. |
| 9 | Linguistic expressions | Store phrases and search consecutive `word_seq_in_doc` positions; support marked phrase from context pane. |
| 10 | Group index export | Export occurrences for a selected group to named `.txt` or `.csv` file. |
| 11 | Statistics | Show counts per line, stanza, song, and word-frequency lists. |

---

## 8. Student responsibility split

The split is balanced so both students own important technical work.

### Student A - database foundation, loader, and core queries

Student A owns the database correctness and the core data services that all screens depend on.

| Task block | What to do | Deliverable | Acceptance criteria |
|---|---|---|---|
| A1 Schema | Write `schema.sql` with tables, constraints, and indexes. | SQL schema file. | Fresh DB can be created with no errors; FK, UNIQUE, CHECK constraints work. |
| A2 Reset script | Create reset/recreate DB flow. | `reset_db()` or script. | Demo can start from clean DB without manual SQL. |
| A3 Corpus folder | Define managed corpus location. | Agreed folder structure. | Context display still works after restart. |
| A4 Tokenizer | Define lowercase, punctuation, apostrophe, hyphen, contraction rules. | Tokenizer function and documentation. | Same tokenization used by loader, search, phrases, and statistics. |
| A5 Loader | Load songs as stanza/line/word occurrence rows. | `load_folder(path)`. | 3 songs, then 12-18 songs load correctly. |
| A6 Reload/delete | Prevent duplicate rows on reload. | Delete-and-reload by `file_path`. | Reload same file does not duplicate occurrences. |
| A7 Query API | Implement parameterized functions for search, lists, indexes, stats. | Backend service module. | UI can call functions without writing SQL. |
| A8 Context contract | Return occurrence IDs, document path, and line ranges. | `get_context(...)`. | UI can show surrounding text without DB storing full text. |
| A9 Phrase search | Search stored and marked phrases using `word_seq_in_doc`. | `search_phrase(tokens)`. | Cross-line phrase test passes. |
| A10 Groups SQL | Create groups, add/remove members, group index query. | Group service functions. | Group index query returns only group words. |
| A11 XML schema support | Define table export order and restore order based on foreign keys. | XML table-order helper and restore contract. | Empty DB can be recreated before XML import. |
| A12 Tests | Test risky backend logic. | `pytest` tests. | Loader, reload, phrase search, stats, and XML restore tests pass. |

### Student B - UI, XML backup/restore, reporting, documentation, demo

Student B owns the user-facing app and the XML additional topic workflow. Student A provides DB helpers, but Student B owns the export/restore user flow and verification report.

| Task block | What to do | Deliverable | Acceptance criteria |
|---|---|---|---|
| B1 UI mockups | Draw Load/Metadata, Concordance, Word Index screens. | 3 wireframes for planning packet. | Evaluator can map screens to workbook functions. |
| B2 App shell | Build PySide6 app with navigation and five empty screens. | Desktop app skeleton. | App opens reliably. |
| B3 Library screen | Folder picker, loaded songs table, metadata editor. | Library/Load screen. | Functions 1-2 demo with 3 songs. |
| B4 Search screen | Metadata search, word search, word list. | Search + Concordance screen. | Functions 3-4 demoable. |
| B5 Context viewer | Scrollable pane, highlight word, next/previous occurrence. | Context UI. | Function 5 demoable. |
| B6 Index screen | Word index grid and position lookup form. | Word Index + Lookup screen. | Functions 6-7 pass on known positions. |
| B7 Groups screen | Group CRUD, add word, phrase form, marked phrase action. | Groups/Phrases screen. | Functions 8-9 demoable. |
| B8 Export | Named group-index export. | Export dialog. | Function 10 creates named `.txt` or `.csv`. |
| B9 Stats screen | Line/stanza/song stats, frequency list. | Stats table UI. | Function 11 demoable. |
| B10 XML backup/restore | Export database to XML, restore from XML, show verification counts. | XML screen/action and report. | Export -> reset DB -> restore -> verify succeeds. |
| B11 Slides | Prepare 5-7 final slides. | Slide deck. | Covers schema, process, tools, XML backup/restore, problems/solutions. |
| B12 Demo script | Script the 10-minute walkthrough. | Demo checklist. | Clean reset -> load -> all 11 functions + XML round-trip in under 10 minutes. |

---

## 9. Integration contract

Student B must not write direct SQL inside UI widgets. Student A exposes a backend service layer.

Minimum service API:

```python
reset_db()
load_folder(path: str, metadata_defaults: dict | None = None)
list_documents()
update_document_metadata(document_id: int, metadata: dict)

search_documents(filters: dict)
search_by_word(token: str)

get_word_list(document_ids: list[int] | None = None)
get_occurrences(word_id: int, document_id: int | None = None)
get_context(occurrence_id: int, before: int = 3, after: int = 3)

get_word_index(document_id: int | None = None)
locate_word(document_id: int, stanza_no: int, line_in_stanza: int, word_offset: int)

create_group(name: str)
add_word_to_group(group_id: int, token: str)
remove_word_from_group(group_id: int, token: str)
get_group_index(group_id: int)
export_group_index(group_id: int, output_path: str, format: str)

create_phrase(name: str, tokens: list[str])
search_phrase(tokens: list[str])
search_marked_phrase(document_id: int, start_word_seq: int, length: int)

get_statistics(level: str, document_id: int | None = None)

export_database_xml(output_path: str)
restore_database_xml(input_path: str)
verify_database_counts()
export_xml_verification_report(output_path: str)
```

Contract decisions to freeze before coding:

1. Are UI offsets displayed as 0-based or 1-based? Recommended: store 0-based, display 1-based with labels.
2. How are contractions tokenized? Recommended: keep apostrophes inside words, so `don't` is one token.
3. How are hyphenated words tokenized? Recommended: split on hyphen unless the coordinator approves otherwise.
4. What XML file structure is used? Recommended: one root element, one element per table, and one child element per row.
5. What restore order is used? Recommended: parent tables first (`artist`, `album`, `document`), then child tables (`stanza`, `line`, `occurrence`, groups, phrases).
6. Where is the managed corpus folder? Recommended: `data\corpus\`, ignored from Git if copyright status is unclear.

---

## 10. UI screen plan

Build exactly five MVP screens.

| Screen | Functions covered | What it contains |
|---|---|---|
| 1. Library / Load | 1, 2 | Folder picker, loaded songs table, metadata editor. |
| 2. Search + Concordance | 3, 4, 5, part of 9 | Metadata search, word search, word list, context viewer, marked phrase action. |
| 3. Word Index + Position Lookup | 6, 7 | Word index grid, document filter, position lookup form. |
| 4. Groups, Phrases & Export | 8, 9, 10 | Group manager, phrase manager, group index export. |
| 5. Statistics + XML Backup | 11, additional topic | Line/stanza/song stats, frequency list, XML export/restore/verify actions. |

Implementation rule: use basic Qt widgets first (`QTableView`, forms, buttons, text pane). Do not build charts, custom widgets, or styling until all required functions work.

---

## 11. XML backup/restore plan

XML is the additional topic. It directly demonstrates database backup, data exchange, and rebuilding the database from an external file.

### What XML does in this project

The system exports the database data to a file such as:

```text
lyriconc_backup.xml
```

The XML file contains the project tables as structured data. It does not replace the SQL DDL. The restore process is:

1. Export current database rows to XML.
2. Drop/recreate the SQLite database using `schema.sql`.
3. Import rows back from XML in foreign-key-safe order.
4. Verify the restored database by comparing row counts and sample queries.

### XML file structure

Recommended structure:

```xml
<lyriconcBackup exportedAt="2026-07-14">
  <table name="artist">
    <row>
      <artist_id>1</artist_id>
      <name>Example Artist</name>
    </row>
  </table>
  <table name="document">
    <row>
      <document_id>1</document_id>
      <title>Example Song</title>
      <file_path>data\corpus\example.txt</file_path>
    </row>
  </table>
</lyriconcBackup>
```

An optional `lyriconc_backup.xsd` can be added if time allows, but the MVP only requires the XML export/import/restore flow to work.

### XML acceptance criteria

- Export creates a readable `.xml` file.
- Restore recreates the database from SQL DDL, then imports XML rows.
- Foreign keys remain valid after restore.
- Verification report compares row counts before and after restore.
- After restore, the app can still search documents, display word context, and show word indexes.
- The demo shows the XML round-trip clearly: export -> reset -> restore -> verify.

---

## 12. Week-by-week plan

Assume both students have full-time jobs. Plan for focused evening work plus one weekend integration session.

| Week | Goal | Student A | Student B | Exit checkpoint |
|---|---|---|---|---|
| Week 0 | Approval packet | Final schema draft, SQL samples, approval notes. | UI mockups, screen map, approval text. | Packet ready for coordinator. |
| Week 1 | Schema + loader | DB create/reset, tokenizer, load 3-5 songs. | PySide6 shell, Library/Load screen. | Clean DB can load sample songs. |
| Week 2 | Core retrieval | Search, word list, index, lookup, stats API. | Search, Word List, Index, Stats screens. | Functions 1-4, 6-7, 11 work. |
| Week 3 | Context/groups/phrases | Context query, group queries, phrase search. | Context pane, groups/phrases/export UI. | Functions 5, 8-10 work. |
| Week 4 | XML backup/restore + corpus freeze | Restore order, XML import helpers, verification queries. | XML export/restore actions and verification report. | 12-18 songs loaded; XML round-trip succeeds. |
| Week 5 | Documentation + rehearsal | DDL/query appendix, reset script, backend fixes. | Slides, screenshots, demo script. | Full demo rehearsal succeeds. |
| Week 6 | Buffer only | Blocking bugs only. | Blocking bugs only, UI labels only. | Demo under 10 minutes from clean reset. |

No new features after Week 4.

---

## 13. Demo script

Use this exact safe path for the live demo:

1. Reset database.
2. Load the fixed corpus folder.
3. Edit metadata for one song.
4. Search songs by artist/genre.
5. Search songs by a word.
6. Show corpus word list.
7. Select a word and show surrounding context.
8. Page through next/previous occurrences.
9. Show word index with both position types.
10. Enter a known position and locate the word.
11. Create/open a word group and add a word.
12. Define or mark a phrase and find other occurrences.
13. Export group index to a named file.
14. Show line/stanza/song statistics.
15. Export database to XML.
16. Reset/recreate the database.
17. Restore data from XML.
18. Show verification counts and repeat one search/index query after restore.

Target duration: under 10 minutes.

---

## 14. Main risks and mitigations

| Risk | Mitigation |
|---|---|
| Copyrighted lyrics | Use public-domain, open-licensed, self-written, or explicitly permitted corpus. |
| SQLite not approved | Keep schema SQL portable; fallback to PostgreSQL only if required. |
| File paths become stale | Use a managed corpus folder and do not move files after loading. |
| Tokenization mismatch | Freeze tokenizer before UI and final corpus loading. |
| Phrase search bugs | Base phrase matching on `word_seq_in_doc`; test cross-line phrase. |
| XML restore order bugs | Import parent tables before child tables and keep foreign keys enabled during verification. |
| XML scope creep | Do backup/restore only; do not attempt cross-engine migration unless everything else is complete. |
| PySide6 consumes time | Use simple tables/forms first; no custom visual polish before MVP. |
| Optional theme/difficulty causes scope creep | Hide/defer until all 11 functions work. |
| Backend/UI schema drift | Use one service API; weekly integration from clean DB. |
| Demo failure | Maintain reset/load script and rehearse twice. |

---

## 15. Phase A approval packet checklist

Include:

- Project description.
- ER diagram.
- Full SQL DDL.
- Index list and constraint explanation.
- Sample SQL for major functions.
- UI mockups for at least 3 screens.
- Technology justification.
- SQLite approval request.
- XML backup/restore additional-topic request.
- Corpus source/legal explanation.
- Student A/B responsibility split.
- Timeline and demo plan.

---

## 16. Final decision

Proceed with LyriConc using:

```text
SQLite 3 + Python 3.12 + PySide6 + XML backup/restore
```

This is the cleanest implementation path for two students because it keeps the database schema visible, avoids deployment complexity, satisfies all required functions, and gives a clear XML backup/restore demo.