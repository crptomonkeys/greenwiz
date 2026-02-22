import asyncio
import random
import traceback
from datetime import datetime, timedelta, timezone
from datetime import time as dtime
from typing import Any, Iterable, Optional

import discord
from discord.ext import tasks  # type: ignore
from utils.green_api_wrapper import GreenApi
from utils.meta_cog import MetaCog
from utils.settings import (
    MINE_RAFFLE_ACTION_ACCOUNT,
    MINE_RAFFLE_ACTION_NAME,
    MINE_RAFFLE_COLLECTION,
    MINE_RAFFLE_LAND_IDS,
)
from wax_chain.collection_config import get_collection_info
from wax_chain.wax_addresses import is_valid_wax_address

MINE_RAFFLE_QUERY_LIMIT = 1000
MINE_RAFFLE_MAX_QUERY_REQUESTS = 2000
MINE_RAFFLE_QUERY_RETRIES = 4
MINE_RAFFLE_RETRY_BASE_SECONDS = 0.5
MINE_RAFFLE_TIMES_UTC = [dtime(hour=hour, minute=0, second=0, tzinfo=timezone.utc) for hour in range(0, 24, 2)]


def parse_hyperion_timestamp(timestamp: str) -> Optional[datetime]:
    if timestamp == "":
        return None
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def extract_mine_participants(
    actions: list[dict[str, Any]],
    land_ids: Iterable[str],
    window_start: datetime,
    valid_specials: Optional[set[str]] = None,
) -> set[str]:
    participants, _mine_count = extract_mine_window_stats(
        actions=actions,
        land_ids=land_ids,
        window_start=window_start,
        valid_specials=valid_specials,
    )
    return participants


def extract_mine_window_stats(
    actions: list[dict[str, Any]],
    land_ids: Iterable[str],
    window_start: datetime,
    valid_specials: Optional[set[str]] = None,
) -> tuple[set[str], int]:
    target_land_ids = {str(item) for item in land_ids}
    participants: set[str] = set()
    mine_count = 0
    for action in actions:
        if not isinstance(action, dict):
            continue
        timestamp = parse_hyperion_timestamp(str(action.get("timestamp", "")))
        if timestamp is None or timestamp < window_start:
            continue
        act = action.get("act")
        if not isinstance(act, dict):
            continue
        data = act.get("data")
        if not isinstance(data, dict):
            continue
        land_id = str(data.get("land_id", "")).strip()
        if land_id not in target_land_ids:
            continue
        miner = str(data.get("miner", "")).strip().lower()
        if miner == "":
            continue
        if is_valid_wax_address(miner, valid_specials=valid_specials, case_sensitive=True):
            mine_count += 1
            participants.add(miner)
    return participants, mine_count


def filter_participants_by_whitelist(participants: set[str], whitelist: set[str]) -> set[str]:
    if len(whitelist) < 1:
        return set()
    return {entry for entry in participants if entry in whitelist}


def format_winner_discord(discord_ids: list[int]) -> str:
    if len(discord_ids) < 1:
        return "Unknown"
    winner_id = discord_ids[0]
    return f"<@{winner_id}> (`{winner_id}`)"


def get_latest_even_hour_window(now: datetime) -> tuple[datetime, datetime]:
    """Return the latest closed two-hour UTC window aligned to even-hour boundaries."""
    window_end = now.astimezone(timezone.utc).replace(
        minute=0,
        second=0,
        microsecond=0,
    )
    if window_end.hour % 2 != 0:
        window_end -= timedelta(hours=1)
    window_start = window_end - timedelta(hours=2)
    return window_start, window_end


