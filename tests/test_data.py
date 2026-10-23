from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import random
import unittest
from unittest.mock import MagicMock, patch

from elastic_tutorial.data import (
    EVENTS_COUNT,
    EVENTS_MAPPING,
    EVENTS_INDEX,
    FLIGHTS_COUNT,
    FLIGHTS_INDEX,
    FLIGHTS_MAPPING,
    generate_events,
    generate_flights,
    seed_events,
    seed_flights,
)


class DataTests(unittest.TestCase):
    def test_generators_are_deterministic_without_changing_global_random_state(self):
        state = random.getstate()
        for generate in (generate_flights, generate_events):
            self.assertEqual(generate(15), generate(15))
            self.assertEqual(generate(15)[:5], generate(5))
        self.assertEqual(random.getstate(), state)

    def test_default_sizes_and_unique_ids(self):
        for records, expected in ((generate_flights(), FLIGHTS_COUNT), (generate_events(), EVENTS_COUNT)):
            self.assertEqual(len(records), expected)
            self.assertEqual([row["id"] for row in records], list(range(expected)))

    def test_utc_dates_cover_every_month_in_leap_year(self):
        timestamps = [datetime.fromisoformat(row["timestamp"]) for row in generate_events()]
        self.assertTrue(all(timestamp.year == 2024 for timestamp in timestamps))
        self.assertTrue(all(timestamp.utcoffset() == timezone.utc.utcoffset(timestamp) for timestamp in timestamps))
        self.assertEqual({timestamp.month for timestamp in timestamps}, set(range(1, 13)))
        self.assertTrue(any(timestamp.month == 2 and timestamp.day == 29 for timestamp in timestamps))

    def test_event_ranges_and_text_examples(self):
        records = generate_events()
        self.assertTrue(all(1 <= row["random_number"] <= 1000 for row in records))
        self.assertEqual(Counter(row["category"] for row in records), {
            "search": 5000, "checkout": 5000, "support": 5000, "login": 5000,
        })
        self.assertEqual(sum("payment" in row["message"] for row in records), 5000)

    def test_data_matches_explicit_mappings(self):
        for records, mapping in ((generate_flights(10), FLIGHTS_MAPPING), (generate_events(10), EVENTS_MAPPING)):
            for row in records:
                self.assertEqual(set(row), set(mapping["properties"]))
            self.assertEqual(mapping["properties"]["timestamp"]["type"], "date")
            self.assertEqual(mapping["dynamic"], "strict")

    def test_invalid_sizes_are_rejected(self):
        for generate in (generate_flights, generate_events):
            self.assertEqual(generate(0), [])
            for count in (-1, 1.5, "10", True):
                with self.subTest(generator=generate.__name__, count=count), self.assertRaises(ValueError):
                    generate(count)


class SeedSafetyTests(unittest.TestCase):
    def test_repeat_seed_preserves_ids_and_never_deletes(self):
        client = MagicMock()
        client.indices.exists.return_value = False
        writes = []

        def capture(_client, actions, **kwargs):
            rows = list(actions)
            writes.append(rows)
            self.assertTrue(kwargs["raise_on_error"])
            return len(rows), 0

        with patch("elastic_tutorial.data.helpers.bulk", side_effect=capture):
            self.assertEqual(seed_flights(client), FLIGHTS_COUNT)
            client.indices.exists.return_value = True
            client.indices.get_mapping.return_value = {FLIGHTS_INDEX: {"mappings": deepcopy(FLIGHTS_MAPPING)}}
            self.assertEqual(seed_flights(client), FLIGHTS_COUNT)

        self.assertEqual(writes[0], writes[1])
        self.assertEqual({row["_id"] for row in writes[0]}, {str(i) for i in range(FLIGHTS_COUNT)})
        self.assertEqual({row["_op_type"] for row in writes[0]}, {"index"})
        client.indices.delete.assert_not_called()
        client.delete_by_query.assert_not_called()
        self.assertEqual(client.indices.refresh.call_count, 2)
        client.indices.create.assert_called_once()

    def test_refuses_existing_unowned_index(self):
        client = MagicMock()
        client.indices.exists.return_value = True
        client.indices.get_mapping.return_value = {EVENTS_INDEX: {"mappings": {"properties": EVENTS_MAPPING["properties"]}}}
        with patch("elastic_tutorial.data.helpers.bulk") as bulk:
            with self.assertRaisesRegex(ValueError, "ownership"):
                seed_events(client)
            bulk.assert_not_called()
        client.indices.delete.assert_not_called()

    def test_refuses_changed_date_mapping(self):
        client = MagicMock()
        client.indices.exists.return_value = True
        existing = deepcopy(EVENTS_MAPPING)
        existing["properties"]["timestamp"] = {"type": "keyword"}
        client.indices.get_mapping.return_value = {EVENTS_INDEX: {"mappings": existing}}
        with patch("elastic_tutorial.data.helpers.bulk") as bulk:
            with self.assertRaisesRegex(ValueError, "mapping differs"):
                seed_events(client)
            bulk.assert_not_called()


if __name__ == "__main__":
    unittest.main()
