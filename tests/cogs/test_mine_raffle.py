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


def test_collect_recent_participants_uses_time_cursor_with_subsecond_increment(monkeypatch) -> None:
    monkeypatch.setattr("cogs.mine_raffle.MINE_RAFFLE_QUERY_LIMIT", 3)
    monkeypatch.setattr("cogs.mine_raffle.MINE_RAFFLE_MAX_QUERY_REQUESTS", 20)

    window_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    window_end = datetime(2026, 1, 1, 0, 10, 0, tzinfo=timezone.utc)
    after_start = MineRaffle._hyperion_time(window_start)
    after_t1 = "2026-01-01T00:00:01.000"
    after_t1_next = "2026-01-01T00:00:01.001"

    responses_by_cursor: dict[str, list[dict[str, object]]] = {
        after_start: [
            {
                "timestamp": after_t1,
                "data": {"miner": "b52qw.wam", "land_id": "1099512959648"},
                "transaction_id": "tx-1",
            },
            {
                "timestamp": after_t1,
                "data": {"miner": "4h.qy.wam", "land_id": "1099512959648"},
                "transaction_id": "tx-2",
            },
            {
                "timestamp": after_t1,
                "data": {"miner": "mconstant.gm", "land_id": "1099512959648"},
                "transaction_id": "tx-3",
            },
        ],
        after_t1_next: [
            {
                "timestamp": "2026-01-01T00:00:02.000",
                "data": {"miner": "huilinvoiach", "land_id": "1099512959648"},
                "transaction_id": "tx-4",
            },
            {
                "timestamp": "2026-01-01T00:00:02.000",
                "data": {"miner": "qkzf2.wam", "land_id": "1099512959648"},
                "transaction_id": "tx-5",
            },
            {
                "timestamp": "2026-01-01T00:00:02.000",
                "data": {"miner": "niranr111dg3", "land_id": "1099512959648"},
                "transaction_id": "tx-6",
            },
        ],
    }
    observed_queries: list[str] = []
    observed_has_skip: list[bool] = []

    async def fake_get_hyperion_actions(query: dict[str, object]) -> dict[str, object]:
        after = str(query["after"])
        observed_queries.append(after)
        observed_has_skip.append("skip" in query)
        return {"total": {"value": 1, "relation": "eq"}, "simple_actions": responses_by_cursor.get(after, [])}

    raffle = MineRaffle.__new__(MineRaffle)
    raffle.land_ids = {"1099512959648"}
    raffle.bot = SimpleNamespace(
        wax_con=SimpleNamespace(get_hyperion_actions=fake_get_hyperion_actions),
        special_addr_list={"wam"},
    )
    raffle.log = lambda *_args, **_kwargs: None

    participants, mine_count = asyncio.run(
        raffle._collect_recent_participants(
            window_start=window_start,
            window_end=window_end,
        )
    )

    assert participants == {
        "b52qw.wam",
        "4h.qy.wam",
        "mconstant.gm",
        "huilinvoiach",
        "qkzf2.wam",
        "niranr111dg3",
    }
    assert mine_count == 6
    assert observed_queries == [after_start, after_t1_next, "2026-01-01T00:00:02.001"]
    assert observed_has_skip == [False, False, False]


def test_collect_recent_participants_stops_when_page_crosses_window_end(monkeypatch) -> None:
    monkeypatch.setattr("cogs.mine_raffle.MINE_RAFFLE_QUERY_LIMIT", 2)
    monkeypatch.setattr("cogs.mine_raffle.MINE_RAFFLE_MAX_QUERY_REQUESTS", 10)

    window_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    window_end = datetime(2026, 1, 1, 0, 0, 5, tzinfo=timezone.utc)
    after_start = MineRaffle._hyperion_time(window_start)
    after_t1 = "2026-01-01T00:00:01.000"
    after_t1_next = "2026-01-01T00:00:01.001"

    responses_by_cursor: dict[str, list[dict[str, object]]] = {
        after_start: [
            {
                "timestamp": after_t1,
                "data": {"miner": "b52qw.wam", "land_id": "1099512959648"},
                "transaction_id": "tx-1",
            },
            {
                "timestamp": after_t1,
                "data": {"miner": "4h.qy.wam", "land_id": "1099512959648"},
                "transaction_id": "tx-2",
            },
        ],
        after_t1_next: [
            {
                "timestamp": "2026-01-01T00:00:06.000",
                "data": {"miner": "mconstant.gm", "land_id": "1099512959648"},
                "transaction_id": "tx-3",
            },
            {
                "timestamp": "2026-01-01T00:00:06.000",
                "data": {"miner": "qkzf2.wam", "land_id": "1099512959648"},
                "transaction_id": "tx-4",
            },
        ],
    }
    observed_queries: list[str] = []
    observed_has_skip: list[bool] = []

    async def fake_get_hyperion_actions(query: dict[str, object]) -> dict[str, object]:
        after = str(query["after"])
        observed_queries.append(after)
        observed_has_skip.append("skip" in query)
        return {"total": {"value": 1, "relation": "eq"}, "simple_actions": responses_by_cursor.get(after, [])}

    raffle = MineRaffle.__new__(MineRaffle)
    raffle.land_ids = {"1099512959648"}
    raffle.bot = SimpleNamespace(
        wax_con=SimpleNamespace(get_hyperion_actions=fake_get_hyperion_actions),
        special_addr_list={"wam"},
    )
    raffle.log = lambda *_args, **_kwargs: None

    participants, mine_count = asyncio.run(
        raffle._collect_recent_participants(
            window_start=window_start,
            window_end=window_end,
        )
    )

    assert participants == {"b52qw.wam", "4h.qy.wam"}
    assert mine_count == 2
    assert observed_queries == [after_start, after_t1_next]
    assert observed_has_skip == [False, False]


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


