import random
import traceback
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

import discord
from discord.ext import tasks  # type: ignore

from utils.meta_cog import MetaCog
from utils.settings import (
    MINE_RAFFLE_ACTION_ACCOUNT,
    MINE_RAFFLE_ACTION_NAME,
    MINE_RAFFLE_COLLECTION,
    MINE_RAFFLE_INTERVAL_SECONDS,
    MINE_RAFFLE_LAND_IDS,
    MINE_RAFFLE_WINDOW_SECONDS,
)
from wax_chain.collection_config import get_collection_info
from wax_chain.wax_addresses import is_valid_wax_address

MINE_RAFFLE_QUERY_LIMIT = 500
MINE_RAFFLE_QUERY_CAP = 5000


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
    target_land_ids = {str(item) for item in land_ids}
    participants: set[str] = set()
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
        if is_valid_wax_address(
            miner, valid_specials=valid_specials, case_sensitive=True
        ):
            participants.add(miner)
    return participants


class MineRaffle(MetaCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.land_ids = {
            str(land_id).strip() for land_id in MINE_RAFFLE_LAND_IDS if str(land_id).strip()
        }
        self._disabled_logged = False
        self.mine_raffle.start()
        self.bot.log(
            "Started mine raffle task (1 raffle every 2 hours).", self.bot.debug
        )

    def cog_unload(self):
        self.mine_raffle.cancel()
        self.bot.log("Ended mine raffle task.", self.bot.debug)

    @staticmethod
    def _hyperion_time(value: datetime) -> str:
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000")

    async def _collect_recent_participants(
        self, window_start: datetime, window_end: datetime
    ) -> set[str]:
        participants: set[str] = set()
        skip = 0
        valid_specials = (
            self.bot.special_addr_list
            if hasattr(self.bot, "special_addr_list")
            and isinstance(self.bot.special_addr_list, set)
            else None
        )
        while skip < MINE_RAFFLE_QUERY_CAP:
            response = await self.bot.wax_con.get_hyperion_actions(
                {
                    "account": MINE_RAFFLE_ACTION_ACCOUNT,
                    "act.name": MINE_RAFFLE_ACTION_NAME,
                    "after": self._hyperion_time(window_start),
                    "before": self._hyperion_time(window_end),
                    "limit": MINE_RAFFLE_QUERY_LIMIT,
                    "skip": skip,
                    "sort": "desc",
                }
            )
            actions = response.get("actions", [])
            if not isinstance(actions, list):
                self.log(
                    f"Mine raffle received invalid actions payload: {response}", "WARN"
                )
                break

            participants.update(
                extract_mine_participants(
                    actions, self.land_ids, window_start, valid_specials=valid_specials
                )
            )
            if len(actions) < MINE_RAFFLE_QUERY_LIMIT:
                break
            skip += len(actions)
        return participants

    async def _announce_winner(
        self,
        winner: str,
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
            f"Winner: `{winner}`\n"
            f"Prize: [#{asset_id}](<https://neftyblocks.com/assets/{asset_id}>) "
            f"from `{MINE_RAFFLE_COLLECTION}`."
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

        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(seconds=MINE_RAFFLE_WINDOW_SECONDS)
        participants = await self._collect_recent_participants(window_start, window_end)
        if len(participants) == 0:
            self.log(
                f"Mine raffle window {window_start} to {window_end}: no eligible miners found."
            )
            return

        winner = random.choice(sorted(participants))
        selected_assets = await self.bot.wax_con.get_random_assets_to_send(
            user=winner, num=1, collection=MINE_RAFFLE_COLLECTION
        )
        asset_id = selected_assets[0].asset_id
        await self.bot.wax_con.transfer_assets(
            receiver=winner,
            asset_ids=[asset_id],
            sender="Mine raffle task",
            sender_ac=MINE_RAFFLE_COLLECTION,
            memo=f"Mining raffle reward ({window_end.strftime('%Y-%m-%d %H:%M UTC')})",
        )
        self.log(
            f"Mine raffle transferred asset {asset_id} to {winner} "
            f"from {len(participants)} entrants."
        )
        await self._announce_winner(
            winner=winner,
            asset_id=asset_id,
            entrants=len(participants),
            window_start=window_start,
            window_end=window_end,
        )

    @tasks.loop(seconds=MINE_RAFFLE_INTERVAL_SECONDS)
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
