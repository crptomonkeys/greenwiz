import asyncio
import json
from collections import Counter
from typing import Optional

import discord
from discord.ext import commands  # type: ignore

from utils.cryptomonkey_util import nifty
from utils.exceptions import UnableToCompleteRequestedAction
from utils.green_api_wrapper import GreenApi, GreenApiException
from utils.logic_parser import parse_addresses
from utils.meta_cog import MetaCog
from utils.util import (
    scope,
    get_addrs_from_content_or_file,
)
from wax_chain.wax_addresses import (
    is_valid_wax_address,
    async_get_special_wax_address_list,
)


class Blacklisting(MetaCog):
    def __init__(self, bot):
        super().__init__(bot)
        if not hasattr(self.bot, "green_api"):
            self.bot.green_api = GreenApi(self.session)

    # Commands
    @commands.command(
        description="Blacklists an address from future filtered giveaways.", hidden=True
    )
    @commands.check(nifty())
    async def blacklist(self, ctx: commands.Context, *, provided: Optional[str]):
        """
        Adds an address to the blacklist. They will be excluded from future filtered giveaways.
        Alternatively, you can provide a file that is either a csv or a .txt file with one
        address per line with no commas. All valid addresses in the file will be blacklisted.
        """
        return_inline, i_list = await get_addrs_from_content_or_file(
            ctx.message, provided
        )
        # For just one address, short way
        if len(i_list) == 1:
            resp = await self.bot.green_api.blacklist_add(i_list[0])
            if not resp.get("success", False):
                raise UnableToCompleteRequestedAction(
                    resp.get("exception", "Add to blacklist failed, try again later.")
                )
            return await ctx.send(
                f"`{i_list[0]}` has been blacklisted from future filtered giveaways."
            )
        # Mass-blacklist
        specials = await async_get_special_wax_address_list(self.session)
        to_blacklist, unable = [], []
        for addr in list(set(i_list)):
            if is_valid_wax_address(addr, valid_specials=specials):
                to_blacklist.append(addr)
            else:
                unable.append(addr)
        to_send = ""
        if len(unable) > 0:
            to_send += f"Skipping the following invalid addresses: {unable}."
        to_send += f" Attempting to blacklist {len(to_blacklist)} addresses, stand by."
        await ctx.send(to_send)
        tasks = [
            asyncio.create_task(self.bot.green_api.blacklist_add(address))
            for address in to_blacklist
        ]
        results = await asyncio.gather(*tasks)
        failed: Counter[str] = Counter()
        for result in results:
            if not result.get("success"):
                failed[result["exception"]] += 1
        if len(to_blacklist) - sum(failed.values()) > 0:
            to_send = f"Successfully blacklisted {len(to_blacklist)-sum(failed.values())} addresses."
        else:
            to_send = "No addresses were blacklisted."
        if sum(failed.values()) > 1:
            to_send += " Failure reasons are:"
            for key, value in failed.items():
                to_send += f"\n{value}x {key}"
        elif sum(failed.values()) == 1:
            st = str(failed.most_common(1)).split("'")[1]
            to_send += f" One address couldn't be blacklisted because {st}"
        await ctx.send(to_send)

    @commands.command(
        description="Remove an address from future filtered giveaways.", hidden=True
    )
    @commands.check(nifty())
    @commands.check(scope())
    async def unblacklist(self, ctx: commands.Context, address: str):
        """
        Removes an address from the blacklist.
        """
        resp = await self.bot.green_api.blacklist_remove(address)
        if not resp.get("success", False):
            raise UnableToCompleteRequestedAction(
                resp.get("exception", "Remove from blacklist failed, try again later.")
            )
        await ctx.send(f"`{address}` has been removed from the blacklist.")

    @commands.command(description="See the current wax address blacklist.", hidden=True)
    @commands.check(nifty())
    async def get_blacklist(self, ctx: commands.Context, csv: str = ""):
        """
        Returns the blacklist as a .txt file.
        """
        blacklist = await self.bot.green_api.get_blacklist()
        self.log(f"Blacklist is: {blacklist}", "DBUG")

        with open("res/tmp/blacklist.txt", "w+", encoding="utf-8") as f:
            if csv == "":
                f.write("\n".join(blacklist))
            else:
                f.write(",".join(blacklist))
        await ctx.send(
            f"Here's the {len(blacklist)} long list you requested.",
            file=discord.File("res/tmp/blacklist.txt"),
        )

    @commands.command(
        description="Remove all blacklisted addresses from the provided txt file"
    )
    @commands.check(nifty())
    @commands.check(scope())
    async def filter(self, ctx: commands.Context, *, provided: str = ""):
        """
        Remove all blacklisted addresses from the provided txt file or in-line list.
        File should be a .csv or a .txt with one address per line.
        If you send addresses in the command, they should be separated by single spaces with no commas.
        If you request addresses inline, it will return addresses inline. If you request addresses with a file,
        it will return a file.
        """
        return_inline, i_list = await get_addrs_from_content_or_file(
            ctx.message, provided
        )

        print(i_list)
        blacklist = set(await self.bot.green_api.get_blacklist())
        special_addresses = set(await async_get_special_wax_address_list(self.session))
        result_list = [
            i
            for i in i_list
            if i not in blacklist
            and is_valid_wax_address(i, valid_specials=special_addresses)
        ]
        print(result_list)
        to_send = "\n".join(result_list)
        if return_inline:
            return await ctx.send(
                f"Here's your {len(result_list)} results:\n {to_send}"
            )
        file = ctx.message.attachments[0]
        with open(f"res/tmp/filtered_{file.filename}", "w+", encoding="utf-8") as f:
            f.write(to_send)
        num_removed = len(i_list) - len(result_list)
        await ctx.send(
            f"{num_removed} results removed. Here's your {len(result_list)} results:",
            file=discord.File(f"res/tmp/filtered_{file.filename}"),
        )

    @commands.command(
        description="Gets all wax addresses that fit specified ownership criteria."
    )
    @commands.check(nifty())
    @commands.check(scope())
    async def get_addresses(self, ctx: commands.Context, *, text=None):
        """
        Creates a text file of addresses, one per line, that meet specified conditions. You can specify card IDs
         with and and or between them. You **must** also use brackets for ordering. If you do not use
         brackets whenever order could be ambiguous, the returned result will not be valid.
         You can optionally add a True flag before the logic in order to include results from the blacklist.
         Addresses in the blacklist are *excluded* by default.
        """
        blacklist = await self.bot.green_api.get_blacklist()
        resultant_list = await parse_addresses(
            self.session, text=text, blacklist=blacklist
        )
        # Prepare final results for sending
        to_send = "\n".join(resultant_list)
        # If short, can give result inline
        if len(resultant_list) < 10:
            return await ctx.send(f"I found the following few addresses:\n{to_send}")
        # If long, send result in a file
        with open("res/tmp/requested_addresses.txt", "w+", encoding="utf-8") as f:
            f.write(to_send)
        await ctx.send(
            f"I found {len(resultant_list)} results, so I put them in a file:",
            file=discord.File("res/tmp/requested_addresses.txt"),
        )

    @commands.command(
        description="Quickly fetch miners for the cycle specified",
        aliases=["topminers"],
    )
    @commands.check(nifty())
    async def topminers_x(self, ctx: commands.Context, cycle: int, top: int = 10):
        """Quickly fetch miners for the cycle specified from Green's api."""
        msg = await ctx.send(
            f"Fetching data for cycle {cycle}, this shouldn't take longer than a minute..."
        )
        try:
            self.bot.got_miner_data = await self.bot.green_api.all_miners_for_cycle(
                cycle
            )
        except GreenApiException as e:
            return await msg.edit(content=e)

        to_send = f"Top miners for cycle {cycle}:\n"
        i = 0
        for item in self.bot.got_miner_data:
            self.bot.log(
                f'Miner {item["user"]} mined {item["tlm"]:.4f} TLM over {item["mines"]} mines.',
                "DBUG",
            )
            i += 1
            if i <= top:
                to_send += f'{i}) {item["user"]} - {item["tlm"]:.4f} TLM over {item["mines"]}x mines\n'
        total = sum(item["tlm"] for item in self.bot.got_miner_data)

        with open(f"res/tmp/minersCycle{cycle}.json", "w+") as f:
            json.dump(self.bot.got_miner_data, f, indent=4)
        with open(f"res/tmp/minersCycle{cycle}.txt", "w+", encoding="utf-8") as f:
            f.write(",".join(item["user"] for item in self.bot.got_miner_data))
        await ctx.send(
            f"Total TLM mined for cycle {cycle} is {total:.4f} by {len(self.bot.got_miner_data)} "
            f"different miners.\n"
            f"Here's the full data.",
            file=discord.File(f"res/tmp/minersCycle{cycle}.json"),
        )
        await msg.edit(content=to_send[:1990])
        await ctx.send(
            "Here's a csv of all those miners.",
            file=discord.File(f"res/tmp/minersCycle{cycle}.txt"),
        )


async def setup(bot):
    await bot.add_cog(Blacklisting(bot))
