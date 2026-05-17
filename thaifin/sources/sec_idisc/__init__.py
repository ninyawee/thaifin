"""SEC IDISC ingest layer for the v2 dataset pipeline.

Four layers, each independently usable:

- ``symbols``    : enumerate ~866 listed companies from letter-pages (slice #17)
- ``discovery``  : per-symbol ``fs-norm`` page parser → filing manifest (slice #15)
- ``fetcher``    : incremental, polite zip downloader with state.json (slice #17)
- ``normalize``  : libreoffice-backed legacy-XLS/DOC → OOXML wrapper (slice #17)
"""

from thaifin.sources.sec_idisc import discovery, fetcher, normalize, symbols
from thaifin.sources.sec_idisc.discovery import (
    FilingManifestEntry,
    discover_filings,
    filings_to_records,
    parse_fs_norm_html,
)

__all__ = [
    "FilingManifestEntry",
    "discover_filings",
    "discovery",
    "fetcher",
    "filings_to_records",
    "normalize",
    "parse_fs_norm_html",
    "symbols",
]
