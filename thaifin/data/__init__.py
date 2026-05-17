"""Dataset access layer (HuggingFace-hosted parquet via DuckDB streaming)."""

from thaifin.data.client import DATASET_REPO, DatasetClient
from thaifin.data.download import cache_dir_for, download_dataset
from thaifin.data.revision import (
    DEFAULT_REVISION,
    get_data_revision,
    reset_data_revision,
    set_data_revision,
)

__all__ = [
    "DATASET_REPO",
    "DEFAULT_REVISION",
    "DatasetClient",
    "cache_dir_for",
    "download_dataset",
    "get_data_revision",
    "reset_data_revision",
    "set_data_revision",
]
