# LyriConc - Stage A Project Planning and Approval Request

**Course:** 20563 - Database Workshop, Spring 2026B  
**Project:** LyriConc - Song Lyrics Concordance and Text Retrieval  
**Students:** `[Student 1 name and ID]`, `[Student 2 name and ID]`  
**Submission date:** `[Date sent for approval]`  
**Requested database approval:** SQLite 3 instead of Oracle  
**Additional topic:** XML backup and restore

> Before submission, replace the bracketed student names, IDs, and submission
> date. No other section requires project-design input.

## 1. Project Description

LyriConc is a single-user desktop system that provides concordance and
text-retrieval services for a corpus of song lyric files. Each source document
is a UTF-8 plain-text `.txt` file representing one song. The application loads
multiple files, records song metadata, tokenizes their contents, and builds a
relational word-position index.

The system recognizes this document structure:

```text
song -> stanza -> lyric line -> word occurrence
```

A blank line separates stanzas. Each non-empty line is a lyric line. This
structure supplies the two position systems required by the project:

1. **Structural position:** stanza number, line within stanza, and word offset.
2. **Absolute position:** global lyric-line number and word sequence in the
   document.

The complete lyric text is not stored in the database. The database stores a
unique document ID, file path, metadata, aggregate counts, normalized words,
and occurrence positions. When context is requested, the Python service reads
the source file at `file_path`, applies the same parsing rules, selects nearby
lines, and highlights the requested occurrence.

The planned corpus contains 12-18 legally usable English-language songs. It
will contain only public-domain, open-licensed, self-written, or explicitly
permitted material. Source and license information will be recorded before the
final corpus is frozen.

## 2. Goals and Scope

The system will:

- Load and reload folders of lyric `.txt` files without duplicate rows.
- Store and edit song-specific metadata.
- Search by metadata or normalized lyric token.
- Produce word lists, concordance indexes, and context views.
- Resolve words from structural or absolute positions.
- Manage named word groups and ordered phrases.
- Export a group-specific index as TXT or CSV.
- Calculate line, stanza, song, and corpus statistics.
- Export all database rows to XML, recreate an empty database from SQL DDL,
  restore the XML rows, and verify the restored data.

The MVP is local and single-user. A web server, REST API, shared database,
cross-engine migration, charts, and advanced linguistic analysis are outside
scope.

## 3. Workbook Requirement Mapping

| # | Required service | Planned implementation |
|---|---|---|
| 1 | Load documents | A folder picker invokes a Python loader for all `.txt` files. |
| 2 | Enter structured data | Metadata editor for title, contributors and roles, album, genre, language, and year. |
| 3 | Retrieve documents | Parameterized searches by metadata and by normalized token. |
| 4 | Display all words | Frequency list for the whole corpus or one selected document. |
| 5 | Display word context | Resolve occurrence position, read nearby source-file lines, highlight the token, and navigate occurrences. |
| 6 | Word index and positions | Display stanza/line/offset and global line/document sequence. |
| 7 | Locate word by position | Position form returns the normalized token at the specified coordinates. |
| 8 | User-defined word groups | Create named groups and add/remove typed or selected words. |
| 9 | Linguistic expressions | Store ordered phrase tokens and find aligned consecutive `word_seq_in_doc` values. |
| 10 | Group index report | Display and export a selected group's occurrences to a named TXT or CSV file. |
| 11 | Statistics | Character and word counts by line, stanza, and song, plus word frequencies. |

## 4. Processing Rules

The following rules are fixed for consistent loading, searching, phrase
matching, and statistics:

- Input files are decoded as UTF-8; invalid files are reported and skipped.
- One or more blank lines delimit stanzas.
- Only non-empty lines receive lyric-line numbers.
- Tokens are normalized with Unicode-aware lowercase/case folding.
- Apostrophes inside a word are retained, so `don't` is one token.
- Hyphens split tokens, so `long-term` becomes `long` and `term`.
- Punctuation surrounding a token is discarded.
- Database `word_offset`, `word_seq_in_doc`, and `phrase_word.position` values
  are zero-based. The UI displays offsets as one-based and labels them.
- Character counts exclude newline characters. Word counts use this tokenizer.
- Reloading a known `file_path` replaces that document and its dependent rows
  in one transaction.

## 5. Architecture

```text
User
  -> PySide6 desktop screens
     -> Python service layer
        -> parameterized sqlite3 queries
           -> local lyriconc.db
        -> source .txt files for context display
        -> XML/TXT/CSV files for import and export
```

The PySide6 widgets contain no direct SQL. UI actions call service functions
that validate input, normalize tokens, manage transactions, execute the SQL,
and return display-ready records. This separation allows backend testing
without starting the interface.

## 6. Relational Design

