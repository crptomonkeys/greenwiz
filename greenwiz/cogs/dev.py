import ast
import asyncio
import copy
import textwrap
import time
import timeit
import typing

import discord
from discord.ext import commands

from utils.meta_cog import MetaCog
from utils.util import embed_footer
from wax_chain.collection_config import collections


def insert_returns(body):
    # Return the last value set in the command
    if isinstance(body[-1], ast.Expr):
        body[-1] = ast.Return(body[-1].value)
        ast.fix_missing_locations(body[-1])
    # Insert if statements into body
    if isinstance(body[-1], ast.If):
        insert_returns(body[-1].body)
        insert_returns(body[-1].orelse)
    # Insert with blocks into body
    if isinstance(body[-1], ast.With):
        insert_returns(body[-1].body)


def fanta():
    async def user_auth_check(ctx):
        if not hasattr(ctx.author, "roles"):
            return False
        for role in ctx.author.roles:
            if role.name == "Jungle Fanta":
                return True
            # if ctx.author.id == 125449182663278592:
            #    return True
        return False

    return user_auth_check


class Dev(MetaCog):
    def __init__(self, bot):
        super().__init__(bot)
        if hasattr(self.bot, "deltime"):
            self.deltime = self.bot.deltime
        else:
            self.deltime = 30

    # ==================== Commands ====================

    @commands.command(aliases=["dev_say"])
    @commands.is_owner()
    async def dev_echo(self, ctx: commands.Context, *, message: str):
        """
        Have the bot repeat your message.
        """
        try:
            await ctx.message.delete()  # delete the command
        except discord.Forbidden:
            pass
        await ctx.send(message)
        self.log(f"Echo command used by {ctx.author} with message {message}.", "CMMD")

    @commands.command(name="sendmsg", aliases=["dm", "message"])
    @commands.is_owner()
    async def send(
        self,
        ctx: commands.Context,
        user: discord.User,
        *,
        message: typing.Optional[str] = None,
    ):
        """
        DM someone from the bot.
        User: The user to message
        Message: The message to send
        """
        message = message or "Someone is pranking you bro."
        try:
            await ctx.message.delete()  # delete the command
        except discord.Forbidden:
            pass
        await ctx.send("Message sent.", delete_after=self.deltime)
        await user.send(message)
        self.log(
            f"Send command used by {ctx.author} to user {user} with message {message}.",
            "CMMD",
        )

    @commands.group(name="auth", aliases=["who", "check", "authorize"])
    @commands.is_owner()
    async def autho(self, ctx):
        """
        Check the auth level of a user
        Member: The discord member to check the auth level of
        You can use auth set <user> <level> if you have auth level 7
        """
        # await ctx.send('Use auth check, auth set or auth all')
        self.log(f"Auth command used by {ctx.author}.", "CMMD")

    @commands.command(name="restart", hidden=True, pass_context=False)
    @commands.is_owner()
    async def restart(self, ctx) -> None:
        """
        Restart the bot... hopefully. A lot could go wrong with this, so relying on it isn't recommended.
        :return:
        :rtype:
        """
        if ctx is not None:
            await self.bot.restart()

    @autho.command()
    @commands.is_owner()
    async def check(
        self,
        ctx: commands.Context,
        user: typing.Optional[discord.User] = None,
        detail: str = "",
    ):
        """Check someone's auth level. Requires auth 2."""
        if user is None:
            user = ctx.author
        try:
            auth_level = await self.storage[ctx.guild.id].get_auth(user)
        except AttributeError:
            auth_level = 0
        embed = discord.Embed(title="", description="", color=user.color)
        embed.set_author(
            icon_url=user.display_avatar.url,
            name=f"{user} is " f"authorized at level {auth_level}",
        )
        if detail != "":
            perms = ""
            for perm in sorted(self.bot.PERMS_INFO, reverse=True):
                if perm <= auth_level:
                    perms += str(perm) + ": " + self.bot.PERMS_INFO.get(perm) + "\n"
            embed.add_field(name="The Details:", value=perms)
        embed.set_footer(text=embed_footer(ctx.author))
        await ctx.send(content=None, embed=embed, delete_after=self.deltime * 5)
        await ctx.message.delete(delay=self.deltime)  # delete the command
        self.log(
            f"Auth check command used by {ctx.author}, {user} is authorized at level {auth_level}.",
            "CMMD",
        )

    @autho.command()
    @commands.is_owner()
    async def set(self, ctx: commands.Context, user: discord.User, level: int):
        """Set someone's auth level. Requires at least auth 5 and a higher auth than you're giving them."""
        invoker_auth = await self.storage[ctx.guild].get_auth(ctx.author)
        target_auth = await self.storage[ctx.guild].get_auth(user)
        if invoker_auth <= level:
            return await ctx.send(
                "You can not set someone's auth level higher than or equal to your own."
            )
        if target_auth >= invoker_auth:
            return await ctx.send(
                "You can't change the auth level of someone with your auth level or higher."
            )

        await self.storage[ctx.guild].set_auth(user, level)
        result = f"Changed {user} auth level to {level} on {ctx.author}'s authority."
        self.log(result, "PRIO")
        await ctx.send(result)
        self.log(
            f"Authset command used by {ctx.author} to set {user}'s auth level to {level}.",
            "CMMD",
        )

    @autho.command(name="all")
    @commands.is_owner()
    async def all_commanders(self, ctx):
        """Display all elevated-auth users. Requires auth 5."""
        commanders = await self.storage[ctx.guild].get_commanders()

        embed = discord.Embed(title="", description="", color=ctx.author.color)
        embed.set_author(icon_url=ctx.author.display_avatar.url, name="Here you go:")
        message = ""
        for c in commanders:
            message += (
                str(await self.bot.fetch_user(c)) + ": " + str(commanders[c]) + "\n"
            )
        embed.add_field(name="Bot Commanders:", value=message)
        embed.set_footer(text=embed_footer(ctx.author))
        await ctx.send(content=None, embed=embed)
        self.log(f"Auth All command used by {ctx.author}.", "CMMD")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def load(self, ctx: commands.Context, extension: str) -> None:
        """
        Load a specified cog dynamically from the cogs folder.
        :param extension: The name of the cog to unload
        """
        # Sanitize input
        extension = extension.replace(".", "")
        await self.bot.load_extension(f"cogs.{extension}")
        self.log(f"Loaded {extension}.")
        await ctx.send(f"Loaded {extension}.", delete_after=15)
        await ctx.message.delete(delay=15)  # delete the command

    @commands.command()
    @commands.is_owner()
    async def unload(self, ctx: commands.Context, extension: str):
        """
        Unload a cog
        Extension: The cog to unload
        """
        # Sanitize input
        extension = extension.replace(".", "")
        await self.bot.unload_extension(f"cogs.{extension}")
        self.log(f"Unloaded {extension}")
        await ctx.send(f"Unloaded {extension}.", delete_after=self.deltime)
        await ctx.message.delete(delay=self.deltime)  # delete the command
        self.log(f"Unload command used by {ctx.author} on cog {extension}.", "CMMD")

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx: commands.Context, extension: str):
        """
        Reload a cog
        Extension: The cog to reload
        """
        # Sanitize input
        extension = extension.replace(".", "")
        try:
            await self.bot.unload_extension(f"cogs.{extension}")
        except discord.ext.commands.errors.ExtensionNotLoaded:
            await ctx.send(f"Cog {extension} wasn't loaded, loading it now.")
        await self.bot.load_extension(f"cogs.{extension}")
        self.log(f"Reloaded {extension}")
        await ctx.send(f"Reloaded {extension}", delete_after=self.deltime)
        await ctx.message.delete(delay=self.deltime)  # delete the command
        self.log(f"Reload command used by {ctx.author} on cog {extension}.", "CMMD")

    @commands.command()
    @commands.is_owner()
    async def status(self, ctx: commands.Context, *, message: str = ""):
        """
        Change the bot's "playing" status
        Message: The message to change it to
        """
        await self.bot.change_presence(activity=discord.Game(message))
        self.log(f"Updated status to {message}.")
        await ctx.send(f"Updated status to {message}.", delete_after=self.deltime)
        await ctx.message.delete(delay=self.deltime)  # delete the command
        self.log(
            f"Status command used by {ctx.author} to set bot status to {message}.",
            "CMMD",
        )

    @commands.command(name="eval", hidden=True)
    @commands.is_owner()
    async def eval_(self, ctx: commands.Context, *, cmd: str):
        """
        Evaluates input.
        This command is owner only for obvious reasons.
        """
        self.log(f"Evaluating {cmd} for {ctx.author}.", "CMMD")
        starttime: float = time.time_ns()
        cmd = cmd.strip("` ")
        if cmd[0:2] == "py":  # Cut out py for ```py``` built in code blocks
            cmd = cmd[2:]
        # add a layer of indentation
        cmd = textwrap.indent(cmd, "    ")
        # wrap in async def body
        body: str = f"async def evaluation():\n{cmd}"
        parsed: ast.AST = ast.parse(body)
        body: str = parsed.body[0].body  # type: ignore
        insert_returns(body)
        env: dict[str, typing.Any] = {
            "bot": ctx.bot,
            "discord": discord,
            "commands": commands,
            "ctx": ctx,
            "me": ctx.author,
            "guild": ctx.guild,
            "channel": ctx.channel,
            "collection_configs": collections,
            "self": self,
            "__import__": __import__,
        }
        env.update(globals())
        exec(compile(parsed, filename="<ast>", mode="exec"), env)

        result = await eval("evaluation()", env)
        endtime = time.time_ns()
        elapsed_ms = int((endtime - starttime) / 10000) / 100
        if elapsed_ms > 100:
            await ctx.send(f"Command took {elapsed_ms}ms to run.")
        self.log(
            f"Evaluation of {cmd} for {ctx.author} gave the following result: {result}.",
            "CMMD",
        )
        if result is not None:
            if len(str(result)) > 1900:
                return await ctx.send(await self.bot.create_bin(result))
        await ctx.send(f"Result: {result}")

    @commands.command()
    @commands.is_owner()
    async def delete(self, ctx: commands.Context, message_id: int):
        """
        Delete a single message by ID
        Used for cleaning up bot mistakes.
        """
        await (await ctx.channel.fetch_message(message_id)).delete()
        await ctx.message.delete(delay=self.deltime)  # delete the command
        self.log(
            f"Deleted message {message_id} in channel {ctx.channel} for user {ctx.author}.",
            "CMMD",
        )

    @commands.command()
    @commands.is_owner()
    async def tofile(self, ctx: commands.Context, *, text=None):
        """Puts your text into a file that it uploads."""
        with open("temp_file.txt", "w+", encoding="utf-8") as f:
            f.write(text)
        await ctx.send("Here's your file.", file=discord.File("temp_file.txt"))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def sudo(
        self,
        ctx,
        channel: typing.Optional[discord.TextChannel],
        user: discord.User,
        *,
        command: str,
    ):
        """Invoke a command as another user, in another channel."""
        message = copy.copy(ctx.message)
        channel = channel or ctx.channel
        message.channel = channel
        message.author = channel.guild.get_member(user.id) or user
        message.content = ctx.prefix + command
        ctx = await self.bot.get_context(message, cls=type(ctx))
        await self.bot.invoke(ctx)

    @commands.command(name="timeit", hidden=True)
    @commands.is_owner()
    async def timeit_(
        self, ctx: commands.Context, setup_="", times: int = 10, cmd: str = "pass"
    ):
        """Time an operation."""
        env = {
            "bot": ctx.bot,
            "discord": discord,
            "commands": commands,
            "ctx": ctx,
            "guild": ctx.guild,
            "channel": ctx.channel,
            "me": ctx.author,
            "self": self,
            "__import__": __import__,
        }
        env.update(globals())
        try:
            result = timeit.timeit(cmd, number=times, setup=setup_, globals=env)
        except Exception as e:
            return await ctx.send(
                f"Error attempting to run the requested timeit: ```py\n{e}\n```"
            )
        await ctx.send(f"{result}")

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def sync(
        self,
        ctx: commands.Context,
        guilds: commands.Greedy[discord.Object],
        spec: typing.Optional[typing.Literal["~", "*", "^"]] = None,
    ) -> None:
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            elif spec in ["^*", "*^"]:
                ctx.bot.tree.clear_commands(guild=None)
                synced = await ctx.bot.tree.sync()
                synced = []
            else:
                synced = await ctx.bot.tree.sync()
            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return
        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1
        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

    @commands.command()
    @commands.is_owner()
    async def shoo(
        self, ctx: commands.Context, user: discord.User, name: str = "Vyryn"
    ):
        """Tell someone to go away firmly but politely."""
        await ctx.message.delete()
        await user.send(
            f"{name} is busy and their temper is short right now. They are already aware of whatever you "
            f"just bothered them about, likely because 20+ people have already informed them of it in the "
            f"same way you did. They have either been troubleshooting it since they were made aware,"
            f" or they can't fix it. In fact, whatever brought this issue to your attention probably "
            f"told you to contact someone else entirely if you were paying attention."
            f"\n\n\n\nSo, in summary, this is {name} telling you politely and kindly to"
            f" please leave them alone. I'm the messenger here because if they'd told you this personally, "
            f"it would be nowhere near as polite or patient. Please don't ping them, and if you're feeling"
            f" nice maybe send them a thank you or tell them to stop and go to sleep."
        )

    @commands.command()
    @commands.is_owner()
    async def shooo(
        self, ctx: commands.Context, user: discord.User, name: str = "Vyryn"
    ):
        """Tell someone to go away firmly and rudely."""
        await ctx.message.delete()
        await ctx.send(
            f"{user.mention}, leave {name} alone! They've already told you what the matter is, "
            f"and asked you to leave them alone, and you didn't listen.",
            delete_after=20,
        )
        for i in range(3):
            await asyncio.sleep(2)
            await user.send(f"{name} told you to leave them alone.")
            await asyncio.sleep(4)
            await user.send("It is a very good idea for you to do so.")
            await asyncio.sleep(10)
            await user.send("Seriously.")
            await asyncio.sleep(10)
        await asyncio.sleep(20)
        await ctx.send(f"{user.mention} ***Seriously, lay off.***", delete_after=20)

    @commands.command()
    @commands.check(fanta())
    async def nocit(self, ctx: commands.Context, user: discord.User):
        await ctx.message.delete()
        await ctx.send(
            f"{user.mention}, you can find out about citizenship here:\n "
            f"https://www.daily-peel.com/post/break-it-down-citizen\n"
            f"The basic idea is that we want to be sure you're a real person and care about the community "
            f"as opposed to use getting free stuff, before we let you participate in some distribution "
            f"events. It takes a minimum of 2 weeks of demonstrated, extended activity in the server. "
            f"And if you beg for the role, it will take longer. So don't keep bringing it up, it will"
            f" come eventually. In the meantime, have fun! Banano is an awesome community, and you can "
            f"enjoy it whether or not you're a citizen."
        )

    @commands.command()
    @commands.is_owner()
    async def fetch(self, ctx: commands.Context, *, url: str):
        """Return the result of fetching the url"""
        resp = await self.session.get(url)
        if resp.status != 200:
            return await ctx.send(f"Got a {resp.status} code response.")
        text = await resp.text()
        print(text)
        if len(text) <= 1900:
            return await ctx.send(text)
        await ctx.send(text[:1900])

    @commands.command()
    @commands.is_owner()
    async def debug(self, ctx: commands.Context, *, mode="DBUG"):
        """Toggles debug mode. Debug mode enables all logging."""
        if not hasattr(self.bot, "debug_mode"):
            self.bot.debug_mode = set()
        if mode in self.bot.debug_mode:
            self.bot.debug_mode.remove(mode)
            return await ctx.send(f"Disabled debug mode for {mode}.")
        else:
            self.bot.debug_mode.add(mode)
            return await ctx.send(f"Enabled debug mode for {mode}.")


async def setup(bot):
    await bot.add_cog(Dev(bot))
