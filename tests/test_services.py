def test_load_folder_loads_all_files(service, corpus_env):
    docs = service.list_documents()
    txt_count = len(list(corpus_env["corpus"].glob("*.txt")))
    assert len(docs) == txt_count
    assert all(row["title"] for row in docs)


def test_reload_does_not_duplicate(service, corpus_env):
    before = service.verify_database_counts()
    service.load_folder(corpus_env["corpus"])
    after = service.verify_database_counts()
    assert before == after


def test_search_by_word(service):
    hits = service.search_by_word("grace")
    assert hits, "'grace' should occur in Amazing Grace"
    assert any("Amazing Grace" == row["title"] for row in hits)


def test_word_list_sorted_by_frequency(service):
    words = service.get_word_list()
    frequencies = [row["frequency"] for row in words]
    assert frequencies == sorted(frequencies, reverse=True)


def test_get_context_returns_matching_line(service):
    word_id = service.get_word_id("grace")
    occurrences = service.get_occurrences(word_id)
    context = service.get_context(occurrences[0]["occurrence_id"], before=2, after=2)
    matching = [line for line in context["lines"] if line["is_match"]]
    assert len(matching) == 1
    assert "grace" in matching[0]["text"].lower()


def test_word_index_positions(service):
    rows = service.get_word_index()
    for row in rows:
        assert row["word_position"] >= 1
        assert row["global_line_no"] >= 1
        assert row["stanza_no"] >= 1


def test_locate_word_roundtrip(service):
    word_id = service.get_word_id("grace")
    occurrence = service.get_occurrences(word_id)[0]
    found = service.locate_word(
        document_id=occurrence["document_id"],
        stanza_no=occurrence["stanza_no"],
        line_in_stanza=occurrence["line_in_stanza"],
        word_offset=occurrence["word_position"],
    )
    assert found is not None
    assert found["normalized_token"] == "grace"


def test_groups_add_remove_and_index(service):
    group_id = service.create_group("emotions")
    assert service.add_word_to_group(group_id, "grace") is True
    assert service.add_word_to_group(group_id, "love") is True

    words = service.list_group_words(group_id)
    tokens = {row["normalized_token"] for row in words}
    assert {"grace", "love"} <= tokens

    index = service.get_group_index(group_id)
    assert index
    assert all(row["normalized_token"] in tokens for row in index)

    service.remove_word_from_group(group_id, "love")
    tokens = {row["normalized_token"] for row in service.list_group_words(group_id)}
    assert "love" not in tokens


def test_export_group_index_txt_and_csv(service, tmp_path):
    group_id = service.create_group("export-test")
    service.add_word_to_group(group_id, "grace")

    txt = service.export_group_index(group_id, tmp_path / "index.txt", format="txt")
    csv_ = service.export_group_index(group_id, tmp_path / "index.csv", format="csv")
    assert txt.exists() and txt.read_text(encoding="utf-8").strip()
    assert csv_.exists() and "grace" in csv_.read_text(encoding="utf-8").lower()


def test_phrase_creation_and_search(service):
    phrase_id = service.create_phrase("amazing", ["amazing", "grace"])
    results = service.search_phrase_by_id(phrase_id)
    assert results, "phrase 'amazing grace' should be found"
    assert results[0]["length"] == 2
    assert "amazing" in results[0]["phrase"]


def test_search_marked_phrase(service):
    word_id = service.get_word_id("amazing")
    occ = service.get_occurrences(word_id)[0]
    results = service.search_marked_phrase(
        document_id=occ["document_id"],
        start_word_seq=occ["word_seq_in_doc"],
        length=2,
    )
    assert results


def test_statistics_levels(service):
    for level in ("line", "stanza", "document", "word_frequency"):
        rows = service.get_statistics(level)
        assert isinstance(rows, list) and rows, f"level {level} returned no rows"
