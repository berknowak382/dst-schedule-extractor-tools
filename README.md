# dst-schedule-extractor-tools

Finds the precise dates of daylight saving time transitions for a timezone.

```python
from datetime import date
from dst_schedule_extractor_tools import get_dst_schedule

transitions = get_dst_schedule("America/New_York", date(2023, 1, 1), date(2023, 12, 31))
for t in transitions:
    print(t.date, t.offset_before, t.offset_after, t.spring_forward)
# 2023-03-12 -1 day, 0:00:00 -1 day, 1:00:00 True
# 2023-11-05 -1 day, 1:00:00 -1 day, 0:00:00 False
```

## Why

You need to know when clocks change for a given IANA timezone — for scheduling, billing, or log alignment — without pulling in a heavyweight dependency. The standard library's `zoneinfo` already ships the rules; this library probes them.

The trade-off: we report the **date** of each transition and the UTC offset before and after, plus whether it is a spring-forward or fall-back. We do **not** report the exact wall-clock moment of the change (e.g. 02:00 → 03:00). That detail would require reimplementing zic transition-time logic and is usually unnecessary for planning.

## Edge you will hit

`get_dst_schedule` needs two consecutive days to detect a change. Internally it samples the offset at local **noon** of each day, which avoids landing in the 02:00 gap or 01:00 overlap. A one-day search window (`start == end`) still works because we probe the day before `start` as context, but a zero-length window will yield nothing. An inverted range (`end < start`) returns an empty list rather than raising.

## Exports

- `DSTTransition` — frozen dataclass with fields `date`, `offset_before` (`timedelta`), `offset_after` (`timedelta`), `spring_forward` (`bool`).
- `get_dst_schedule(timezone_name: str, start: date, end: date) -> list[DSTTransition]`
- `find_transitions_in_range(timezone_name: str, year: int, month: int, day: int) -> list[DSTTransition]` — convenience wrapper searching one calendar year forward from the given date.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