The complete ER diagram is in [er_diagram.md](er_diagram.md), and executable DDL
is in [schema.sql](schema.sql).

| Relation | Purpose |
|---|---|
| `artist` | A performer, lyricist, composer, or band. |
| `album` | Optional album title and release year. |
| `document` | Song metadata and unique source-file path. |
| `document_contributor` | Many-to-many song/artist association with a role. |
| `stanza` | Numbered structural block and aggregate counts. |
| `lyric_line` | Numbered lyric line and aggregate counts, without lyric text. |
| `word` | One distinct normalized token. |
| `occurrence` | One token appearance with structural and absolute positions. |
| `word_group` | A user-defined named semantic group. |
| `word_group_member` | Many-to-many group/word membership. |
| `phrase` | A user-defined named ordered expression. |
| `phrase_word` | A word at an exact zero-based position in a phrase. |

### Main integrity constraints

- Primary keys uniquely identify every entity or association.
- `document.file_path`, `word.normalized_token`, group names, and phrase names
  are unique.
- Foreign keys preserve document, structure, vocabulary, group, and phrase
  relationships.
- Deleting a document cascades through contributors, stanzas, lines, and
  occurrences, which supports atomic reload.
- Contributor roles are restricted to performer, lyricist, and composer.
- Years and all counts/positions have valid ranges.
- Composite occurrence-to-line foreign keys ensure that stored stanza, line,
  and global-line coordinates describe the same lyric line.
- A document cannot contain two occurrences at the same line/offset or at the
  same document sequence number.

### Index strategy

| Index | Supports |
|---|---|
| `idx_document_metadata` | Genre/language/year filtering. |
| `idx_contributor_artist_role` | Artist and role searches. |
| `idx_occurrence_word_document` | Word search, frequency, concordance, and phrase candidates. |
| `idx_occurrence_document_position` | Structural lookup and ordered context navigation. |
| `idx_group_member_word` | Group-only concordance reports. |
| `idx_phrase_word_word` | Phrase token matching. |

SQLite automatically indexes primary-key and unique constraints in addition to
the explicit indexes above.

## 7. SQL Operations

The executable query appendix is [sample_queries.sql](sample_queries.sql). It
contains parameterized examples for:

1. Metadata search.
2. Document retrieval by word.
3. Global and per-document word frequencies.
4. Context-position resolution.
5. Concordance indexes with both position types.
6. Word lookup by position.
7. Word-group membership.
8. Group-only index export.
9. Stored phrase matching, including matches crossing lyric lines.
10. Line, stanza, and song statistics.
11. XML restore row-count verification.

All runtime values are bound parameters through Python `sqlite3`; values are
never concatenated into SQL strings.

## 8. User Interface Plan

The rendered screen mockups are in [ui_mockups.md](ui_mockups.md). The application
has five screens reached through a persistent left navigation area:

| Screen | Main controls | Functions |
|---|---|---|
| Library / Load | Folder picker, document table, metadata form, save/reload | 1-2 |
| Search + Concordance | Metadata filters, token search, frequency list, context pane, previous/next | 3-5 and phrase marking |
| Word Index + Position Lookup | Document filter, index grid, coordinate form | 6-7 |
| Groups, Phrases & Export | Group and phrase lists, membership controls, results, export | 8-10 |
| Statistics + XML Backup | Level filters, statistics tables, XML export/restore/verify | 11 and additional topic |

Standard Qt tables, forms, file dialogs, buttons, and a scrollable text pane
are sufficient. The MVP prioritizes complete behavior and readable validation
messages over custom styling.

## 9. Additional Topic: XML Backup and Restore

XML demonstrates database backup, structured data exchange, and reconstruction
from an external representation.

### Export format

The root is `lyriconcBackup` with an export timestamp and schema version. Each
table has one `table` element, and each record has one `row` element containing
named column children. SQL NULL values are represented explicitly with
`null="true"`.

```xml
<lyriconcBackup exportedAt="2026-07-19T12:00:00Z" schemaVersion="1">
  <table name="document">
    <row>
      <document_id>1</document_id>
      <title>Example Song</title>
      <file_path>data/corpus/example.txt</file_path>
    </row>
  </table>
</lyriconcBackup>
```

### Round-trip procedure

1. Record row counts for all 12 tables.
2. Export rows in foreign-key-safe order.
3. Recreate an empty database by executing `schema.sql`.
4. Import parent tables before child tables in one transaction:
   `artist`, `album`, `document`, `word`, `word_group`, `phrase`,
   `document_contributor`, `stanza`, `lyric_line`, `word_group_member`,
   `phrase_word`, `occurrence`.
5. Run `PRAGMA foreign_key_check`.
6. Compare all pre-export and post-restore row counts.
7. Repeat a word search, context lookup, and concordance query.

