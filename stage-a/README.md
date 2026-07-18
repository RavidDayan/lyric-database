# LyriConc Stage A Submission Bundle

This folder contains the completed planning and approval package required before
implementation.

## Files

- [approval_packet.md](approval_packet.md) - main planning document and approval
  request.
- [er_diagram.md](er_diagram.md) - Mermaid entity-relationship diagram and
  cardinality notes.
- [schema.sql](schema.sql) - executable SQLite DDL, constraints, and indexes.
- [sample_queries.sql](sample_queries.sql) - parameterized SQL examples for the
  required functions.
- [ui_mockups.md](ui_mockups.md) - five rendered application screen mockups.
- `ui-library.png`, `ui-search.png`, `ui-index.png`, `ui-groups.png`, and
  `ui-stats.png` - full-size desktop mockup images.
- `render_mockups.html` - reproducible source used to render the mockup images.

## Before Sending

1. Replace the student names and IDs on lines 5 and 349 of
   `approval_packet.md`.
2. Replace the submission date on line 6 of `approval_packet.md`.
3. Render the Markdown files to PDF if the coordinator requires PDF rather than
   source Markdown.
4. Send the bundle to `hilak@openu.ac.il` using the email draft at the end of
   `approval_packet.md`.
5. Wait for approval of the plan, SQLite, and XML topic before implementation.

## Validation Result

The schema and query appendix were validated with Python's SQLite driver:

- 12 schema tables and 6 explicit indexes created successfully.
- All 12 sample SQL statements executed successfully.
- Foreign-key validation returned no issues.
- Unique, check, and occurrence-coordinate constraints rejected invalid data.
- A stored three-word phrase matched across two lyric lines.
- Song statistics returned exact seeded totals without join overcounting.
- All local links in the Markdown bundle resolve.