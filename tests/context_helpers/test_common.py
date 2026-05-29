from engram.context_helpers.common import compact_text

def test_compact_text():
    # None and empty
    assert compact_text(None) == ""
    assert compact_text("") == ""

    # Primary logic: strip whitespace
    assert compact_text("  hello  ") == "hello"
    assert compact_text("\t\nworld\r\n") == "world"

    # Normal ASCII
    assert compact_text("Hello World") == "Hello World"

    # ASCII conversion/Unicode replacement
    assert compact_text("Hello \u2665 World") == "Hello ? World"

    # Verify no truncation occurs on long strings
    long_str = "a" * 200
    assert compact_text(long_str) == long_str
