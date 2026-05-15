"""Tests for ``thaifin.sources.sec_idisc.fetcher`` (slice #17).

httpx is mocked via its built-in ``MockTransport`` — no real network I/O.
"""

from __future__ import annotations

from pathlib import Path

import httpx

from thaifin.sources.sec_idisc.fetcher import (
    FilingFetcher,
    load_state,
    parse_filing_id,
    save_state,
)

SAMPLE_URL = (
    "https://market.sec.or.th/public/idisc/Download"
    "?FILEID=dat/news/202602/0646FIN190220261747440265T.zip"
)
EXPECTED_FILING_ID = "0646FIN190220261747440265T"
SAMPLE_PAYLOAD = b"PK\x03\x04zip-bytes-here-not-really-a-zip"


def _ok_handler(payload: bytes = SAMPLE_PAYLOAD):
    """Handler that returns 200 with given payload to GET, content-length to HEAD."""

    def handler(req: httpx.Request) -> httpx.Response:
        if req.method == "HEAD":
            return httpx.Response(200, headers={"content-length": str(len(payload))})
        return httpx.Response(200, content=payload)

    return handler


def _flaky_then_ok_handler(payload: bytes = SAMPLE_PAYLOAD):
    """Handler that returns 429 the first 2 GETs, then 200."""
    state = {"calls": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        if req.method == "HEAD":
            return httpx.Response(404)  # force GET path
        state["calls"] += 1
        if state["calls"] <= 2:
            return httpx.Response(429, headers={"retry-after": "0"})
        return httpx.Response(200, content=payload)

    return handler


def _client_with_handler(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_parse_filing_id_strips_path_and_zip() -> None:
    assert parse_filing_id(SAMPLE_URL) == EXPECTED_FILING_ID


def test_parse_filing_id_handles_no_subdir() -> None:
    url = "https://example.com/Download?FILEID=ABC123.zip"
    assert parse_filing_id(url) == "ABC123"


def test_first_fetch_downloads_and_records_state(tmp_path: Path) -> None:
    """A cold cache fetch writes the zip and populates state.json."""
    client = _client_with_handler(_ok_handler())
    state_path = tmp_path / "state.json"
    fetcher = FilingFetcher(
        dest_dir=tmp_path / "zips",
        state_path=state_path,
        delay=0.0,
        client=client,
    )
    result = fetcher.fetch(SAMPLE_URL)
    fetcher.flush_state()

    assert result.was_skipped is False
    assert result.local_zip_path is not None and result.local_zip_path.exists()
    assert result.local_zip_path.read_bytes() == SAMPLE_PAYLOAD
    assert len(result.source_sha256) == 64

    state = load_state(state_path)
    assert EXPECTED_FILING_ID in state
    entry = state[EXPECTED_FILING_ID]
    assert entry["sha256"] == result.source_sha256
    assert entry["content_length"] == len(SAMPLE_PAYLOAD)
    assert entry["source_url"] == SAMPLE_URL


def test_second_fetch_skips_via_head(tmp_path: Path) -> None:
    """When HEAD's content-length matches state, fetch is skipped."""
    state = {
        EXPECTED_FILING_ID: {
            "sha256": "deadbeef" * 8,
            "content_length": len(SAMPLE_PAYLOAD),
            "fetched_at": "2026-05-15T00:00:00+00:00",
            "source_url": SAMPLE_URL,
        }
    }
    state_path = tmp_path / "state.json"
    save_state(state, state_path)

    # GET handler raises if called — should not happen.
    def handler(req: httpx.Request) -> httpx.Response:
        if req.method == "HEAD":
            return httpx.Response(
                200, headers={"content-length": str(len(SAMPLE_PAYLOAD))}
            )
        raise AssertionError(f"unexpected GET: {req.url}")

    client = _client_with_handler(handler)
    fetcher = FilingFetcher(
        dest_dir=tmp_path / "zips",
        state_path=state_path,
        delay=0.0,
        client=client,
    )
    result = fetcher.fetch(SAMPLE_URL)
    assert result.was_skipped is True
    assert result.local_zip_path is None
    assert result.source_sha256 == "deadbeef" * 8


def test_size_mismatch_triggers_redownload(tmp_path: Path) -> None:
    """If HEAD's content-length differs from state, fetcher proceeds to GET."""
    state = {
        EXPECTED_FILING_ID: {
            "sha256": "old-hash",
            "content_length": 999_999,  # mismatch with SAMPLE_PAYLOAD
            "fetched_at": "2026-05-15T00:00:00+00:00",
            "source_url": SAMPLE_URL,
        }
    }
    state_path = tmp_path / "state.json"
    save_state(state, state_path)

    client = _client_with_handler(_ok_handler())
    fetcher = FilingFetcher(
        dest_dir=tmp_path / "zips",
        state_path=state_path,
        delay=0.0,
        client=client,
    )
    result = fetcher.fetch(SAMPLE_URL)
    assert result.was_skipped is False
    assert result.local_zip_path is not None and result.local_zip_path.exists()
    # State sha256 has been updated to the new hash.
    assert result.source_sha256 != "old-hash"


def test_retry_on_429(tmp_path: Path) -> None:
    """Two consecutive 429s are retried, then the third call succeeds."""
    client = _client_with_handler(_flaky_then_ok_handler())
    fetcher = FilingFetcher(
        dest_dir=tmp_path / "zips",
        state_path=tmp_path / "state.json",
        delay=0.0,
        client=client,
        retry_attempts=4,
    )
    result = fetcher.fetch(SAMPLE_URL)
    assert result.was_skipped is False
    assert result.local_zip_path is not None
    assert result.local_zip_path.read_bytes() == SAMPLE_PAYLOAD


def test_skip_when_head_omits_content_length(tmp_path: Path) -> None:
    """SEC IDISC uses Transfer-Encoding: chunked → no Content-Length on HEAD.

    With a cache entry and a successful HEAD (any status), the fetcher
    should still skip the GET — filing zips are immutable once published.
    """
    state = {
        EXPECTED_FILING_ID: {
            "sha256": "deadbeef" * 8,
            "content_length": len(SAMPLE_PAYLOAD),
            "fetched_at": "2026-05-15T00:00:00+00:00",
            "source_url": SAMPLE_URL,
        }
    }
    state_path = tmp_path / "state.json"
    save_state(state, state_path)

    def handler(req: httpx.Request) -> httpx.Response:
        if req.method == "HEAD":
            # No Content-Length, mimicking real SEC IDISC behavior.
            return httpx.Response(200, headers={"transfer-encoding": "chunked"})
        raise AssertionError(f"unexpected GET: {req.url}")

    client = _client_with_handler(handler)
    fetcher = FilingFetcher(
        dest_dir=tmp_path / "zips",
        state_path=state_path,
        delay=0.0,
        client=client,
    )
    result = fetcher.fetch(SAMPLE_URL)
    assert result.was_skipped is True


def test_provenance_fields_populated(tmp_path: Path) -> None:
    client = _client_with_handler(_ok_handler())
    fetcher = FilingFetcher(
        dest_dir=tmp_path / "zips",
        state_path=tmp_path / "state.json",
        delay=0.0,
        client=client,
    )
    result = fetcher.fetch(SAMPLE_URL)
    assert result.filing_id == EXPECTED_FILING_ID
    assert result.source_url == SAMPLE_URL
    assert len(result.source_sha256) == 64
    assert result.fetched_at  # non-empty ISO timestamp
    assert "T" in result.fetched_at
