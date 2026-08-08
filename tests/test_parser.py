from lyriconc.parser import parse_text


SAMPLE = """Title: Sample Song
Lyricist: A. Writer; B. Writer
Genre: Test

Line one of verse
Line two of verse

Chorus line one
Chorus line two
"""


def test_front_matter_is_extracted():
    parsed = parse_text(SAMPLE)
    assert parsed.metadata["title"] == "Sample Song"
    assert parsed.metadata["lyricists"] == ["A. Writer", "B. Writer"]
    assert parsed.metadata["genre"] == "Test"


def test_stanzas_and_lines_are_numbered():
    parsed = parse_text(SAMPLE)
    assert len(parsed.stanzas) == 2
    assert [s.line_count for s in parsed.stanzas] == [2, 2]

    first = parsed.stanzas[0].lines[0]
    assert first.stanza_no == 1
    assert first.line_in_stanza == 1
    assert first.global_line_no == 1
    assert [w.token for w in first.words] == ["line", "one", "of", "verse"]

    last = parsed.stanzas[1].lines[1]
    assert last.stanza_no == 2
    assert last.line_in_stanza == 2
    assert last.global_line_no == 4


def test_word_seq_in_doc_is_continuous():
    parsed = parse_text(SAMPLE)
    seq = [w.word_seq_in_doc for line in parsed.lines for w in line.words]
    assert seq == list(range(len(seq)))


def test_line_without_front_matter_is_body():
    parsed = parse_text("Chorus:\nHello world\n")
    assert parsed.metadata == {}
    assert len(parsed.stanzas) == 1
    assert parsed.stanzas[0].lines[0].text == "Chorus:"