def test_run_raffle_excludes_recent_winners_and_records_new_winner(monkeypatch) -> None:
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
        }

    storage = SimpleNamespace(
        get_mine_raffle_wallets_with_recent_rewards=AsyncMock(return_value={"alice.wam"}),
        record_mine_raffle_reward=AsyncMock(),
    )
    get_random_assets_mock = AsyncMock(return_value=[SimpleNamespace(asset_id=123456)])
    transfer_assets_mock = AsyncMock()

    raffle = MineRaffle.__new__(MineRaffle)
    raffle.land_ids = {"1099512959648"}
    raffle._disabled_logged = False
    raffle._last_processed_window_end = None
    raffle.bot = SimpleNamespace(
        wax_con=SimpleNamespace(
            get_random_assets_to_send=get_random_assets_mock,
            transfer_assets=transfer_assets_mock,
        ),
        green_api=SimpleNamespace(get_monkeyconnect_wallet_to_discord_ids=fake_get_wallet_map),
        storage={None: storage},
    )
    raffle.log = lambda *_args, **_kwargs: None

    async def fake_collect(_window_start: datetime, _window_end: datetime) -> tuple[set[str], int]:
        return {"alice.wam", "bob.wam"}, 4

    raffle._collect_recent_participants = fake_collect
    raffle._announce_winner = AsyncMock()

    asyncio.run(raffle._run_raffle())

    storage.get_mine_raffle_wallets_with_recent_rewards.assert_awaited_once()
    get_random_assets_mock.assert_awaited_once_with(user="bob.wam", num=1, collection="crptomonkeys")
    transfer_assets_mock.assert_awaited_once_with(
        receiver="bob.wam",
        asset_ids=[123456],
        sender="monKeymining raffle",
        sender_ac="crptomonkeys",
        memo="Mining raffle reward (2026-01-01 02:00 UTC)",
    )
    storage.record_mine_raffle_reward.assert_awaited_once()
    assert storage.record_mine_raffle_reward.await_args.kwargs["wallet"] == "bob.wam"
    raffle._announce_winner.assert_awaited_once()
    assert raffle._last_processed_window_end == window_end


def test_run_raffle_skips_when_all_whitelisted_miners_are_recent_winners(monkeypatch) -> None:
    window_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    window_end = datetime(2026, 1, 1, 2, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(
        "cogs.mine_raffle.get_latest_even_hour_window",
        lambda now: (window_start, window_end),
    )

    async def fake_get_wallet_map() -> dict[str, set[int]]:
        return {"alice.wam": {1}}

    storage = SimpleNamespace(
        get_mine_raffle_wallets_with_recent_rewards=AsyncMock(return_value={"alice.wam"}),
        record_mine_raffle_reward=AsyncMock(),
    )
    get_random_assets_mock = AsyncMock()
    transfer_assets_mock = AsyncMock()

    raffle = MineRaffle.__new__(MineRaffle)
    raffle.land_ids = {"1099512959648"}
    raffle._disabled_logged = False
    raffle._last_processed_window_end = None
    raffle.bot = SimpleNamespace(
        wax_con=SimpleNamespace(
            get_random_assets_to_send=get_random_assets_mock,
            transfer_assets=transfer_assets_mock,
        ),
        green_api=SimpleNamespace(get_monkeyconnect_wallet_to_discord_ids=fake_get_wallet_map),
        storage={None: storage},
    )
    raffle.log = lambda *_args, **_kwargs: None

    async def fake_collect(_window_start: datetime, _window_end: datetime) -> tuple[set[str], int]:
        return {"alice.wam"}, 1

    raffle._collect_recent_participants = fake_collect
    raffle._announce_winner = AsyncMock()
    raffle._announce_all_eligible_in_cooldown = AsyncMock()

    asyncio.run(raffle._run_raffle())

    storage.get_mine_raffle_wallets_with_recent_rewards.assert_awaited_once()
    get_random_assets_mock.assert_not_awaited()
    transfer_assets_mock.assert_not_awaited()
    storage.record_mine_raffle_reward.assert_not_awaited()
    raffle._announce_winner.assert_not_awaited()
    raffle._announce_all_eligible_in_cooldown.assert_awaited_once_with(
        window_start=window_start,
        window_end=window_end,
        eligible_whitelisted_miners=1,
        cooldown_blocked_miners=1,
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
    assert "No eligible miners for the raffle were on the whitelist out of 27 whitelisted addresses" in channel.messages[0]
    assert "52 mines and 18 unique miners" in channel.messages[0]


def test_announce_all_eligible_in_cooldown_posts_window_message(monkeypatch) -> None:
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
        raffle._announce_all_eligible_in_cooldown(
            window_start=window_start,
            window_end=window_end,
            eligible_whitelisted_miners=4,
            cooldown_blocked_miners=4,
        )
    )

    assert len(channel.messages) == 1
    assert "No raffle winner this round: all 4 eligible whitelisted miner(s) were in the 24-hour winner cooldown window (4 blocked)." in channel.messages[0]
