"""Incremental zip fetcher for SEC IDISC filings.

Maintains a state map keyed by ``filing_id`` (parsed from the FILEID URL
parameter) recording sha256 + fetch timestamp + source URL. On re-runs,
the fetcher does a HEAD request and skips download if the remote
``Content-Length`` matches the cached one (cheap proxy for change
detection — the actual filing zip on SEC IDISC is published once with a
stable name and rarely changes).

Polite by default: 0.3 s between fetches. ``tenacity`` retries on
transient HTTP errors with exponential backoff.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

DEFAULT_DELAY_SEC = 0.3
DEFAULT_TIMEOUT_SEC = 60.0
RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

_FILEID_RE = re.compile(r"FILEID=([^&]+)")


@dataclass(frozen=True)
class FetchResult:
    """Outcome of one filing fetch.

    ``was_skipped`` is True when the incremental cache hit short-circuited
    the download. In that case ``local_zip_path`` may be ``None`` if the
    caller asked the fetcher not to materialize cache hits to disk.
    """

    filing_id: str
    source_url: str
    source_sha256: str
    local_zip_path: Path | None
    was_skipped: bool
    fetched_at: str  # ISO 8601 UTC


def parse_filing_id(filing_url: str) -> str:
    """Extract the filing-id from a SEC IDISC download URL.

    The URL format is::

        https://market.sec.or.th/public/idisc/Download?FILEID=dat/news/202602/0646FIN....zip

    The filing-id is the basename of the FILEID value without ``.zip``.
    Hyphenated symbols and date-keyed subdirectories pass through fine.
    """
    parsed = urlparse(filing_url)
    qs = parse_qs(parsed.query)
    fileid = (qs.get("FILEID") or [""])[0]
    if not fileid:
        # Some links pass FILEID via path; fall back to regex.
        m = _FILEID_RE.search(filing_url)
        if not m:
            raise ValueError(f"could not parse FILEID from URL: {filing_url}")
        fileid = m.group(1)
    base = fileid.rsplit("/", 1)[-1]
    if base.lower().endswith(".zip"):
        base = base[:-4]
    return base


def load_state(state_path: Path) -> dict[str, dict[str, Any]]:
    """Read ``state.json`` if present, else return ``{}``.

    The state map is treated as authoritative cache — corrupt or missing
    files start fresh rather than crashing the backfill.
    """
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict[str, dict[str, Any]], state_path: Path) -> Path:
    """Write the state map to disk atomically (write-temp-then-rename)."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(state_path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    tmp.replace(state_path)
    return state_path


