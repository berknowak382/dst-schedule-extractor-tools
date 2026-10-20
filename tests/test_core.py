"""Tests for the core DST transition finder."""

import unittest
from datetime import date, timedelta
from datetime import timezone as dt_timezone

from dst_schedule_extractor_tools import (
    DSTTransition,
    get_dst_schedule,
    find_transitions_in_range,
)


class TestGetDSTSchedule(unittest.TestCase):

    # --- New York transitions: second Sunday of March, first Sunday of November ---

    def test_new_york_spring_2023(self):
        transitions = get_dst_schedule(
            "America/New_York",
            date(2023, 3, 1),
            date(2023, 3, 31),
        )
        self.assertEqual(len(transitions), 1)
        t = transitions[0]
        self.assertEqual(t.date, date(2023, 3, 12))
        self.assertEqual(t.offset_before, timedelta(hours=-5))
        self.assertEqual(t.offset_after, timedelta(hours=-4))
        self.assertTrue(t.spring_forward)

    def test_new_york_fall_2023(self):
        transitions = get_dst_schedule(
            "America/New_York",
            date(2023, 11, 1),
            date(2023, 11, 30),
        )
        self.assertEqual(len(transitions), 1)
        t = transitions[0]
        self.assertEqual(t.date, date(2023, 11, 5))
        self.assertEqual(t.offset_before, timedelta(hours=-4))
        self.assertEqual(t.offset_after, timedelta(hours=-5))
        self.assertFalse(t.spring_forward)

    def test_new_york_full_year_2023(self):
        transitions = get_dst_schedule(
            "America/New_York",
            date(2023, 1, 1),
            date(2023, 12, 31),
        )
        self.assertEqual([t.date for t in transitions],
                         [date(2023, 3, 12), date(2023, 11, 5)])

    # --- London transitions: last Sunday of March, last Sunday of October ---

    def test_london_spring_2023(self):
        transitions = get_dst_schedule(
            "Europe/London",
            date(2023, 3, 1),
            date(2023, 3, 31),
        )
        self.assertEqual(len(transitions), 1)
        t = transitions[0]
        self.assertEqual(t.date, date(2023, 3, 26))
        # Before: UTC+0, after: UTC+1
        self.assertEqual(t.offset_before, timedelta(0))
        self.assertEqual(t.offset_after, timedelta(hours=1))
        self.assertTrue(t.spring_forward)

    def test_london_fall_2023(self):
        transitions = get_dst_schedule(
            "Europe/London",
            date(2023, 10, 1),
            date(2023, 10, 31),
        )
        self.assertEqual(len(transitions), 1)
        t = transitions[0]
        self.assertEqual(t.date, date(2023, 10, 29))
        self.assertEqual(t.offset_before, timedelta(hours=1))
        self.assertEqual(t.offset_after, timedelta(0))
        self.assertFalse(t.spring_forward)

    # --- Australia: DST in southern hemisphere (starts Oct, ends Apr) ---

    def test_sydney_spring_2022(self):
        # Australia/Sydney springs forward on the first Sunday of October.
        transitions = get_dst_schedule(
            "Australia/Sydney",
            date(2022, 10, 1),
            date(2022, 10, 31),
        )
        self.assertEqual(len(transitions), 1)
        t = transitions[0]
        self.assertEqual(t.date, date(2022, 10, 2))
        self.assertEqual(t.offset_before, timedelta(hours=10))
        self.assertEqual(t.offset_after, timedelta(hours=11))
        self.assertTrue(t.spring_forward)

    def test_sydney_fall_2023(self):
        # Sydney falls back on the first Sunday of April.
        transitions = get_dst_schedule(
            "Australia/Sydney",
            date(2023, 4, 1),
            date(2023, 4, 30),
        )
        self.assertEqual(len(transitions), 1)
        t = transitions[0]
        self.assertEqual(t.date, date(2023, 4, 2))
        self.assertEqual(t.offset_before, timedelta(hours=11))
        self.assertEqual(t.offset_after, timedelta(hours=10))
        self.assertFalse(t.spring_forward)

    # --- Timezones without DST ---

    def test_tokyo_no_dst(self):
        transitions = get_dst_schedule(
            "Asia/Tokyo",
            date(2023, 1, 1),
            date(2023, 12, 31),
        )
        self.assertEqual(transitions, [])

    def test_utc_no_dst(self):
        transitions = get_dst_schedule(
            "UTC",
            date(2023, 1, 1),
            date(2023, 12, 31),
        )
        self.assertEqual(transitions, [])

    # --- Edge cases on the search window ---

    def test_single_day_window(self):
        transitions = get_dst_schedule(
            "America/New_York",
            date(2023, 3, 12),
            date(2023, 3, 12),
        )
        # Two distinct days are needed to detect a change, so the
        # implementation requires at least start <= end but still needs
        # the day before ``start`` as context.  Here March 12 itself is
        # a transition day (it changes from EST to EDT), so we expect
        # one transition.
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0].date, date(2023, 3, 12))

    def test_inverted_range_returns_empty(self):
        transitions = get_dst_schedule(
            "America/New_York",
            date(2023, 12, 31),
            date(2023, 1, 1),
        )
        self.assertEqual(transitions, [])

    def test_transition_on_first_day_of_range(self):
        # March 12 2023 is a transition day in New York.  A range that
        # starts exactly on that day must still report it.
        transitions = get_dst_schedule(
            "America/New_York",
            date(2023, 3, 12),
            date(2023, 4, 1),
        )
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0].date, date(2023, 3, 12))

    def test_transition_on_last_day_of_range(self):
        # November 5 2023 is a fall-back day in New York.  A range that
        # ends exactly on that day must report it.
        transitions = get_dst_schedule(
            "America/New_York",
            date(2023, 10, 25),
            date(2023, 11, 5),
        )
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0].date, date(2023, 11, 5))

    # --- Dataclass behaviour ---

    def test_transition_is_frozen(self):
        transitions = get_dst_schedule(
            "America/New_York",
            date(2023, 3, 1),
            date(2023, 3, 31),
        )
        with self.assertRaises(Exception):
            transitions[0].spring_forward = False

    def test_transition_rejects_equal_offsets(self):
        with self.assertRaises(ValueError):
            DSTTransition(
                date=date(2023, 3, 12),
                offset_before=timedelta(hours=-5),
                offset_after=timedelta(hours=-5),
                spring_forward=True,
            )

    # --- find_transitions_in_range convenience wrapper ---

    def test_find_transitions_in_range_new_york_2023(self):
        transitions = find_transitions_in_range("America/New_York", 2023, 1, 1)
        self.assertEqual([t.date for t in transitions],
                         [date(2023, 3, 12), date(2023, 11, 5)])

    def test_find_transitions_in_range_invalid_date(self):
        with self.assertRaises(ValueError):
            find_transitions_in_range("America/New_York", 2023, 13, 1)


if __name__ == "__main__":
    unittest.main()
