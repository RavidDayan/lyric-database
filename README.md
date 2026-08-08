# LyriConc

Stage A planning package for course 20563, Database Workshop.

LyriConc is a planned desktop concordance and text-retrieval system for song
lyrics. It uses SQLite 3, Python 3.12, PySide6, and XML backup/restore. Complete
lyric text remains in source files; the relational database stores metadata,
normalized words, positions, groups, phrases, and statistics.

## Stage A Deliverables

- [Planning and approval packet](stage-a/approval_packet.md)
- [Entity-relationship diagram](stage-a/er_diagram.md)
- [SQLite schema](stage-a/schema.sql)
- [Sample SQL queries](stage-a/sample_queries.sql)
- [Rendered UI mockups](stage-a/ui_mockups.md)
- [Submission checklist](stage-a/README.md)

The downloadable source bundle is [LyriConc-Stage-A.zip](LyriConc-Stage-A.zip).

## Status

Stage A planning is complete and Stage B implementation is in place:

- SQLite schema, loader, tokenizer, parser, service layer, XML backup/restore.
- PySide6 desktop app with 5 screens covering all 11 workbook functions plus
  the XML additional topic.
- `pytest` suite (tokenizer, parser, services, XML round-trip, UI smoke test).

The two student names/IDs and submission date remain placeholders in the
approval packet until the coordinator approves the plan, SQLite use, and XML
additional topic.

## Running

```powershell
# One-time setup
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# Launch the desktop app
.\.venv\Scripts\python -m lyriconc

# Run the test suite
$env:QT_QPA_PLATFORM='offscreen'; .\.venv\Scripts\python -m pytest
```

On first launch use the *Library / Load* tab to point at `data/corpus/` (or any
folder of `.txt` lyric files) and click **Load folder**.
