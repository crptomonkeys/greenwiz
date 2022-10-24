import asyncio
import random
from decimal import Decimal, InvalidOperation
from typing import Union, Awaitable, Optional

import discord

from utils.coerce_converters import sanitize_name
from utils.exceptions import InvalidInput, UnableToCompleteRequestedAction


class StorageManager:
    def __init__(self, bot, guild: discord.Guild = None) -> None:
        self.bot = bot
        self.redis = bot.redis
        if guild:
            self.guild: Optional[discord.Guild] = guild
            self.guild_id = guild.id
        else:
            self.guild = None
            self.guild_id = 0

    async def get_setting(self, setting: str, key: str = "") -> str:
        """Gets a redis setting for a specified id, for example a users' auth level"""
        if key == "":
            result = await self.redis.get(f"{self.guild_id}:settings:{setting}")
        else:
            result = await self.redis.hget(f"{self.guild_id}:settings:{setting}", key)
        if result is None:
            if setting == "prefix":
                result = self.bot.settings.DEFAULT_PREFIX
        return str(result)

    async def set_setting(self, setting: str, value: str, key: str = "") -> str:
        """Sets a redis setting for a specified id, for example a users' auth level"""
        if value is None:
            raise InvalidInput("Value should not be None.")
        if key == "":
            res = await self.redis.set(
                f"{self.guild_id}:settings:{setting}", str(value)
            )
        else:
            res = await self.redis.hset(
                f"{self.guild_id}:settings:{setting}", key, str(value)
            )
        if not res:
            raise UnableToCompleteRequestedAction(
                f"Fields were not properly added to redis db when saving {setting} "
                f"as {value} ({key})."
            )
        return value

    async def get_settings(self, num: int = 1000) -> dict[str, str]:
        """Returns up to 50 settings and their value for this server."""
        cur, keys = await self.redis.scan(
            match=f"{self.guild_id}:settings:*", count=num
        )
        results = dict()
        for key in keys:
            id_ = str(key).split(":")[-1][:-1]
            if await self.redis.type(key) == b"string":
                value = await self.redis.get(key)
            else:
                value = await self.redis.hgetall(key)
            results[id_] = value
        return results

    async def get_auth(self, user: discord.User) -> int:
        """Get the authorization level of a user"""
        if user.id == self.bot.owner_id:
            return 10
        try:
            result = int(await self.get_setting("auth", key=str(user.id)))
        except TypeError:
            return 0
        return result

    async def set_auth(self, user: discord.User, level: int) -> None:
        """Set the authorization level of a user"""
        await self.set_setting("auth", str(level), key=str(user.id))

    async def get_commanders(self) -> dict[int, int]:
        """Return the full list of commanders and their level."""
        result = await self.redis.hgetall(f"{self.guild_id}:settings:auth")
        return {int(key): int(value) for key, value in result.items()}

    async def get_stat_user(self, user: Union[discord.User, int], stat: str) -> str:
        """Gets a redis stat for a specified user"""
        if not isinstance(user, int):
            user = user.id
        result = await self.redis.hget(f"{self.guild_id}:stat:{stat}", str(user))
        if not result:
            result = ""
        return str(result)

    async def get_all_users_with_stat_balances(self, stat: str) -> dict[int, str]:
        """Return a dict of user_id: stat for all users with the given stat."""
        result = await self.redis.hgetall(f"{self.guild_id}:stat:{stat}")
        return {int(key): str(value) for key, value in dict(result).items()}

    async def get_all_users_with_int_balances(
        self, stat: str = "balance"
    ) -> dict[int, int]:
        """Return a dict of user_id: invested/balance for all users with given stat > 0."""
        res = await self.get_all_users_with_stat_balances(stat)
        return {key: int(value) for key, value in res.items() if int(value) > 0}

    async def set_stat_user(self, user: discord.User, stat: str, value: str) -> None:
        """Sets a redis stat for a user."""
        await self.redis.hset(f"{self.guild_id}:stat:{stat}", str(user.id), value)

    async def add_stat_user(
        self, user: Union[discord.User, int], stat: str, value: Decimal
    ) -> None:
        """Increases a redis stat for a user by a specified amount, atomically. Must be a Decimal stat."""
        if not isinstance(user, int):
            user = user.id
        await self.watch(f"stat:{stat}")
        bal = await self.get_stat_user(user, stat)
        try:
            new_bal = value + Decimal(bal)
        except InvalidOperation:
            new_bal = value + Decimal(0)
        try:
            if new_bal < 0:
                raise InvalidInput(f"{stat} can not be negative.")
            if new_bal > Decimal(10**22):
                new_bal = Decimal(10**22)
            tr = self.redis.multi_exec()
            tr.hset(f"{self.guild_id}:stat:{stat}", str(user), str(new_bal))
            await tr.execute()
            if not await self.get_stat_user(user, stat) == str(new_bal):
                raise UnableToCompleteRequestedAction("Try running this command again.")
        finally:
            await self.redis.unwatch()

    def watch(self, stat_name) -> Awaitable[str]:
        """Returns a future for redis-watching a specified stat. Just for readability."""
        return self.redis.watch(f"{self.guild_id}:{stat_name}")  # type: ignore

    async def recent_activity_to_activity(
        self, user_id: int, actweight: int = 0
    ) -> None:
        """Converts all of a user's recent activity to long-term activity points."""
        tx = [
            self.watch("activity"),
            self.watch("recent_activity"),
        ]
        await asyncio.gather(*tx)
        try:
            transference = await self.redis.hget(
                f"{self.guild_id}:recent_activity", user_id
            )
            if transference == 0:
                return
            if int(transference) <= 0:
                raise InvalidInput("User recent activity can not be less than 1")
            tr = self.redis.multi_exec()
            tr.incrby(f"{self.guild_id}:activity", user_id, transference)
            tr.hset(f"{self.guild_id}:recent_activity", user_id, 0)
            await tr.execute()
        finally:
            await self.redis.unwatch()

    async def do_activity_update(self) -> int:
        """Update activity scores for all users.
        Returns the number of users updated."""
        activities = await self.get_all_users_with_int_balances("activity")
        actweight = Decimal(await self.get_setting("actweight"))
        for user_id, activity in activities.items():
            await self.recent_activity_to_activity(user_id, actweight=int(actweight))
        return len(activities)

    async def get_all_stat(self, stat) -> dict[int, Decimal]:
        """Return all user's balances"""
        result = await self.redis.hgetall(f"{self.guild_id}:stat:{stat}")
        return {int(key): Decimal(value) for key, value in result.items()}

    async def remove_data(self, user: Union[discord.User, int]) -> None:
        """Deletes a user's data."""
        if isinstance(user, discord.User):
            uid = user.id
        else:
            uid = user
        for stat in ["balance", "invested", "activity"]:
            await self.redis.hdel(f"{self.guild_id}:stat:{stat}", str(uid))

    async def add_warning(self, user: discord.User, warning: str) -> int:
        """Add a warning for a user"""
        warning_num = await self.redis.incr("warnings")
        await self.redis.append(
            f"{self.guild_id}:warnings:{user.id}", f"\n{warning_num}) {warning}"
        )
        return int(warning_num)

    async def get_warnings(self, user: discord.User) -> str:
        """Get all warnings for a user"""
        warnings = await self.redis.get(f"{self.guild_id}:warnings:{user.id}")
        return str(warnings)

    async def clear_warnings(self, user: discord.User) -> None:
        """Sets a user's warnings to none."""
        await self.redis.set(f"{self.guild_id}:warnings:{user.id}", "")

    @sanitize_name
    async def get_note(self, user: discord.User, name: str) -> str:
        """Retrieves a note"""
        note = await self.redis.hget(f"notes:{user.id}", name)
        if not note or len(note) == 0:
            return "Not found."
        return str(note)

    @sanitize_name
    async def set_note(self, user: discord.User, name: str, note: str) -> None:
        """Saves or updates a note"""
        await self.redis.hset(f"notes:{user.id}", name, note)

    @sanitize_name
    async def set_codex(self, name: str, note: str, style: str = "codex") -> str:
        """Saves or updates a server-wide note/codex."""
        await self.redis.hset(f"{self.guild_id}:{style}", name, note)
        return name

    @sanitize_name
    async def get_codex(self, name: str, style: str = "codex") -> str:
        """Retrieves a server-wide note/codex."""
        note = await self.redis.hget(f"{self.guild_id}:{style}", name)
        if not note or len(note) == 0:
            return "Not found."
        return str(note)

    @sanitize_name
    async def del_codex(self, name: str, style: str = "codex") -> None:
        """Deletes specified codex entry."""
        await self.redis.hdel(f"{self.guild_id}:{style}", name)

    async def get_codex_names(self, style: str = "codex") -> dict[str, str]:
        """Retrieves up to 50 codex names."""
        res = await self.redis.hgetall(f"{self.guild_id}:{style}")
        return dict(res)

    async def get_random_codex(self, style: str = "codex") -> tuple[str, str]:
        """Retrieves a random codex."""
        res = await self.redis.hgetall(f"{self.guild_id}:{style}")
        try:
            selection: tuple[str, str] = random.choice(list(res.items()))
        except (KeyError, IndexError):
            return "-1", f"No {style}s stored."
        return selection

    async def inc_trivia_points(self, user: discord.User, points: int = 1) -> int:
        """Increments the number of trivia points talied for a given user for this server."""
        return int(
            await self.redis.hincrby(f"{self.guild}:trivia", str(user.id), points)
        )

    async def return_and_reset_trivia(self) -> dict[int, int]:
        """Returns the full trivia result and deletes the trivia record."""
        res = await self.redis.hgetall(f"{self.guild}:trivia")
        await self.redis.delete(f"{self.guild}:trivia")
        return {int(key): val for key, val in res.items()}
