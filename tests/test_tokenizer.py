from lyriconc.tokenizer import normalize_token, tokenize


def test_tokenize_lowercases_and_splits_hyphens():
    assert tokenize("Well-known SONG") == ["well", "known", "song"]


def test_tokenize_keeps_inner_apostrophe():
    assert tokenize("don't stop") == ["don't", "stop"]


def test_tokenize_drops_edge_apostrophe():
    assert tokenize("'tis fine") == ["tis", "fine"]


def test_tokenize_curly_apostrophe_normalised():
    assert tokenize("you\u2019re here") == ["you're", "here"]


def test_normalize_token_rejects_multi_word():
    assert normalize_token("hello world") == ""
    assert normalize_token("hello") == "hello"
    assert normalize_token("") == ""
