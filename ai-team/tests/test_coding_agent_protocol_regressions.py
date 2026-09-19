import re


def test_request_protocol_has_read_range_support():
    from agents.coding_agent import ACTION_RE

    text = "<<<READ: src/main.py:10-20>>>"
    match = ACTION_RE.search(text)

    assert match is not None
    assert match.group("path") == "src/main.py:10-20"


def test_request_protocol_done_marker_is_detected():
    from agents.coding_agent import ACTION_RE

    match = ACTION_RE.search("<<<DONE>>>")

    assert match is not None
    assert match.group("done") == "DONE"
