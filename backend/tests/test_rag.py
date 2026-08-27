from app.main import health_check
from app.rag import _split_text, clean_text


def test_health_check_reports_the_api_as_available():
    response = health_check()

    assert response.status == "ok"


def test_clean_text_normalizes_whitespace_and_joined_words():
    text = "  DearHiring,team!\n\nThis is   a test.  "

    assert clean_text(text) == "Dear Hiring, team! This is a test."


def test_split_text_creates_multiple_nonempty_chunks_with_overlap():
    text = " ".join(f"sentence {number}." for number in range(1, 60))

    chunks = _split_text(text, chunk_size=140, chunk_overlap=30)

    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)
    assert chunks[0].startswith("sentence 1.")
    assert chunks[-1].endswith("sentence 59.")
