import json
import random
from collections import Counter
from datetime import datetime, timezone

import discord
import parsedatetime as pdt
from aiohttp import ClientSession
from discord.ext import commands

from cogs.wax import nifty
from utils.exceptions import UnableToCompleteRequestedAction
from utils.meta_cog import MetaCog
from utils.settings import (
    UPLAND_QUERY_URL,
    METAFORCE_PROPERTY_LIST,
    CRYPTOMONKEY_PROPERTY_LIST,
)


def time_stamp(item: dict) -> datetime:
    string_time = item["created_at"]
    cal = pdt.Calendar()
    timestamp, _ = cal.parseDT(string_time.replace("T", " "), tzinfo=timezone.utc)
    return timestamp


async def visitors(
    session: ClientSession,
    property_id: int,
    start="2021-01-01",
    end=str(datetime.today),
) -> Counter:
    cal = pdt.Calendar()
    start_stamp, _ = cal.parseDT(start, tzinfo=timezone.utc)
    end_stamp, _ = cal.parseDT(end, tzinfo=timezone.utc)
    response = await session.get(UPLAND_QUERY_URL + str(property_id))
    json_res = await response.json()
    print(json_res)
    if not type(json_res) == list and json_res.get("code", 200) >= 400:
        raise UnableToCompleteRequestedAction(
            f"I received an invalid response from the upland api: {json_res}"
        )

    users = Counter(
        i["username"] for i in json_res if start_stamp <= time_stamp(i) < end_stamp
    )

    # return f'Property {property} had {len(json_res)} visits between {start} and {end}.' \
    #        f' {len(users)} filtered visits.', users
    return users


async def do_a_run(
    session: ClientSession, props: list, start_time="last week", end_time="now"
) -> Counter:
    cumulative_visitors: Counter = Counter()
    for prop in props:
        res = await visitors(session, prop, start=start_time, end=end_time)
        cumulative_visitors.update(res)
    return cumulative_visitors


class UplandData(MetaCog):
    @commands.command()
    @commands.check(nifty())
    async def topvisitors(
        self,
        ctx,
        page: str = "c",
        start: str = "yesterday",
        end: str = "today",
        how_many: int = -1,
    ):
        """Scrapes the wax_chain address pairs from visited properties from the uplandcomics visitors sheet.
        Fetches visit data direct from upland API.
        Specify page as "meta" or "m" or "MetaForce Mine Visits" for MetaForce lands,
        and "cryptomonkey", "c" or "NFT Mine Visits" for cryptomonkey lands. If they are added to the sheet in the
        future, other lands can be specified by their exact page name."""
        if page in ["c", "cryptomonkey", "cryptomonkeys"]:
            props = CRYPTOMONKEY_PROPERTY_LIST
        elif page in ["m", "meta", "metaforce"]:
            props = METAFORCE_PROPERTY_LIST
        else:
            props = []

        values = self.bot.sheet_values(
            self.bot.settings.SURVEY_3_SHEET_CODE, "'Sheet1'!A:D"
        )
        if not values:
            return await ctx.send(
                "Something went wrong, no wax_chain address data found in the spreadsheet."
            )
        upland_wax_mapping = {row[1]: row[3] for row in values}

        def wallet(x):
            return upland_wax_mapping.get(
                x, f"User {x} did not submit their wax_chain address"
            )

        if len(ctx.message.attachments) > 0:
            # If message has a file attached, try using it as data
            file_bytes = await ctx.message.attachments[0].read()
            contents = file_bytes.decode("utf-8").split("\n")
            vd = dict()
            for line in contents:
                username, visits = line.split(",")
                wax_username = wallet(username)
                if "did not submit" in wax_username:
                    continue
                vd[wallet(username)] = int(visits)

        else:
            visited_wallets_tally = await do_a_run(
                self.session, props, start_time=start, end_time=end
            )

            vd = {
                wallet(x): y
                for x, y in visited_wallets_tally.items()
                if "did not submit" not in wallet(x)
            }
        possible_selection = [i for i in vd.items() if len(i) < 13]
        self.bot.visitor_data = vd

        with open("res/tmp/temp_file.json", "w+", encoding="utf-8") as f:
            json.dump(dict(self.bot.visitor_data), f, indent=4)

        await ctx.send(
            f"Found {sum(vd.values())} valid wallet entries between {start} and "
            f"{end}. Here is the full data.",
            file=discord.File("res/tmp/temp_file.json"),
        )
        if how_many != -1:
            selections = random.choices(*zip(*possible_selection), k=how_many)
            with open("res/tmp/temp_file.txt", "w+", encoding="utf-8") as f:
                f.write(",".join(selections))
            await ctx.send(
                f"Since you requested {how_many} addresses, here is a weighted random selection of that "
                f"size:",
                file=discord.File("res/tmp/temp_file.txt"),
            )


async def setup(bot):
    await bot.add_cog(UplandData(bot))
