from datetime import datetime
from typing import Any, Union

import discord
import aiohttp
from discord.ext import commands

from utils.meta_cog import MetaCog
from utils.util import utcnow, log
from utils.settings import ADVENT_OF_CODE_COOKIE

LEADERBOARD = "https://adventofcode.com/2022/leaderboard/private/view/193648.json"
PUBLIC_LEADERBOARD = "https://adventofcode.com/2022/leaderboard/private/view/193648"


async def get_lb(session: aiohttp.ClientSession) -> dict[str, Any]:
    """Fetches the AoC leaderboard and parses it."""
    async with session.get(
        LEADERBOARD, headers={"cookie": ADVENT_OF_CODE_COOKIE}
    ) as response:
        raw: dict[str, Any] = await response.json()
        return raw


def parse_lb(raw: dict[str, Any]) -> list[dict[str, dict[str, Union[str, int]]]]:
    """Parses the raw api response into a list of users with just relevant content."""
    parsed: list[dict[str, Any]] = []
    members = raw["members"]
    for key, member in members.items():
        name = member["name"]
        score = member["local_score"]
        stars = member["stars"]
        if name is None:
            name = f"Anon #{member['id']}"
        if member["local_score"] > 0:
            parsed.append({"name": name, "stars": stars, "score": score})
    res = sorted(
        parsed, key=lambda x: x["score"], reverse=True  # type:ignore[no-any-return]
    )
    return res


def prep_embed_content(members: list[dict[str, Any]]) -> str:
    """Formats the leaderboard list for embed content."""
    log(f"{members=}", "DBUG")
    resp = "```"
    i = 0
    for member in members:
        i += 1
        log(f"{i=}, {member['name']=}, {member['stars']=}, {member['score']=}", "DBUG")
        resp += f"{i:<2}) {member['name'][:15]: <15} ({member['stars']:>2} stars) - {member['score']:>4} points\n"
        if len(resp) > 900:
            resp += "```"
            return resp
    if len(resp) >= 996:
        resp = resp[:996]
    resp += "```"
    return resp


class AdventOfCode(MetaCog):
    def __init__(self, bot):
        super().__init__(bot)
        if not hasattr(self.bot, "aoc_cache"):
            self.bot.aoc_cache = dict()
        if not hasattr(self.bot, "aoc_cache_time"):
            self.bot.aoc_cache_time = None

    @commands.hybrid_command()
    async def aoc(self, ctx):
        """Display the Advent of Code leaderboard"""
        if (
            not self.bot.aoc_cache_time
            or (datetime.now() - self.bot.aoc_cache_time).total_seconds() > 15 * 60
        ):
            self.bot.aoc_cache = await get_lb(self.bot.session)
            self.bot.aoc_cache_time = datetime.now()
        top: list[dict[str, Any]] = parse_lb(self.bot.aoc_cache)
        parsed_top_10: str = prep_embed_content(top)

        embed = discord.Embed(timestamp=utcnow())
        embed.title = "Advent of Code"
        embed.url = PUBLIC_LEADERBOARD
        embed.colour = discord.Colour.green()
        embed.add_field(
            name="Top 10",
            value=parsed_top_10,
        )
        await ctx.reply(embed=embed)


async def setup(bot):
    await bot.add_cog(AdventOfCode(bot))
