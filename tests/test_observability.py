import logging

from utils.observability import StringifyLogAttributes


def test_mixed_sequence_attribute_is_stringified():
    # mitmproxy logs with extra={"client": (host, port)}, a (str, int) tuple.
    record = logging.LogRecord("mitmproxy", logging.INFO, __file__, 1, "server disconnect", (), None)
    record.client = ("1.2.3.4", 7171)

    assert StringifyLogAttributes().filter(record)

    assert isinstance(record.client, str)
    assert "1.2.3.4" in record.client
    assert "7171" in record.client


def test_all_extra_attributes_are_stringified():
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "m", (), None)
    record.tags = ("a", "b")
    record.count = 5

    StringifyLogAttributes().filter(record)

    assert isinstance(record.tags, str)
    assert isinstance(record.count, str)
    assert record.count == "5"


def test_standard_record_attributes_are_untouched():
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "hi %s %d", ("a", 1), None)

    StringifyLogAttributes().filter(record)

    assert record.args == ("a", 1)
    assert record.getMessage() == "hi a 1"
