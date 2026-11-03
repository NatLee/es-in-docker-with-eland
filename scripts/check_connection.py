#!/usr/bin/env python3
"""Validate TLS, authentication, and that the server major matches the Python client."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from elasticsearch import ApiError
from elastic_transport import TransportError

from elastic_tutorial import create_client, require_compatible_server


def main() -> int:
    try:
        with create_client() as client:
            info = client.info()
            version = require_compatible_server(info)
            health = client.cluster.health()
            print(f"Connected: Elasticsearch {version}, cluster {info['cluster_name']}")
            print(f"TLS certificate verified; cluster health: {health['status']}")
            if health["status"] == "red":
                print("Connection succeeded, but cluster health is red; inspect the Elasticsearch logs.", file=sys.stderr)
                return 1
    except (ValueError, OSError) as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 1
    except ApiError as error:
        print(
            f"Elasticsearch returned HTTP {error.status_code}. Check credentials, permissions, and cluster logs.",
            file=sys.stderr,
        )
        return 1
    except TransportError as error:
        # Avoid printing the raw exception: connection details can contain secrets.
        print(
            f"Connection failed ({type(error).__name__}). Check Docker, ELASTICSEARCH_URL, and the CA certificate.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
