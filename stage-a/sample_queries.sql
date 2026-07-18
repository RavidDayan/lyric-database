-- LyriConc Stage A sample queries
-- Parameters use Python sqlite3 named-parameter syntax.

-- 1. Retrieve documents by structured metadata and optional contributor.
SELECT DISTINCT
    d.document_id,
    d.title,
    d.genre,
    d.language,
    d.release_year,
    d.file_path
FROM document AS d
LEFT JOIN document_contributor AS dc ON dc.document_id = d.document_id
LEFT JOIN artist AS a ON a.artist_id = dc.artist_id
WHERE (:title IS NULL OR d.title LIKE '%' || :title || '%')
  AND (:genre IS NULL OR d.genre = :genre)
  AND (:language IS NULL OR d.language = :language)
  AND (:artist IS NULL OR a.name LIKE '%' || :artist || '%')
ORDER BY d.title;

-- 2. Retrieve documents containing a normalized word.
SELECT
    d.document_id,
    d.title,
    COUNT(*) AS occurrence_count
FROM word AS w
JOIN occurrence AS o ON o.word_id = w.word_id
JOIN document AS d ON d.document_id = o.document_id
WHERE w.normalized_token = :token
GROUP BY d.document_id, d.title
ORDER BY occurrence_count DESC, d.title;

-- 3. Global or per-document word-frequency list.
SELECT
    w.word_id,
    w.normalized_token,
    COUNT(*) AS frequency
FROM word AS w
JOIN occurrence AS o ON o.word_id = w.word_id
WHERE (:document_id IS NULL OR o.document_id = :document_id)
GROUP BY w.word_id, w.normalized_token
ORDER BY frequency DESC, w.normalized_token;

-- 4. Resolve one occurrence for context display. Python reads the original
-- file and displays lines around global_line_no; lyric text is not in the DB.
SELECT
    o.occurrence_id,
    d.title,
    d.file_path,
    w.normalized_token,
    o.stanza_no,
    o.line_in_stanza,
    o.global_line_no,
    o.word_offset
FROM occurrence AS o
JOIN document AS d ON d.document_id = o.document_id
JOIN word AS w ON w.word_id = o.word_id
WHERE o.occurrence_id = :occurrence_id;

-- 5. Concordance index with structural and absolute positions.
SELECT
    w.normalized_token,
    d.title,
    o.stanza_no,
    o.line_in_stanza,
    o.global_line_no,
    o.word_offset
FROM occurrence AS o
JOIN word AS w ON w.word_id = o.word_id
JOIN document AS d ON d.document_id = o.document_id
WHERE (:document_id IS NULL OR o.document_id = :document_id)
ORDER BY w.normalized_token, d.title, o.word_seq_in_doc;

-- 6. Locate a word from a displayed 1-based offset. The database stores
-- word_offset as zero-based, so the service subtracts one from the UI value.
SELECT
    w.normalized_token,
    o.global_line_no,
    o.word_seq_in_doc
FROM occurrence AS o
JOIN word AS w ON w.word_id = o.word_id
WHERE o.document_id = :document_id
  AND o.stanza_no = :stanza_no
  AND o.line_in_stanza = :line_in_stanza
  AND o.word_offset = :zero_based_word_offset;

-- 7. Add an existing normalized word to a user-defined group.
INSERT INTO word_group_member (group_id, word_id)
SELECT :group_id, word_id
FROM word
WHERE normalized_token = :token
ON CONFLICT (group_id, word_id) DO NOTHING;

-- 8. Group-only index for display or TXT/CSV export.
SELECT
    g.name AS group_name,
    w.normalized_token,
    d.title,
    o.stanza_no,
    o.line_in_stanza,
    o.global_line_no,
    o.word_offset
FROM word_group AS g
JOIN word_group_member AS gm ON gm.group_id = g.group_id
JOIN word AS w ON w.word_id = gm.word_id
JOIN occurrence AS o ON o.word_id = w.word_id
JOIN document AS d ON d.document_id = o.document_id
WHERE g.group_id = :group_id
ORDER BY w.normalized_token, d.title, o.word_seq_in_doc;

-- 9. Find all occurrences of a stored phrase. Subtracting phrase position
-- from document sequence aligns every token on the same candidate start.
SELECT
    d.document_id,
    d.title,
    o.word_seq_in_doc - pw.position AS start_word_seq,
    MIN(o.global_line_no) AS first_line,
    MAX(o.global_line_no) AS last_line
FROM phrase_word AS pw
JOIN occurrence AS o ON o.word_id = pw.word_id
JOIN document AS d ON d.document_id = o.document_id
WHERE pw.phrase_id = :phrase_id
GROUP BY d.document_id, d.title, o.word_seq_in_doc - pw.position
HAVING COUNT(DISTINCT pw.position) = (
    SELECT COUNT(*)
    FROM phrase_word
    WHERE phrase_id = :phrase_id
)
ORDER BY d.title, start_word_seq;

-- 10. Statistics per lyric line.
SELECT
    d.title,
    l.stanza_no,
    l.line_in_stanza,
    l.global_line_no,
    l.char_count,
    l.word_count
FROM lyric_line AS l
JOIN document AS d ON d.document_id = l.document_id
WHERE (:document_id IS NULL OR l.document_id = :document_id)
ORDER BY d.title, l.global_line_no;

-- 11. Statistics per stanza and song.
SELECT
    d.document_id,
    d.title,
    (
        SELECT COUNT(*) FROM stanza AS s
        WHERE s.document_id = d.document_id
    ) AS stanza_count,
    (
        SELECT COUNT(*) FROM lyric_line AS l
        WHERE l.document_id = d.document_id
    ) AS line_count,
    (
        SELECT COUNT(*) FROM occurrence AS o
        WHERE o.document_id = d.document_id
    ) AS word_count,
    (
        SELECT COALESCE(SUM(l.char_count), 0) FROM lyric_line AS l
        WHERE l.document_id = d.document_id
    ) AS character_count
FROM document AS d
WHERE (:document_id IS NULL OR d.document_id = :document_id)
ORDER BY d.title;

-- 12. Verification counts recorded before XML export and after restore.
SELECT 'artist' AS table_name, COUNT(*) AS row_count FROM artist
UNION ALL SELECT 'album', COUNT(*) FROM album
UNION ALL SELECT 'document', COUNT(*) FROM document
UNION ALL SELECT 'document_contributor', COUNT(*) FROM document_contributor
UNION ALL SELECT 'stanza', COUNT(*) FROM stanza
UNION ALL SELECT 'lyric_line', COUNT(*) FROM lyric_line
UNION ALL SELECT 'word', COUNT(*) FROM word
UNION ALL SELECT 'occurrence', COUNT(*) FROM occurrence
UNION ALL SELECT 'word_group', COUNT(*) FROM word_group
UNION ALL SELECT 'word_group_member', COUNT(*) FROM word_group_member
UNION ALL SELECT 'phrase', COUNT(*) FROM phrase
UNION ALL SELECT 'phrase_word', COUNT(*) FROM phrase_word;