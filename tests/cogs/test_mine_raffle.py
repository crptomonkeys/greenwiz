import sys
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "greenwiz"))

from cogs.mine_raffle import (
    MineRaffle,
    extract_mine_participants,
    extract_mine_window_stats,
    filter_participants_by_whitelist,
    format_winner_discord,
    get_latest_even_hour_window,
    parse_hyperion_timestamp,
)


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


def test_extract_mine_window_stats_counts_mines_and_unique_miners() -> None:
    window_start = datetime(2025, 11, 12, 0, 0, 0, tzinfo=timezone.utc)
    actions = [
        {
            "timestamp": "2025-11-12T00:10:00.000",
            "act": {"data": {"miner": "b52qw.wam", "land_id": "1099512959648"}},
        },
        {
            "timestamp": "2025-11-12T00:40:00.000",
            "act": {"data": {"miner": "b52qw.wam", "land_id": "1099512959648"}},
        },
        {
            "timestamp": "2025-11-12T01:20:00.000",
            "act": {"data": {"miner": "4h.qy.wam", "land_id": "1099512959648"}},
        },
    ]

    participants, mine_count = extract_mine_window_stats(
        actions=actions,
        land_ids={"1099512959648"},
        window_start=window_start,
        valid_specials={"wam"},
    )

    assert mine_count == 3
    assert participants == {"b52qw.wam", "4h.qy.wam"}


def test_filter_participants_by_whitelist() -> None:
    participants = {"49815.wam", "4h.qy.wam", "mconstant.gm"}
    whitelist = {"4h.qy.wam", "mconstant.gm"}

    filtered = filter_participants_by_whitelist(participants, whitelist)

    assert filtered == {"4h.qy.wam", "mconstant.gm"}


def test_format_winner_discord() -> None:
    assert format_winner_discord([753349150833115311]) == ("<@753349150833115311> (`753349150833115311`)")


def test_get_latest_even_hour_window_aligns_to_even_hours() -> None:
    window_start, window_end = get_latest_even_hour_window(
        datetime(2025, 11, 12, 17, 41, 33, tzinfo=timezone.utc)
    )

    assert window_start == datetime(2025, 11, 12, 14, 0, 0, tzinfo=timezone.utc)
    assert window_end == datetime(2025, 11, 12, 16, 0, 0, tzinfo=timezone.utc)


def test_get_latest_even_hour_window_handles_boundary() -> None:
    window_start, window_end = get_latest_even_hour_window(
        datetime(2025, 11, 12, 18, 0, 1, tzinfo=timezone.utc)
    )

    assert window_start == datetime(2025, 11, 12, 16, 0, 0, tzinfo=timezone.utc)
    assert window_end == datetime(2025, 11, 12, 18, 0, 0, tzinfo=timezone.utc)


def test_run_raffle_announces_when_no_whitelisted_eligible_miners(monkeypatch) -> None:
    window_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    window_end = datetime(2026, 1, 1, 2, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(
        "cogs.mine_raffle.get_latest_even_hour_window",
        lambda now: (window_start, window_end),
    )

    async def fake_get_wallet_map() -> dict[str, set[int]]:
        return {
            "alice.wam": {1},
            "bob.wam": {2},
            "charlie.wam": {3},
        }

    raffle = MineRaffle.__new__(MineRaffle)
    raffle.land_ids = {"1099512959648"}
    raffle._disabled_logged = False
    raffle._last_processed_window_end = None
    raffle.bot = SimpleNamespace(
        wax_con=object(),
        green_api=SimpleNamespace(get_monkeyconnect_wallet_to_discord_ids=fake_get_wallet_map),
    )
    raffle.log = lambda *_args, **_kwargs: None

    async def fake_collect(_window_start: datetime, _window_end: datetime) -> tuple[set[str], int]:
        return {"notonlist.wam"}, 5

    raffle._collect_recent_participants = fake_collect
    announce_mock = AsyncMock()
    raffle._announce_no_whitelist_eligible_miners = announce_mock

    asyncio.run(raffle._run_raffle())

    announce_mock.assert_awaited_once_with(
        window_start=window_start,
        window_end=window_end,
        whitelisted_users=3,
        mines_in_window=5,
        unique_miners_in_window=1,
    )
    assert raffle._last_processed_window_end == window_end


def test_announce_no_whitelist_eligible_miners_posts_window_message(monkeypatch) -> None:
    class FakeChannel:
        def __init__(self) -> None:
            self.messages: list[str] = []

        async def send(self, msg: str) -> None:
            self.messages.append(msg)

    class FakeGuild:
        def __init__(self, channel: FakeChannel) -> None:
            self.channel = channel

        def get_channel(self, _channel_id: int):
            return self.channel

    channel = FakeChannel()
    guild = FakeGuild(channel)
    raffle = MineRaffle.__new__(MineRaffle)
    raffle.bot = SimpleNamespace(get_guild=lambda _guild_id: guild)

    monkeypatch.setattr(
        "cogs.mine_raffle.get_collection_info",
        lambda _collection: SimpleNamespace(guild=123, announce_ch=456, emoji=":pick:"),
    )
    monkeypatch.setattr("cogs.mine_raffle.discord.TextChannel", FakeChannel)
    monkeypatch.setattr("cogs.mine_raffle.discord.Thread", FakeChannel)

    window_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    window_end = datetime(2026, 1, 1, 2, 0, 0, tzinfo=timezone.utc)
    asyncio.run(
        raffle._announce_no_whitelist_eligible_miners(
            window_start=window_start,
            window_end=window_end,
            whitelisted_users=27,
            mines_in_window=52,
            unique_miners_in_window=18,
        )
    )

    assert len(channel.messages) == 1
    assert (
        "No eligible miners for the raffle were on the whitelist (out of 27 whitelisted addresses)"
        in channel.messages[0]
    )
    assert "Mines in raffle window: 52" in channel.messages[0]
    assert "Unique miners in raffle window: 18" in channel.messages[0]