The SQL DDL remains the authoritative schema. XML contains data, not replacement
DDL. Cross-engine migration and an XSD are optional future extensions.

## 10. Technology Selection and Approval Request

| Part | Selection | Reason |
|---|---|---|
| Database | SQLite 3 | Relational constraints, transactions, indexes, portability, and no server dependency for a local single-user demo. |
| Language | Python 3.12 | Mature text processing, standard `sqlite3` and XML libraries, and straightforward automated testing. |
| UI | PySide6 / Qt | Native desktop tables, forms, navigation, text panes, and file dialogs. |
| Tests | pytest | Focused loader, query, phrase, statistics, and XML round-trip tests. |

**Approval requested:** The workbook specifies Oracle or another system with
coordinator approval. We request approval to use SQLite 3. The application is
single-user and local, so a database server does not add functional value.
SQLite supports the required relational model, foreign keys, check and unique
constraints, indexes, parameterized SQL, and transactions. SQL remains visible
in the submitted DDL and query appendix. If SQLite is not approved, the schema
and service boundary allow migration to PostgreSQL with limited type and
auto-generated-key changes.

## 11. Corpus and Copyright Plan

- Corpus target: 12-18 `.txt` song files in `data/corpus/`.
- Allowed sources: public domain, open license, student-authored, or explicit
  permission.
- A corpus manifest will record title, source URL or author, license/permission,
  and retrieval date.
- Raw lyrics will not be committed or distributed when permission does not
  allow redistribution.
- The application stores only paths, metadata, normalized vocabulary,
  positions, and counts in the database.

## 12. Responsibility Split

### Student 1 - database and service layer

- DDL, reset flow, loader, tokenizer, and reload transaction.
- Parameterized retrieval, index, lookup, context, statistics, groups, and
  phrase queries.
- XML table ordering and backend verification helpers.
- Backend automated tests.

### Student 2 - UI, reporting, and XML workflow

- PySide6 shell and all five screens.
- Context highlighting and occurrence navigation.
- Group/phrase controls and TXT/CSV report export.
- XML export/restore UI and verification report.
- Final screenshots, slides, and demonstration script.

Both students review the schema, integrate weekly from a clean database, write
the final report, and present the system.

## 13. Schedule

| Week | Goal | Exit criterion |
|---|---|---|
| 0 | Planning and approval | Coordinator approves topic, SQLite, schema, and XML topic. |
| 1 | Schema, parser, loader, app shell | Fresh DB loads 3-5 sample songs. |
| 2 | Retrieval and statistics | Functions 1-4, 6-7, and 11 operate through UI. |
| 3 | Context, groups, phrases, export | Functions 5 and 8-10 operate through UI. |
| 4 | XML and corpus freeze | 12-18 legal songs load; XML round trip passes. |
| 5 | Report and rehearsal | Clean full demonstration succeeds. |
| 6 | Buffer | Only blocking fixes and label corrections. |

No new functionality will be added after Week 4.

## 14. Main Risks and Mitigations

| Risk | Mitigation |
|---|---|
| SQLite is not approved | Keep SQL portable and migrate through the service layer if required. |
| Copyright restrictions | Use only documented legal sources and keep a manifest. |
| Source paths become invalid | Copy approved files into the managed corpus folder before loading. |
| Tokenization differs across features | Use one shared tokenizer for loading, searching, phrases, and statistics. |
| Phrase matching fails across lines | Use continuous `word_seq_in_doc` and automated cross-line tests. |
| XML import violates foreign keys | Recreate from DDL, import in dependency order, use one transaction, and run FK verification. |
| UI work consumes implementation time | Use standard Qt widgets until every required function works. |
| Demo data becomes inconsistent | Maintain a clean reset/load flow and rehearse from an empty database. |

## 15. Requested Approvals

Please confirm approval of:

1. Song lyrics as the selected text type.
2. The proposed schema and two position systems.
3. SQLite 3 as the database instead of Oracle.
4. XML backup/restore as the additional course topic.
5. The described corpus and copyright approach.

Implementation will proceed after planning approval, as required by the course
workbook.

## 16. Suggested Submission Email

**To:** hilak@openu.ac.il  
**Subject:** Course 20563 - LyriConc project planning approval

Hello Hila,

Attached is our Stage A planning document for LyriConc, a song-lyrics
concordance and text-retrieval system. The document includes the project
description, ER diagram, SQL DDL and constraints, sample SQL, and UI wireframes.

We request approval to use SQLite 3 instead of Oracle for this local single-user
desktop application, and to implement XML backup/restore as the additional
course topic. We will use only legally permitted lyric files and will keep the
full text outside the database.

Students: `[Student 1 name and ID]`, `[Student 2 name and ID]`

Thank you.
