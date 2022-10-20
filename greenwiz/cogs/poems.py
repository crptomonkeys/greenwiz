from typing import Union

from discord import Embed, Color
from discord.ext import commands

from utils.meta_cog import MetaCog


async def show_poem(ctx, name, poem_text):
    poem_name, user_id = name.rsplit("_", 1)
    username = await ctx.guild.fetch_member(user_id) or "Unknown User"
    embed = Embed(title=poem_name, description=poem_text, color=Color.blue())
    embed.set_author(icon_url=ctx.author.display_avatar.url, name=username)
    return await ctx.send(embed=embed)


class Poems(MetaCog):
    async def show_random_poem(self, ctx):
        name, val = await self.storage[ctx.guild].get_random_codex(style="poem")
        await show_poem(ctx, name, val)

    @commands.group()
    @commands.guild_only()
    async def poem(self, ctx):
        """View the list of poems.
        poem read [name or id]: Read an poem.
        poem new [name] [text]: Create an poem."""
        if ctx.invoked_subcommand is None:
            await self.show_random_poem(ctx)

    @poem.command(aliases=["get", "read", "view", "check", "see"])
    @commands.guild_only()
    async def access(self, ctx: commands.Context, name_or_id: Union[str, int]):
        if "_" not in name_or_id or len(name_or_id) < 18:
            name_or_id = str(name_or_id) + "_" + str(ctx.author.id)
        note = await self.storage[ctx.guild].get_codex(name_or_id, style="poem")
        await show_poem(ctx, name_or_id, note)

    @poem.command(aliases=["add", "create", "new"])
    @commands.guild_only()
    @commands.has_permissions()
    async def save(self, ctx: commands.Context, name: str, *, text: str):
        name += f"_{ctx.author.id}"
        saved_name = await self.storage[ctx.guild].set_codex(name, text, style="poem")
        await ctx.send(f"Poem `{saved_name}` saved.")

    @poem.command(aliases=["remove"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def delete(self, ctx: commands.Context, name_or_id: Union[str, int]):
        await self.storage[ctx.guild].del_codex(name_or_id, style="poem")
        return await ctx.send(f"Deleted {name_or_id}.")

    @poem.command()
    @commands.guild_only()
    async def list(self, ctx):
        """Display poem names for this guild. You can read one with "poem read name" """
        names = await self.storage[ctx.guild].get_codex_names(style="poem")
        if len(names) < 1:
            return await ctx.send(
                "Sorry, there aren't any poems found for this server yet."
            )
        to_send = "\n".join(names)
        return await ctx.send(to_send)

    @poem.command()
    @commands.guild_only()
    async def random(self, ctx):
        """Return a random poem entry"""
        await self.show_random_poem(ctx)


async def setup(bot):
    await bot.add_cog(Poems(bot))
