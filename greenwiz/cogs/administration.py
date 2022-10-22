from typing import Union

import aioredis
import discord
from discord.ext import commands

from utils.meta_cog import MetaCog


class Administration(MetaCog):
    @commands.group()
    @commands.guild_only()
    async def codex(self, ctx):
        """View the list of articles.
        codex read [name or id]: Read an article.
        codex new [name] [text]: Create an article. Requires manage guild perms."""
        if ctx.invoked_subcommand is None:
            return await ctx.send_help("codex")

    @codex.command(aliases=["get", "read", "view", "check", "see"])
    @commands.guild_only()
    async def article(self, ctx: commands.Context, name_or_id: Union[str, int]):
        note = await self.storage[ctx.guild].get_codex(name_or_id)
        await ctx.send(note)

    @codex.command(aliases=["add", "create", "new"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def save(self, ctx: commands.Context, name: str, *, text: str):
        saved_name = await self.storage[ctx.guild].set_codex(name, text)
        await ctx.send(f"Codex entry `{saved_name}` saved.")

    @codex.command(aliases=["remove"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def delete(self, ctx: commands.Context, name_or_id: Union[str, int]):
        await self.storage[ctx.guild].del_codex(name_or_id)
        return await ctx.send(f"Deleted {name_or_id}.")

    @codex.command()
    @commands.guild_only()
    async def list(self, ctx):
        """Display codex names for this guild. You can read one with "codex read name" """
        names = await self.storage[ctx.guild].get_codex_names()
        to_send = "\n".join(names)
        return await ctx.send(to_send)

    @codex.command()
    @commands.guild_only()
    async def random(self, ctx):
        """Return a random codex entry"""
        random = await self.storage[ctx.guild].get_random_codex()
        return await ctx.send(f"I found {random[0]}:\n{random[1]}")

    @commands.group()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def settings(self, ctx):
        """View or update server settings."""
        if ctx.invoked_subcommand is None:
            settings = await self.bot.storage[ctx.guild].get_settings()
            return await ctx.send(settings)

    @settings.command()
    async def factory(self, ctx: commands.Context, reset: str, confirm: str):
        """Settings factory reset confirm will reset all server-specific settings to their default values."""
        if reset != "reset" or confirm != "confirm":
            prefix = (await self.bot.get_prefix(ctx.message))[-1]
            return await ctx.send(
                f"You can type `{prefix}settings factory reset "
                f"confirm` to reset all server-specific settings to their default values."
                f" Don't do so unless you're sure!"
            )
        await ctx.send(
            "Okay, resetting server settings to their default values. Here are your current values "
            "just in case:"
        )
        try:
            settings = await self.bot.storage[ctx.guild].get_settings()
            await ctx.send(settings)
        except aioredis.ReadOnlyError:
            await ctx.send(
                "I couldn't display the settings, but I'm resetting them anyways."
            )
        for setting, value in self.bot.settings.SERVER_DEFAULT_VALUES.items():
            await self.bot.storage[ctx.guild].set_setting(setting, value)

    @settings.command(name="set")
    async def settings_set(
        self,
        ctx: commands.Context,
        setting: str,
        *,
        value: Union[discord.TextChannel, discord.User, str, int],
    ):
        """Sets the specified setting to the specified value."""
        _value: str
        if isinstance(value, discord.TextChannel) or isinstance(value, discord.User):
            _value = str(value.id)
        else:
            _value = str(value)
        result: str = await self.bot.storage[ctx.guild].set_setting(setting, _value)
        return await ctx.send(f"Saved `{setting}` to `{result}`.")


async def setup(bot):
    await bot.add_cog(Administration(bot))