def _is_retryable(exc: BaseException) -> bool:
    """tenacity predicate: retry on httpx transport + on retryable status codes."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRY_STATUS_CODES
    return isinstance(
        exc, (httpx.TransportError, httpx.TimeoutException, httpx.RemoteProtocolError)
    )


# Module-level retry policy — applied to the inner GET. Tests can monkey-patch
# the wait/stop via ``FilingFetcher(_retry_attempts=...)``.
def _retrying_get(
    client: httpx.Client, url: str, *, attempts: int = 4
) -> httpx.Response:
    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8.0),
        reraise=True,
    )
    def _do() -> httpx.Response:
        resp = client.get(url)
        resp.raise_for_status()
        return resp

    return _do()


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


class FilingFetcher:
    """Stateful, polite, incremental zip downloader.

    Construction takes the destination directory for materialized zips and
    a path to the state JSON. Use a single fetcher instance per backfill
    run so the polite-delay clock is shared across all downloads.
    """

    def __init__(
        self,
        dest_dir: Path,
        state_path: Path,
        delay: float = DEFAULT_DELAY_SEC,
        timeout: float = DEFAULT_TIMEOUT_SEC,
        client: httpx.Client | None = None,
        retry_attempts: int = 4,
    ) -> None:
        self.dest_dir = Path(dest_dir)
        self.state_path = Path(state_path)
        self.delay = delay
        self.timeout = timeout
        self._client = client
        self._owns_client = client is None
        self._retry_attempts = retry_attempts
        self.state: dict[str, dict[str, Any]] = load_state(self.state_path)
        self._last_fetch_at: float | None = None
        self.dest_dir.mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> "FilingFetcher":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                follow_redirects=True,
                timeout=self.timeout,
                headers={"User-Agent": "thaifin/2.0"},
            )
        return self._client

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def _maybe_sleep(self) -> None:
        if self._last_fetch_at is None or self.delay <= 0:
            return
        elapsed = time.monotonic() - self._last_fetch_at
        remaining = self.delay - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _try_skip_via_head(
        self, filing_id: str, filing_url: str
    ) -> FetchResult | None:
        """Decide whether the incremental cache lets us skip the GET.

        Two-tier logic:

        1. If the SEC IDISC server returns a ``Content-Length`` on HEAD,
           compare it to the cached length. Equal → skip; differ → re-GET.
        2. If HEAD succeeds but ``Content-Length`` is absent (the SEC
           server uses ``Transfer-Encoding: chunked`` for downloads,
           which strips length), we trust the cached sha256 — the SEC
           filing zips are immutable once published, so a 200 on HEAD
           with the same FILEID is a strong signal the file hasn't changed.
        3. Anything else (HEAD failure, no cache entry) → re-GET.
        """
        cached = self.state.get(filing_id)
        if not cached or "sha256" not in cached:
            return None
        if cached.get("source_url") and cached["source_url"] != filing_url:
            return None
        try:
            head = self.client.head(filing_url)
            head.raise_for_status()
        except (httpx.HTTPError, httpx.HTTPStatusError):
            # HEAD failed — fall through to GET, don't trust the cache.
            return None
        remote_len = head.headers.get("content-length")
        cached_len = str(cached.get("content_length") or "")
        if remote_len and cached_len:
            if remote_len != cached_len:
                return None  # Length changed → re-fetch
        # Either lengths match, or server doesn't expose Content-Length and
        # the URL/filing_id pair is in cache. Trust the cache.
        return FetchResult(
            filing_id=filing_id,
            source_url=filing_url,
            source_sha256=cached["sha256"],
            local_zip_path=None,
            was_skipped=True,
            fetched_at=cached.get("fetched_at", _now_iso()),
        )

    def fetch(self, filing_url: str) -> FetchResult:
        """Fetch one filing zip, honoring incremental cache + polite delay.

        On cache hit (verified via HEAD), returns a result with
        ``was_skipped=True`` and no local file. On miss, downloads the
        zip into ``dest_dir`` named ``<filing_id>.zip``, computes the
        sha256, updates state, and returns it.
        """
        filing_id = parse_filing_id(filing_url)

        # Fast path: HEAD-based skip. Note: this still consumes one HTTP RTT,
        # which is the desired SEC-friendly behavior — confirms the file
        # still exists and matches our cached length.
        skipped = self._try_skip_via_head(filing_id, filing_url)
        if skipped:
            self._last_fetch_at = time.monotonic()
            return skipped

        self._maybe_sleep()
        resp = _retrying_get(
            self.client, filing_url, attempts=self._retry_attempts
        )
        body = resp.content
        sha = hashlib.sha256(body).hexdigest()
        fetched_at = _now_iso()
        local_path = self.dest_dir / f"{filing_id}.zip"
        local_path.write_bytes(body)

        self.state[filing_id] = {
            "sha256": sha,
            "content_length": len(body),
            "fetched_at": fetched_at,
            "source_url": filing_url,
        }
        self._last_fetch_at = time.monotonic()
        return FetchResult(
            filing_id=filing_id,
            source_url=filing_url,
            source_sha256=sha,
            local_zip_path=local_path,
            was_skipped=False,
            fetched_at=fetched_at,
        )

    def flush_state(self) -> None:
        """Persist the in-memory state map to ``state.json``."""
        save_state(self.state, self.state_path)
