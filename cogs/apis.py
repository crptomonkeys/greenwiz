import aiohttp
import discord
from discord.ext import commands

from utils.meta_cog import MetaCog
from utils.util import scope, epoch, today


class APIs(MetaCog):

    # Commands
    @commands.command(
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

    @commands.command(
        name="holidays", description="Gets the worldwide holidays for today."
    )
    @commands.check(scope())
    async def holidays(self, ctx):
        """Lists the worldwide holidays for today"""
        async with self.session.get(
            "https://date.nager.at/Api/v2/NextPublicHolidaysWorldwide"
        ) as resp:
            response = await resp.json()
        self.log(
            f"Queried NextPublicHolidaysWorldwide on {today()}. Response: {response}"
        )
        embed = discord.Embed(title="", description="", color=ctx.author.color)
        num_days = 0
        for holiday in response:
            if True:  # holiday['date'] == today():
                self.log(holiday, self.bot.debug)
                num_days += 1
                name = holiday["name"]
                value = f"*{holiday['localName']}*\n Celebrated in {holiday['countryCode']} on \n{holiday['date']}."
                embed.add_field(name=name, value=value)
        embed.set_author(
            icon_url="https://www.nsaglac.org/wp-content/uploads/2018/11/Christmas-Orn8241779-sm.jpg",
            name=f"Worldwide, {num_days} holidays are upcoming:",
        )
        await ctx.send(content=None, embed=embed)
        self.log(f"Holidays command used by {ctx.author} at {epoch()}.", self.bot.cmd)


async def setup(bot):
    await bot.add_cog(APIs(bot))
