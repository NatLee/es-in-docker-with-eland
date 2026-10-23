#!/usr/bin/env python3
"""Exercise the notebooks' real ES/Eland paths, leaving the tutorial indices."""

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import eland as ed
import pandas as pd
from elasticsearch import ApiError
from elastic_transport import TransportError

from elastic_tutorial import create_client
from elastic_tutorial.data import (
    EVENTS_COUNT,
    EVENTS_INDEX,
    FLIGHTS_COUNT,
    FLIGHTS_INDEX,
    generate_events,
    generate_flights,
    seed_events,
    seed_flights,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_checks() -> None:
    with create_client() as client:
        version = client.info()["version"]["number"]
        require(version.split(".")[0] == "9", f"Expected Elasticsearch 9.x, found {version}; review migration instructions.")
        print(f"Connected to Elasticsearch {version} with verified TLS.")

        require(seed_flights(client) == FLIGHTS_COUNT, "Flight bulk write count differs.")
        require(seed_events(client) == EVENTS_COUNT, "Event bulk write count differs.")
        # Re-running imports must overwrite the same IDs instead of duplicating data.
        seed_flights(client)
        require(client.count(index=FLIGHTS_INDEX)["count"] == FLIGHTS_COUNT, "Repeated seeding duplicated flights.")
        require(client.count(index=EVENTS_INDEX)["count"] == EVENTS_COUNT, "Event index count differs.")
        mapping = client.indices.get_mapping(index=EVENTS_INDEX)[EVENTS_INDEX]["mappings"]
        require(mapping["properties"]["timestamp"]["type"] == "date", "timestamp must be mapped as date.")
        require(mapping["properties"]["category"]["type"] == "keyword", "category must be mapped as keyword.")
        require(mapping["_meta"]["schema_version"] == 1, "Tutorial metadata is missing.")

        flights = ed.DataFrame(client, FLIGHTS_INDEX)
        events = ed.DataFrame(client, EVENTS_INDEX)
        source_events = generate_events()
        source_flights = generate_flights()
        require(len(events) == EVENTS_COUNT, "Eland count differs.")
        expected_filtered = sum(row["random_number"] > 500 for row in source_events)
        require(len(events[events["random_number"] > 500]) == expected_filtered, "Eland numeric filter differs.")

        date_query = {"range": {"timestamp": {"gte": "2024-08-01T00:00:00Z", "lt": "2024-09-01T00:00:00Z"}}}
        august_start = datetime(2024, 8, 1, tzinfo=timezone.utc)
        august_end = datetime(2024, 9, 1, tzinfo=timezone.utc)
        expected_august = sum(august_start <= datetime.fromisoformat(row["timestamp"]) < august_end for row in source_events)
        require(len(events.es_query(date_query)) == expected_august, "Eland date range differs.")
        require(len(events.es_query({"match": {"message": "payment"}})) == EVENTS_COUNT // 4, "Full-text query differs.")

        # id is always present; its value_count is an exact document count here.
        grouped = flights[["Carrier", "id"]].groupby("Carrier").count()["id"]
        require(grouped.to_dict() == dict(Counter(row["Carrier"] for row in source_flights)), "Group counts differ.")
        top_hits = client.search(
            index=EVENTS_INDEX,
            size=10,
            sort=[{"random_number": "desc"}, {"id": "asc"}],
            source_includes=["id", "random_number"],
        )["hits"]["hits"]
        expected_top = sorted(source_events, key=lambda row: (-row["random_number"], row["id"]))[:10]
        require([hit["_source"]["id"] for hit in top_hits] == [row["id"] for row in expected_top], "Server-side descending sort differs.")

        # Full materialization is intentional for this bounded 20,000-row regression.
        result = events.to_pandas()
        require(len(result) == EVENTS_COUNT and len(result) > 10_000, "Export lost records beyond 10,000.")
        require(set(result["id"]) == set(range(EVENTS_COUNT)), "Export contains missing or duplicate IDs.")
        require(pd.api.types.is_datetime64_any_dtype(result["timestamp"]), "Eland did not decode dates.")
        print("PASS: stable IDs, mappings, Eland filters, date queries, aggregation, top-10 sorting, and 20,000-row export.")
        print(f"Tutorial indices retained: {FLIGHTS_INDEX}, {EVENTS_INDEX}")


def main() -> int:
    try:
        run_checks()
    except (ValueError, OSError, AssertionError) as error:
        print(f"Smoke test failed: {error}", file=sys.stderr)
        return 1
    except ApiError as error:
        print(f"Smoke test failed: Elasticsearch HTTP {error.status_code}; inspect cluster logs and index mappings.", file=sys.stderr)
        return 1
    except TransportError as error:
        print(f"Smoke test failed ({type(error).__name__}); check Docker, credentials, URL, and CA certificate.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
