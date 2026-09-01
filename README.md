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

### Windows: double-click launcher

Double-click **Run LyriConc.cmd** in the project folder. On first use, the
launcher creates `.venv` and installs LyriConc and its required packages. Later
launches open the application directly. Python 3.11 or newer must already be
installed on the computer.

### PowerShell

```powershell
# One-time setup
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .

# Launch the desktop app
.\.venv\Scripts\python -m lyriconc

# Run the test suite
$env:QT_QPA_PLATFORM='offscreen'; .\.venv\Scripts\python -m pytest
```

On first launch use the *Library / Load* tab to point at `data/corpus/` (or any
folder of `.txt` lyric files) and click **Load folder**.

## Web App

The simple, read-only Streamlit site lets visitors browse the bundled corpus,
search for words and their context, and view statistics.

### Run locally

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\streamlit run streamlit_app.py
```

Open `http://localhost:8501` in a browser.

### Deploy for free

1. Push the project to GitHub.
2. Sign in at `https://share.streamlit.io` with GitHub.
3. Create an app using this repository and choose `streamlit_app.py` as the
  entry point.
4. Click **Deploy** and share the generated `streamlit.app` URL.

Streamlit Community Cloud installs `requirements.txt` and loads the bundled
files in `data/corpus/` automatically. No secrets or database setup are needed.
