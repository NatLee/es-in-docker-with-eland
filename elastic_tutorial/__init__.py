"""Shared connection and sample-data helpers for the notebooks."""

from .config import ElasticsearchConfig, create_client, load_config, require_compatible_server

__all__ = ["ElasticsearchConfig", "create_client", "load_config", "require_compatible_server"]
