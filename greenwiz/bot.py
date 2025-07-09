"""
Bot object.
"""

import asyncio
import datetime
import logging
import os
import pathlib
import sys
import traceback
from collections import Counter, defaultdict
from typing import Any, Awaitable, Union

import aiohttp
import discord
from discord.ext import commands
from redis import asyncio as aioredis
from utils import error_handler, settings, util
from utils.storage import StorageManager


# ==================== Bot Initialization ====================
class Bot(commands.Bot):
    """Initializes and manages a discord bot."""

    def __init__(self):
        # To be initialized async with startup
        self.owner_id = None
        self.appinfo = None
        self.debug_mode = set()
        self._tasks: list[asyncio.Task[None]] = []
        self.logging_status: list[str] = []
        self.storage: dict[Union[int, None, discord.Guild], StorageManager] = {}
        self.stats: dict[str, Union[int, Counter[str]]] = {
            "commands_counter": Counter(),
            "users_counter": Counter(),
            "message_counter": 0,
        }
        self.initialized = False
        self.extensions_to_load = 0
        self.original_extensions = 0
        self.cogs_initialized = defaultdict(default=False)
        self.cogs_ready = defaultdict(default=False)
        self.settings = settings
        self.start_time: datetime.datetime = util.utcnow()
        intents = discord.Intents.default() | discord.Intents(
            members=True, message_content=True
        )
        super().__init__(
            command_prefix=self.get_prefix,  # type: ignore[arg-type]
            case_insensitive=False,
            intents=intents,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False),
            activity=discord.Game("Starting up..."),
            status=discord.Status.do_not_disturb,
        )
        # Set debug display values
        self.debug = "DBUG"
        self.warn = "WARN"
        self.critical = "CRIT"
        self.cmd = "CMMD"
        self.prio = "PRIO"

    def run(self, *args, **kwargs):
        """Runs the bot."""
        super().run(self.settings.TOKEN, *args, **kwargs)

    @staticmethod
    def handler(_, context: dict[str, Any]) -> None:
        """Task error handler."""
        exc = context.get("exception", None)
        if exc:
            logging.getLogger(__name__).error("Task failed!", exc_info=exc)  # type: ignore

    async def setup_hook(self) -> None:
        """Initialize session and redis connection, and load extensions, then run."""
        asyncio.get_running_loop().set_exception_handler(self.handler)
        self.before_invoke(util.count_command)
        self.session: aiohttp.ClientSession = aiohttp.ClientSession()

        try:
            self.redis = aioredis.from_url(
                f"redis://{self.settings.REDIS_IP}",
                password=self.settings.REDIS_AUTH,
                db=self.settings.DB_NUM,
                encoding="utf-8",
                decode_responses=True,
            )
        except (ConnectionError, OSError) as error:
            self.log(
                f"Unable to connect to redis:\n\t{error}\n\tStartup aborted.", "CRIT"
            )
            await self.close()
            sys.exit(1)

        # An array of StorageManagers, one for each guild. The None key is meaningful here for
        # contexts without a guild, such as private messages, and allows the guild to be indexed
        #  directly.
        self.storage[None] = StorageManager(self)

        self.logging_status = list(
            (await self.redis.hgetall("settings:logging_status")).keys()
        )
        if self.logging_status is None or len(self.logging_status) == 0:
            self.logging_status = self.settings.DONT_LOG

        self.appinfo = await self.application_info()
        self.owner_id = self.appinfo.owner.id

        cogs = [f"{cog.parent}.{cog.stem}" for cog in pathlib.Path("cogs").glob("*.py")]
        self.original_extensions = self.extensions_to_load = len(cogs)
        for cog in cogs:
            try:
                await self.load_extension(cog)
            except commands.ExtensionError as error:
                self.log(f"Extension {cog} failed to load, skipping. ({error})", "WARN")
                self.extensions_to_load -= 1
                traceback.print_exc()
        self._tasks.append(asyncio.create_task(self.run_once_when_ready()))

    async def run_once_when_ready(self) -> None:
        """Contains initialization logic for the bot object that must be run once."""
        await self.wait_until_ready()
        # Initialize all guild storage managers.
        # Guild is a safe index because hash(discord.Guild) == guild.id >> 22
        for guild in self.guilds:
            self.storage[guild] = StorageManager(self, guild=guild)

        while len(self.cogs_ready) < self.extensions_to_load:
            await asyncio.sleep(0)
        await self.change_presence(
            status=discord.Status.online, activity=discord.Game(self.settings.STATUS)
        )
        self.initialized = True
        startup = util.utcnow() - self.start_time
        if self.user is not None:
            name = self.user.name
            _id = self.user.id
        else:
            name = "Unknown bot"
            _id = 0
        self.log(
            f"Logged in as {name} ({_id}) with {len(self.cogs_ready)}"
            f"/{self.original_extensions} cogs loaded"
            f" and ready to rumble after {startup.total_seconds():.3f} seconds.",
            severity="STRT",
        )

    async def on_guild_join(self, guild):
        """Triggered on joining a guild. Adds a storage manager for the guild."""
        self.storage[guild] = StorageManager(self, guild=guild)

    async def on_message(self, message):
        if isinstance(self.stats["message_counter"], int):
            self.stats["message_counter"] += 1
        if isinstance(self.stats["users_counter"], Counter):
            self.stats["users_counter"].update([message.author])
        await super().on_message(message)

    async def prep_close(self, reason="Shutting Down") -> None:
        """Unloads cogs, closes open sessions and sockets, in preparation for shutdown or
        restart."""
        self.log(reason, "SHUT")
        if self is None:
            return  # type: ignore[unreachable]
        await self.change_presence(
            status=discord.Status.do_not_disturb,
            activity=discord.Game(f"{reason}..."),
        )

        if isinstance(self.session, aiohttp.ClientSession):
            await self.session.close()
        await self.redis.close()
        await self.change_presence(status=discord.Status.offline)

    async def close(self) -> None:
        """Unloads cogs, closes open sessions and sockets, and shuts down."""
        await self.prep_close()
        await super().close()

    async def restart(self) -> None:
        """Try to restart self"""
        await self.prep_close(reason="Restarting")
        await super().close()
        os.execv(sys.executable, ["python"] + sys.argv)

    async def add_cog(self, cog: commands.Cog) -> None:  # type: ignore[override]
        """Adds a cog and logs it."""
        await super().add_cog(cog)
        self.log(f"Loaded cog {cog.qualified_name}.")

    async def get_prefix(  # type: ignore[override]
        self, message: discord.Message
    ) -> Union[str, Awaitable[str]]:
        """Returns the prefix for a given message context."""
        if message.guild is None:
            return commands.when_mentioned_or("")(self, message)  # type: ignore[return-value, no-any-return]
        if self.settings.ENV != "prod":
            return f"{self.settings.ENV}{self.settings.TEST_PREFIX_OVERRIDE}"
        try:
            guild_prefix = await self.storage[message.guild].get_setting("prefix")
        except KeyError:
            guild_prefix = self.settings.DEFAULT_PREFIX
        return commands.when_mentioned_or(guild_prefix)(self, message)  # type: ignore[return-value, no-any-return]

    async def set_prefix(self, guild: discord.Guild, prefix: str) -> None:
        """Set the prefix for a given guild"""
        await self.storage[guild].set_setting("prefix", prefix)

    def log(self, message: str, severity="INFO") -> None:
        """
        Prints message to console if bot's severity level warrants it.
        Allows more customizability in what to log and what not to log
         than classic critical, error, warn, info, debug.
        """
        if severity in self.logging_status and severity not in self.debug_mode:
            return
        print(f"[{severity}] {message}")
        if severity not in self.debug_mode:
            return
        try:
            channel = self.get_channel(877782340741505044)
            if channel and not (
                isinstance(channel, discord.ForumChannel)
                or isinstance(channel, discord.CategoryChannel)
            ):
                task = channel.send(f"[{severity}] {message}"[:1995])  # type: ignore[union-attr]
                asyncio.create_task(task)
        except (discord.HTTPException, discord.Forbidden, ValueError, TypeError):
            pass

    async def quiet_send(
        self, ctx: commands.Context[Any], message, delete_after=None
    ) -> None:
        """Send a message. Should sending fail, log the error at the debug level but otherwise fail
        silently."""
        debug = "DBUG"
        try:
            if delete_after:
                await ctx.send(message, delete_after=delete_after)
            else:
                await ctx.send(message)
        except discord.Forbidden:
            self.log(f"Insufficient permissions to send {message}", debug)
        except discord.HTTPException:
            self.log(f"Failed to send {message} due to a discord HTTPException.", debug)
        except (ValueError, TypeError):
            self.log(
                f"Failed to send {message} because files list is of the wrong size, reference is "
                f"not a Message or MessageReference, or both file and files parameters are "
                f"specified.",
                debug,
            )

    async def quiet_x(self, ctx: commands.Context[Any], reaction="❌") -> None:
        """React to a message with an :x: reaction. Should reaction, fail, log the error at the
        debug level but otherwise fail silently."""
        debug = "DBUG"
        if not ctx.message:
            self.log(
                f"Failed to react to {ctx} because it has no message parameter.", debug
            )
        try:
            await ctx.message.add_reaction(reaction)
        except discord.Forbidden:
            self.log(
                f"Insufficient permissions to react to {ctx.message} with an x.", debug
            )
        except discord.NotFound:
            self.log(f"Did not find {ctx.message} to react to with an x.")
        except discord.HTTPException:
            self.log(
                f"Failed to react to {ctx.message} with an x due to a discord HTTPException",
                debug,
            )
        except (ValueError, TypeError):
            self.log(
                f"Failed to react to {ctx.message} because the X reaction is not recognized "
                f"by discord."
            )

    async def quiet_fail(
        self, ctx: commands.Context[Any], message: str, delete: bool = True
    ) -> None:
        """React with an x and send the user an explanatory failure message. Should anything fail,
        log at the debug level but otherwise fail silently. Delete own response after 30 seconds.
        """
        resp = f"{ctx.author.name}, {message}"
        await self.quiet_x(ctx)
        if delete:
            await self.quiet_send(ctx, resp, delete_after=30)
        else:
            await self.quiet_send(ctx, resp, delete_after=None)
        return

    async def on_command_error(self, ctx: commands.Context[Any], error) -> None:
        """
        General bot error handler. The main thing here is if something goes very wrong, dm the bot
        owner the full error directly.
        :param ctx: Invoking context
        :param error: The error
        """
        await error_handler.handle_command_error(self, ctx, error)

    def uptime(self) -> datetime.timedelta:
        """Returns the time since bot startup."""
        return datetime.timedelta(util.utcnow() - self.start_time)  # type: ignore[arg-type]

    def startuptime(self):
        """Returns the time the bot started up."""
        stamp = int(self.start_time.timestamp() - 1)
        return f"<t:{stamp}:R>"
