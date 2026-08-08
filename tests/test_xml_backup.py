def test_xml_round_trip_preserves_counts(service, tmp_path):
    result = service.run_xml_round_trip(
        tmp_path / "backup.xml", report_path=tmp_path / "report.txt"
    )
    assert result["passed"], result["report"]
    assert result["before"] == result["after"]
    assert (tmp_path / "backup.xml").exists()
    assert (tmp_path / "report.txt").exists()


def test_verify_counts_after_restore(service, tmp_path):
    before = service.verify_database_counts()
    backup = tmp_path / "backup.xml"
    service.export_database_xml(backup)
    service.restore_database_xml(backup)
    after = service.verify_database_counts()
    assert before == after


def test_search_still_works_after_round_trip(service, tmp_path):
    service.run_xml_round_trip(tmp_path / "backup.xml")
    assert service.search_by_word("grace")
    assert service.get_word_list()
