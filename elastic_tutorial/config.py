"""Load local tutorial settings without weakening TLS verification."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

from dotenv import dotenv_values
from elasticsearch import Elasticsearch


@dataclass(frozen=True)
class ElasticsearchConfig:
    url: str
    username: str
    password: str = field(repr=False)
    ca_cert: Path


def load_config(
    repo_root: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> ElasticsearchConfig:
    """Read the repository's .env, with process environment taking precedence.

    Paths are relative to the repository, so this also works from notebooks/.
    Values are literal: dotenv interpolation is disabled to preserve passwords
    that contain ``${...}``. Neither this function nor client setup prints them.
    """
    root = Path(repo_root or Path(__file__).resolve().parents[1]).resolve()
    process_env = os.environ if environ is None else environ
    env_file = Path(process_env.get("ELASTIC_ENV_FILE") or ".env").expanduser()
    if not env_file.is_absolute():
        env_file = root / env_file
    if process_env.get("ELASTIC_ENV_FILE") and not env_file.is_file():
        raise FileNotFoundError(f"ELASTIC_ENV_FILE does not exist: {env_file}")
    settings = {
        key: value
        for key, value in dotenv_values(env_file, interpolate=False).items()
        if value is not None
    }
    settings.update(process_env)

    password = settings.get("ELASTIC_PASSWORD", "")
    if not password:
        raise ValueError("Set ELASTIC_PASSWORD in .env or the process environment.")

    url = settings.get("ELASTICSEARCH_URL", "")
    if not url:
        port = settings.get("ES_PORT", "9200")
        if not port.isdecimal() or not 1 <= int(port) <= 65535:
            raise ValueError("ES_PORT must be an integer between 1 and 65535.")
        url = f"https://localhost:{port}"
    try:
        parsed = urlsplit(url)
        parsed.port  # Validate a malformed or out-of-range port without echoing credentials.
    except ValueError:
        raise ValueError("ELASTICSEARCH_URL must be a valid HTTPS URL.") from None
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("ELASTICSEARCH_URL must use HTTPS with a hostname.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Use ELASTIC_USERNAME / ELASTIC_PASSWORD instead of URL credentials.")
    if parsed.query or parsed.fragment:
        raise ValueError("ELASTICSEARCH_URL must not contain a query or fragment.")

    username = settings.get("ELASTIC_USERNAME", "elastic")
    if not username:
        raise ValueError("ELASTIC_USERNAME must not be empty.")
    cert = Path(settings.get("ELASTIC_CA_CERT") or "ca.crt").expanduser()
    if not cert.is_absolute():
        cert = root / cert
    cert = cert.resolve()
    if not cert.is_file():
        raise FileNotFoundError(
            f"CA certificate not found at {cert}. Run ./dev-cp-cert.sh after starting Docker."
        )
    return ElasticsearchConfig(url, username, password, cert)


def create_client(config: ElasticsearchConfig | None = None) -> Elasticsearch:
    """Create a verified HTTPS client; callers should close it or use ``with``."""
    config = config or load_config()
    return Elasticsearch(
        config.url,
        basic_auth=(config.username, config.password),
        ca_certs=str(config.ca_cert),
        verify_certs=True,
        request_timeout=30,
        max_retries=3,
        retry_on_timeout=True,
    )
