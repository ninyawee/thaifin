"""SEC IDISC ingest layer for the v2 dataset pipeline.

Three layers, each independently usable:
- ``symbols``   : enumerate ~866 listed companies from letter-pages
- ``fetcher``   : incremental, polite zip downloader with state.json
- ``normalize`` : libreoffice-backed legacy-XLS/DOC → OOXML wrapper

Discovery of filing URLs per symbol (the ``fs-norm`` page parser) lives
in a sibling ``discovery`` module created by slice #15; this slice does
not import it so the two slices can land independently.
"""

from thaifin.sources.sec_idisc import fetcher, normalize, symbols

__all__ = ["fetcher", "normalize", "symbols"]
