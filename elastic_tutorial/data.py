"""Small, deterministic datasets: no network downloads or Eland test fixtures."""

from __future__ import annotations

import random
import string
from datetime import datetime, timedelta, timezone
from typing import Any

from elasticsearch import Elasticsearch, helpers

FLIGHTS_INDEX = "eland-tutorial-flights-v1"
EVENTS_INDEX = "eland-tutorial-events-v1"
FLIGHTS_COUNT = 1_000
EVENTS_COUNT = 20_000
_OWNER = "es-in-docker-with-eland"

FLIGHTS_MAPPING = {
    "dynamic": "strict",
    "_meta": {"tutorial": _OWNER, "dataset": "flights", "schema_version": 1},
    "properties": {
        "id": {"type": "long"},
        "FlightNum": {"type": "keyword"},
        "Carrier": {"type": "keyword"},
        "OriginCityName": {"type": "keyword"},
        "DestCityName": {"type": "keyword"},
        "AvgTicketPrice": {"type": "double"},
        "DistanceKilometers": {"type": "double"},
        "Cancelled": {"type": "boolean"},
        "FlightDelayMin": {"type": "integer"},
        "timestamp": {"type": "date"},
    },
}

EVENTS_MAPPING = {
    "dynamic": "strict",
    "_meta": {"tutorial": _OWNER, "dataset": "events", "schema_version": 1},
    "properties": {
        "id": {"type": "long"},
        "random_string": {"type": "keyword"},
        "random_number": {"type": "integer"},
        "category": {"type": "keyword"},
        "message": {"type": "text"},
        "timestamp": {"type": "date"},
    },
}


def _validate_count(count: int) -> None:
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError("count must be a nonnegative integer")


def generate_flights(count: int = FLIGHTS_COUNT) -> list[dict[str, Any]]:
    """Return fictional flights with stable IDs and UTC timestamps."""
    _validate_count(count)
    rng = random.Random(42)
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    carriers = ("Formosa Air", "Pacific Wings", "Island Express")
    routes = (
        ("Taipei", "Tokyo", 2100.0),
        ("Taipei", "Seoul", 1500.0),
        ("Kaohsiung", "Hong Kong", 650.0),
        ("Taipei", "Singapore", 3250.0),
    )
    records = []
    for i in range(count):
        origin, destination, distance = routes[i % len(routes)]
        records.append(
            {
                "id": i,
                "FlightNum": f"DEMO{i:05d}",
                "Carrier": carriers[i % len(carriers)],
                "OriginCityName": origin,
                "DestCityName": destination,
                "AvgTicketPrice": round(rng.uniform(80, 900), 2),
                "DistanceKilometers": distance,
                "Cancelled": i % 29 == 0,
                "FlightDelayMin": rng.choice((0, 0, 0, 10, 20, 45, 90)),
                "timestamp": (start + timedelta(hours=i)).isoformat(),
            }
        )
    return records


def generate_events(count: int = EVENTS_COUNT) -> list[dict[str, Any]]:
    """Return repeatable events spanning the leap year 2024 in UTC."""
    _validate_count(count)
    rng = random.Random(42)
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    categories = ("search", "checkout", "support", "login")
    messages = (
        "Search request completed successfully",
        "Checkout payment completed successfully",
        "Support request opened for review",
        "Login request completed successfully",
    )
    return [
        {
            "id": i,
            "random_string": "".join(rng.choices(string.ascii_lowercase + string.digits, k=10)),
            "random_number": rng.randint(1, 1000),
            "category": categories[i % len(categories)],
            "message": messages[i % len(messages)],
            "timestamp": (start + timedelta(seconds=rng.randrange(366 * 86400))).isoformat(),
        }
        for i in range(count)
    ]


def _seed(
    client: Elasticsearch,
    index: str,
    mapping: dict[str, Any],
    records: list[dict[str, Any]],
) -> int:
    """Only write to owned, explicitly named tutorial indices; never delete one."""
    if index not in (FLIGHTS_INDEX, EVENTS_INDEX):
        raise ValueError("Only the named tutorial indices may be seeded.")
    if client.indices.exists(index=index):
        response = client.indices.get_mapping(index=index)
        existing = response.get(index, {}).get("mappings", {})
        if existing.get("_meta") != mapping["_meta"]:
            raise ValueError(
                f"Refusing to write to {index}: tutorial ownership/schema metadata differs. "
                "Use a fresh tutorial cluster or inspect this index manually."
            )
        if existing.get("properties") != mapping["properties"] or existing.get("dynamic") != "strict":
            raise ValueError(f"Refusing to write to {index}: its mapping differs from this tutorial.")
    else:
        client.indices.create(index=index, mappings=mapping)

    # 'index' upserts the same stable document IDs on every run. No replace/delete.
    actions = (
        {"_op_type": "index", "_index": index, "_id": str(row["id"]), "_source": row}
        for row in records
    )
    success, _ = helpers.bulk(client, actions, chunk_size=500, stats_only=True, raise_on_error=True)
    client.indices.refresh(index=index)
    return success


def seed_flights(client: Elasticsearch) -> int:
    """Create or refresh exactly the 1,000 deterministic flight document IDs."""
    return _seed(client, FLIGHTS_INDEX, FLIGHTS_MAPPING, generate_flights())


def seed_events(client: Elasticsearch) -> int:
    """Create or refresh exactly the 20,000 deterministic event document IDs."""
    return _seed(client, EVENTS_INDEX, EVENTS_MAPPING, generate_events())
