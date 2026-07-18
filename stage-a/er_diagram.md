# LyriConc Entity-Relationship Diagram

The diagram reflects the executable schema in [schema.sql](schema.sql). Full
lyric lines are deliberately absent: `lyric_line` stores positions and counts,
and `document.file_path` points to the source text used for context display.

```mermaid
erDiagram
    ALBUM o|--o{ DOCUMENT : contains
    DOCUMENT ||--o{ DOCUMENT_CONTRIBUTOR : credits
    ARTIST ||--o{ DOCUMENT_CONTRIBUTOR : contributes
    DOCUMENT ||--o{ STANZA : has
    STANZA ||--o{ LYRIC_LINE : contains
    DOCUMENT ||--o{ OCCURRENCE : indexes
    LYRIC_LINE ||--o{ OCCURRENCE : locates
    WORD ||--o{ OCCURRENCE : appears_as
    WORD_GROUP ||--o{ WORD_GROUP_MEMBER : contains
    WORD ||--o{ WORD_GROUP_MEMBER : belongs_to
    PHRASE ||--|{ PHRASE_WORD : orders
    WORD ||--o{ PHRASE_WORD : composes

    ARTIST {
        integer artist_id PK
        text name UK
    }

    ALBUM {
        integer album_id PK
        text title
        integer release_year
    }

    DOCUMENT {
        integer document_id PK
        text title
        text file_name
        text file_path UK
        integer album_id FK
        text genre
        text language
        integer release_year
        text loaded_at
    }

    DOCUMENT_CONTRIBUTOR {
        integer document_id PK, FK
        integer artist_id PK, FK
        text role PK
    }

    STANZA {
        integer document_id PK, FK
        integer stanza_no PK
        integer line_count
        integer word_count
        integer char_count
    }

    LYRIC_LINE {
        integer document_id PK, FK
        integer stanza_no PK, FK
        integer line_in_stanza PK
        integer global_line_no UK
        integer char_count
        integer word_count
    }

    WORD {
        integer word_id PK
        text normalized_token UK
        integer char_count
    }

    OCCURRENCE {
        integer occurrence_id PK
        integer document_id FK
        integer word_id FK
        integer stanza_no FK
        integer line_in_stanza FK
        integer global_line_no FK
        integer word_offset
        integer word_seq_in_doc
    }

    WORD_GROUP {
        integer group_id PK
        text name UK
        text description
        text created_at
    }

    WORD_GROUP_MEMBER {
        integer group_id PK, FK
        integer word_id PK, FK
    }

    PHRASE {
        integer phrase_id PK
        text name UK
        text created_at
    }

    PHRASE_WORD {
        integer phrase_id PK, FK
        integer position PK
        integer word_id FK
    }
```

## Cardinality Notes

- A document may belong to zero or one album; an album may contain many songs.
- Artists and documents have a many-to-many relationship resolved by
  `document_contributor`, whose role distinguishes performers, lyricists, and
  composers.
- A document has ordered stanzas, each stanza has ordered lyric lines, and each
  line has zero or more indexed occurrences.
- One normalized word may appear in many documents and positions.
- Words and user groups have a many-to-many relationship.
- A phrase contains one or more ordered phrase-word rows. A vocabulary word may
  participate in many phrases.
