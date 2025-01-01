import discord
from discord.ext import commands

from utils.meta_cog import MetaCog
from utils.util import scope, epoch


class APIs(MetaCog):
    # Commands
    @commands.hybrid_command(
        name="astros", description="Lists all the astronauts currently in space"
    )
    @commands.check(scope())
    async def astros(self, ctx):
        """
        Lists all the astronauts currently in space
        """
        async with self.session.get("http://api.open-notify.org/astros.json") as resp:
            response = await resp.json()
        self.log(f"Queried Astros.json. Response: {response}.")
        embed = discord.Embed(title="", description="", color=ctx.author.color)
        embed.set_author(
            icon_url="http://www.nasa.gov/sites/default/files/thumbnails/image/44911459904_375bc02163_k"
            ".jpg",
            name=f"{response['number']} Astronauts are currently in space:",
        )
        for astro in response["people"]:
            embed.add_field(name=astro["name"], value=f"Aboard: {astro['craft']}")
        await ctx.send(content=None, embed=embed)
        self.log(f"Astros command used by {ctx.author} at {epoch()}.", self.bot.cmd)


async def setup(bot):
    await bot.add_cog(APIs(bot))