class MineRaffle(MetaCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.land_ids = {str(land_id).strip() for land_id in MINE_RAFFLE_LAND_IDS if str(land_id).strip()}
        if not hasattr(self.bot, "green_api"):
            self.bot.green_api = GreenApi(self.session)
        self._last_processed_window_end: Optional[datetime] = None
        self._disabled_logged = False
        self.mine_raffle.start()
        self.bot.log("Started mine raffle task (1 raffle every 2 hours UTC).", self.bot.debug)

    def cog_unload(self):
        self.mine_raffle.cancel()
        self.bot.log("Ended mine raffle task.", self.bot.debug)

    @staticmethod
    def _hyperion_time(value: datetime) -> str:
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]

    @staticmethod
    def _extract_action_records(response: dict[str, Any]) -> Optional[list[dict[str, Any]]]:
        simple_actions = response.get("simple_actions")
        if isinstance(simple_actions, list):
            return [entry for entry in simple_actions if isinstance(entry, dict)]
        actions = response.get("actions")
        if isinstance(actions, list):
            return [entry for entry in actions if isinstance(entry, dict)]
        return None

    def _parse_mine_action(
        self,
        action: dict[str, Any],
        window_start: datetime,
        window_end: datetime,
        valid_specials: Optional[set[str]],
    ) -> Optional[tuple[str, tuple[str, str, str, str, str]]]:
        timestamp = parse_hyperion_timestamp(str(action.get("timestamp", "")))
        if timestamp is None or timestamp < window_start or timestamp > window_end:
            return None

        data = action.get("data")
        if not isinstance(data, dict):
            act = action.get("act")
            if not isinstance(act, dict):
                return None
            data = act.get("data")
            if not isinstance(data, dict):
                return None

        land_id = str(data.get("land_id", "")).strip()
        if land_id not in self.land_ids:
            return None

        miner = str(data.get("miner", "")).strip().lower()
        if miner == "":
            return None
        if not is_valid_wax_address(miner, valid_specials=valid_specials, case_sensitive=True):
            return None

        tx_id = str(action.get("transaction_id", "")).strip()
        if tx_id == "":
            tx_id = str(action.get("trx_id", "")).strip()
        global_sequence = str(action.get("global_sequence", "")).strip()
        block = str(action.get("block", "")).strip()
        if block == "":
            block = str(action.get("block_num", "")).strip()
        dedupe_key = (
            tx_id,
            global_sequence,
            block,
            timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            f"{miner}:{land_id}",
        )
        return miner, dedupe_key

    async def _query_hyperion_actions(
        self,
        query_start: datetime,
    ) -> dict[str, Any]:
        params = {
            "account": MINE_RAFFLE_ACTION_ACCOUNT,
            "act.name": MINE_RAFFLE_ACTION_NAME,
            "filter": f"{MINE_RAFFLE_ACTION_ACCOUNT}:{MINE_RAFFLE_ACTION_NAME}",
            "after": self._hyperion_time(query_start),
            "limit": MINE_RAFFLE_QUERY_LIMIT,
            "sort": "asc",
            "simple": "true",
        }
        retry_delay = MINE_RAFFLE_RETRY_BASE_SECONDS
        for attempt in range(1, MINE_RAFFLE_QUERY_RETRIES + 1):
            try:
                return await self.bot.wax_con.get_hyperion_actions(params)
            except Exception as e:
                if attempt >= MINE_RAFFLE_QUERY_RETRIES:
                    raise
                self.log(
                    "Mine raffle Hyperion query failed "
                    f"(attempt {attempt}/{MINE_RAFFLE_QUERY_RETRIES}) with {type(e).__name__}::{e}. "
                    f"Retrying in {retry_delay:.1f}s.",
                    "WARN",
                )
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
        raise RuntimeError("Mine raffle Hyperion query retries exhausted unexpectedly.")

    async def _collect_recent_participants(self, window_start: datetime, window_end: datetime) -> tuple[set[str], int]:
        participants: set[str] = set()
        mine_count = 0
        seen_mines: set[tuple[str, str, str, str, str]] = set()
        valid_specials = (
            self.bot.special_addr_list
            if hasattr(self.bot, "special_addr_list") and isinstance(self.bot.special_addr_list, set)
            else None
        )
        cursor_start = window_start
        request_count = 0

        while cursor_start <= window_end and request_count < MINE_RAFFLE_MAX_QUERY_REQUESTS:
            response = await self._query_hyperion_actions(cursor_start)
            request_count += 1
            actions = self._extract_action_records(response)
            if actions is None:
                self.log(f"Mine raffle received invalid actions payload: {response}", "WARN")
                break
            if len(actions) == 0:
                break

            latest_timestamp: Optional[datetime] = None
            for action in actions:
                action_timestamp = parse_hyperion_timestamp(str(action.get("timestamp", "")))
                if action_timestamp is not None and (latest_timestamp is None or action_timestamp > latest_timestamp):
                    latest_timestamp = action_timestamp

                parsed = self._parse_mine_action(action, window_start, window_end, valid_specials)
                if parsed is None:
                    continue
                miner, dedupe_key = parsed
                if dedupe_key in seen_mines:
                    continue
                seen_mines.add(dedupe_key)
                mine_count += 1
                participants.add(miner)

            if latest_timestamp is None:
                self.log(
                    "Mine raffle could not parse timestamps from Hyperion actions page; ending collection early.",
                    "WARN",
                )
                break

            if latest_timestamp > window_end:
                break

            next_cursor_start = latest_timestamp + timedelta(milliseconds=1)
            if next_cursor_start <= cursor_start:
                next_cursor_start = cursor_start + timedelta(milliseconds=1)
            cursor_start = next_cursor_start

            if len(actions) < MINE_RAFFLE_QUERY_LIMIT:
                break

        if request_count >= MINE_RAFFLE_MAX_QUERY_REQUESTS:
            self.log(
                f"Mine raffle hit query request cap ({MINE_RAFFLE_MAX_QUERY_REQUESTS}) for window "
                f"{window_start} to {window_end}.",
                "WARN",
            )

        return participants, mine_count

    async def _announce_winner(
        self,
        winner_wallet: str,
        winner_discord_ids: list[int],
        asset_id: int,
        entrants: int,
        window_start: datetime,
        window_end: datetime,
    ) -> None:
        cinfo = get_collection_info(MINE_RAFFLE_COLLECTION)
        guild = self.bot.get_guild(cinfo.guild)
        if guild is None:
            return
        channel = guild.get_channel(cinfo.announce_ch)
        if channel is None or not isinstance(channel, (discord.TextChannel, discord.Thread)):
            return

        window_start_str = window_start.strftime("%Y-%m-%d %H:%M")
        window_end_str = window_end.strftime("%Y-%m-%d %H:%M")
        msg = (
            f"{cinfo.emoji} **Mining Raffle Winner**\n"
            f"Window: {window_start_str} to {window_end_str} UTC\n"
            f"Eligible miners: {entrants}\n"
            f"Winner: {format_winner_discord(winner_discord_ids)} - "
            f"`{winner_wallet}`\n"
            f"Prize: [#{asset_id}](<https://neftyblocks.com/assets/{asset_id}>) "
            f"from `{MINE_RAFFLE_COLLECTION}`."
            "[Click here](<https://www.cryptomonkeys.cc/monkeymining>) for details on how to participate."
        )
        try:
            await channel.send(msg)
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def _announce_no_whitelist_eligible_miners(
        self,
        window_start: datetime,
        window_end: datetime,
        whitelisted_users: int,
        mines_in_window: int,
        unique_miners_in_window: int,
    ) -> None:
        cinfo = get_collection_info(MINE_RAFFLE_COLLECTION)
        guild = self.bot.get_guild(cinfo.guild)
        if guild is None:
            return
        channel = guild.get_channel(cinfo.announce_ch)
        if channel is None or not isinstance(channel, (discord.TextChannel, discord.Thread)):
            return

        window_start_str = window_start.strftime("%Y-%m-%d %H:%M")
        window_end_str = window_end.strftime("%Y-%m-%d %H:%M")
        msg = (
            f"{cinfo.emoji} **Mining Raffle**\n"
            f"Window: {window_start_str} to {window_end_str} UTC\n"
            f"No eligible miners for the raffle were on the whitelist out of {whitelisted_users} whitelisted "
            f"addresses, {mines_in_window} mines and {unique_miners_in_window} unique miners.\n"
            "[Click here](<https://www.cryptomonkeys.cc/monkeymining>) for details on how to participate."
        )
        try:
            await channel.send(msg)
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def _run_raffle(self) -> None:
        if len(self.land_ids) == 0:
            if not self._disabled_logged:
                self.log(
                    "Mine raffle is disabled because MINE_RAFFLE_LAND_IDS is empty.",
                    "WARN",
                )
                self._disabled_logged = True
            return
        self._disabled_logged = False

        if not hasattr(self.bot, "wax_con"):
            self.log("Mine raffle skipped because wax_con is unavailable.", "WARN")
            return

        window_start, window_end = get_latest_even_hour_window(datetime.now(timezone.utc))
        if self._last_processed_window_end == window_end:
            return
        participants, mine_count = await self._collect_recent_participants(window_start, window_end)
        if len(participants) == 0:
            self.log(f"Mine raffle window {window_start} to {window_end}: no eligible miners found.")
            self._last_processed_window_end = window_end
            return
        unique_miners_in_window = len(participants)
        wallet_to_discord_ids = await self.bot.green_api.get_monkeyconnect_wallet_to_discord_ids()
        monkeyconnect_whitelist = set(wallet_to_discord_ids.keys())
        participants = filter_participants_by_whitelist(participants, monkeyconnect_whitelist)
        if len(participants) == 0:
            self.log(
                f"Mine raffle window {window_start} to {window_end}: "
                "no eligible miners were on the monKeyconnect whitelist."
            )
            await self._announce_no_whitelist_eligible_miners(
                window_start=window_start,
                window_end=window_end,
                whitelisted_users=len(monkeyconnect_whitelist),
                mines_in_window=mine_count,
                unique_miners_in_window=unique_miners_in_window,
            )
            self._last_processed_window_end = window_end
            return

        winner_wallet = random.choice(sorted(participants))
        winner_discord_ids = sorted(wallet_to_discord_ids.get(winner_wallet, set()))
        selected_assets = await self.bot.wax_con.get_random_assets_to_send(
            user=winner_wallet, num=1, collection=MINE_RAFFLE_COLLECTION
        )
        asset_id = selected_assets[0].asset_id
        await self.bot.wax_con.transfer_assets(
            receiver=winner_wallet,
            asset_ids=[asset_id],
            sender="monKeymining raffle",
            sender_ac=MINE_RAFFLE_COLLECTION,
            memo=f"Mining raffle reward ({window_end.strftime('%Y-%m-%d %H:%M UTC')})",
        )
        self.log(f"Mine raffle transferred asset {asset_id} to {winner_wallet} from {len(participants)} entrants.")
        await self._announce_winner(
            winner_wallet=winner_wallet,
            winner_discord_ids=winner_discord_ids,
            asset_id=asset_id,
            entrants=len(participants),
            window_start=window_start,
            window_end=window_end,
        )
        self._last_processed_window_end = window_end

    @tasks.loop(time=MINE_RAFFLE_TIMES_UTC)
    async def mine_raffle(self):
        try:
            await self._run_raffle()
        except Exception as e:
            lines = traceback.format_exception(type(e), e, e.__traceback__)
            traceback_text = "```py\n" + "".join(lines) + "\n```"
            self.log(f"Mine raffle loop failed with {type(e)}::{e}\n{traceback_text}")

    @mine_raffle.before_loop
    async def before_mine_raffle(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(MineRaffle(bot))
