from __future__ import annotations

from datetime import UTC, datetime

from django.test import SimpleTestCase

from domain.scheduling.exceptions import SchedulingInvalid
from domain.scheduling.recurrence import materialized_windows


class RecurrenceTests(SimpleTestCase):
    def test_weekly_count_is_bounded_and_materialized_in_utc(self) -> None:
        windows = materialized_windows(
            first_starts_at=datetime(2026, 8, 3, 8, tzinfo=UTC),
            duration_minutes=90,
            timezone_name="America/Bogota",
            recurrence_rule="FREQ=WEEKLY;COUNT=3;BYDAY=MO",
        )
        self.assertEqual(len(windows), 3)
        self.assertTrue(all(start.tzinfo is UTC for start, _ in windows))
        self.assertTrue(
            all((end - start).total_seconds() == 5400 for start, end in windows)
        )

    def test_unbounded_or_excessive_rules_are_rejected(self) -> None:
        start = datetime(2026, 8, 3, 8, tzinfo=UTC)
        for rule in ("FREQ=DAILY", "FREQ=DAILY;COUNT=367", "FREQ=SECONDLY;COUNT=2"):
            with self.subTest(rule=rule), self.assertRaises(SchedulingInvalid):
                materialized_windows(
                    first_starts_at=start,
                    duration_minutes=60,
                    timezone_name="America/Bogota",
                    recurrence_rule=rule,
                )

    def test_invalid_timezone_is_rejected(self) -> None:
        with self.assertRaises(SchedulingInvalid):
            materialized_windows(
                first_starts_at=datetime(2026, 8, 3, 8, tzinfo=UTC),
                duration_minutes=60,
                timezone_name="Mars/Olympus",
                recurrence_rule="",
            )
