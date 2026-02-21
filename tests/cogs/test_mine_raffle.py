from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "greenwiz"))

from cogs.mine_raffle import extract_mine_participants, parse_hyperion_timestamp


def test_parse_hyperion_timestamp_handles_milliseconds_without_timezone() -> None:
    parsed = parse_hyperion_timestamp("2025-11-12T01:49:27.500")

    assert parsed is not None
    assert parsed.tzinfo == timezone.utc
    assert parsed.year == 2025
    assert parsed.minute == 49


def test_extract_mine_participants_filters_land_id_and_time_window() -> None:
    window_start = datetime(2025, 11, 12, 0, 0, 0, tzinfo=timezone.utc)
    actions = [
        {
            "timestamp": "2025-11-12T01:49:27.500",
            "act": {"data": {"miner": "b52qw.wam", "land_id": "1099512959648"}},
        },
        {
            "timestamp": "2025-11-12T01:20:00.000",
            "act": {"data": {"miner": "otherminer12", "land_id": "999999999999"}},
        },
        {
            "timestamp": "2025-11-11T23:59:59.000",
            "act": {"data": {"miner": "lateuser11111", "land_id": "1099512959648"}},
        },
    ]

    participants = extract_mine_participants(
        actions=actions,
        land_ids={"1099512959648"},
        window_start=window_start,
        valid_specials={"wam"},
    )

    assert participants == {"b52qw.wam"}
