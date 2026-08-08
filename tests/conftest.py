"""Shared pytest fixtures for the LyriConc test suite."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def tmp_env(tmp_path, monkeypatch):
    """Redirect all LyriConc data paths to a temporary directory."""
    data = tmp_path / "data"
    corpus = data / "corpus"
    exports = data / "exports"
    corpus.mkdir(parents=True)
    exports.mkdir(parents=True)

    monkeypatch.setenv("LYRICONC_DATA_DIR", str(data))
    monkeypatch.setenv("LYRICONC_CORPUS_DIR", str(corpus))
    monkeypatch.setenv("LYRICONC_DB", str(data / "lyriconc.db"))
    monkeypatch.setenv("LYRICONC_EXPORT_DIR", str(exports))

    # config caches paths at import time - reload after env is patched.
    for name in list(sys.modules):
        if name.startswith("lyriconc"):
            del sys.modules[name]

    import lyriconc.config as config

    return {
        "data": data,
        "corpus": corpus,
        "exports": exports,
        "db": config.DATABASE_PATH,
    }


@pytest.fixture()
def corpus_env(tmp_env):
    """Copy the checked-in corpus into the temporary corpus folder."""
    real_corpus = ROOT / "data" / "corpus"
    for txt in real_corpus.glob("*.txt"):
        shutil.copy(txt, tmp_env["corpus"] / txt.name)
    return tmp_env


@pytest.fixture()
def service(corpus_env):
    from lyriconc.services import LyriConcService

    svc = LyriConcService()
    svc.reset_db()
    svc.load_folder(corpus_env["corpus"])
    yield svc
    svc.close()
