PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

CREATE TABLE artist (
    artist_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE,
    UNIQUE (name)
);

CREATE TABLE album (
    album_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL COLLATE NOCASE,
    release_year INTEGER,
    CHECK (release_year IS NULL OR release_year BETWEEN 1000 AND 9999),
    UNIQUE (title, release_year)
);

CREATE TABLE document (
    document_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    album_id INTEGER,
    genre TEXT,
    language TEXT NOT NULL DEFAULT 'English',
    release_year INTEGER,
    loaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (album_id) REFERENCES album (album_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CHECK (length(trim(title)) > 0),
    CHECK (length(trim(file_name)) > 0),
    CHECK (length(trim(file_path)) > 0),
    CHECK (release_year IS NULL OR release_year BETWEEN 1000 AND 9999),
    UNIQUE (file_path)
);

CREATE TABLE document_contributor (
    document_id INTEGER NOT NULL,
    artist_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    PRIMARY KEY (document_id, artist_id, role),
    FOREIGN KEY (document_id) REFERENCES document (document_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (artist_id) REFERENCES artist (artist_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CHECK (role IN ('PERFORMER', 'LYRICIST', 'COMPOSER'))
);

CREATE TABLE stanza (
    document_id INTEGER NOT NULL,
    stanza_no INTEGER NOT NULL,
    line_count INTEGER NOT NULL DEFAULT 0,
    word_count INTEGER NOT NULL DEFAULT 0,
    char_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (document_id, stanza_no),
    FOREIGN KEY (document_id) REFERENCES document (document_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CHECK (stanza_no >= 1),
    CHECK (line_count >= 0),
    CHECK (word_count >= 0),
    CHECK (char_count >= 0)
);

CREATE TABLE lyric_line (
    document_id INTEGER NOT NULL,
    stanza_no INTEGER NOT NULL,
    line_in_stanza INTEGER NOT NULL,
    global_line_no INTEGER NOT NULL,
    char_count INTEGER NOT NULL,
    word_count INTEGER NOT NULL,
    PRIMARY KEY (document_id, stanza_no, line_in_stanza),
    FOREIGN KEY (document_id, stanza_no)
        REFERENCES stanza (document_id, stanza_no)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CHECK (line_in_stanza >= 1),
    CHECK (global_line_no >= 1),
    CHECK (char_count >= 0),
    CHECK (word_count >= 0),
    UNIQUE (document_id, global_line_no),
    UNIQUE (document_id, stanza_no, line_in_stanza, global_line_no)
);

CREATE TABLE word (
    word_id INTEGER PRIMARY KEY,
    normalized_token TEXT NOT NULL COLLATE NOCASE,
    char_count INTEGER NOT NULL,
    CHECK (length(normalized_token) > 0),
    CHECK (char_count > 0),
    UNIQUE (normalized_token)
);

CREATE TABLE occurrence (
    occurrence_id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL,
    word_id INTEGER NOT NULL,
    stanza_no INTEGER NOT NULL,
    line_in_stanza INTEGER NOT NULL,
    global_line_no INTEGER NOT NULL,
    word_offset INTEGER NOT NULL,
    word_seq_in_doc INTEGER NOT NULL,
    FOREIGN KEY (word_id) REFERENCES word (word_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (document_id, stanza_no, line_in_stanza, global_line_no)
        REFERENCES lyric_line (
            document_id, stanza_no, line_in_stanza, global_line_no
        ) ON UPDATE CASCADE ON DELETE CASCADE,
    CHECK (word_offset >= 0),
    CHECK (word_seq_in_doc >= 0),
    UNIQUE (document_id, global_line_no, word_offset),
    UNIQUE (document_id, word_seq_in_doc)
);

CREATE TABLE word_group (
    group_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(trim(name)) > 0),
    UNIQUE (name)
);

CREATE TABLE word_group_member (
    group_id INTEGER NOT NULL,
    word_id INTEGER NOT NULL,
    PRIMARY KEY (group_id, word_id),
    FOREIGN KEY (group_id) REFERENCES word_group (group_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (word_id) REFERENCES word (word_id)
        ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE phrase (
    phrase_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(trim(name)) > 0),
    UNIQUE (name)
);

CREATE TABLE phrase_word (
    phrase_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    word_id INTEGER NOT NULL,
    PRIMARY KEY (phrase_id, position),
    FOREIGN KEY (phrase_id) REFERENCES phrase (phrase_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (word_id) REFERENCES word (word_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CHECK (position >= 0),
    UNIQUE (phrase_id, word_id, position)
);

CREATE INDEX idx_document_metadata
    ON document (genre, language, release_year);
CREATE INDEX idx_contributor_artist_role
    ON document_contributor (artist_id, role, document_id);
CREATE INDEX idx_occurrence_word_document
    ON occurrence (word_id, document_id, word_seq_in_doc);
CREATE INDEX idx_occurrence_document_position
    ON occurrence (document_id, stanza_no, line_in_stanza, word_offset);
CREATE INDEX idx_group_member_word
    ON word_group_member (word_id, group_id);
CREATE INDEX idx_phrase_word_word
    ON phrase_word (word_id, phrase_id, position);

COMMIT;