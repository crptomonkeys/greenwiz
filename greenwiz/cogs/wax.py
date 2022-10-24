import asyncio
import json
import random
import time
import traceback
from collections import deque, Counter
from typing import Optional, Union

import discord
from aioeos import EosAccount
from discord import TextChannel, Forbidden, HTTPException
from discord.ext import commands, tasks  # type: ignore

from utils.cryptomonkey_util import monkeyprinter, nifty
from utils.exceptions import UnableToCompleteRequestedAction, InvalidInput
from utils.green_api_wrapper import GreenApi, GreenApiException
from utils.logic_parser import parse_addresses
from utils.meta_cog import MetaCog
from utils.settings import (
    WAX_PRIV_KEY,
    WAX_ACC_NAME,
    YOSHI_ACC_NAME,
    YOSHI_PRIV_KEY,
    DEFAULT_WAX_COLLECTION,
    MONKEYMATCH_ACC_NAME,
    MONKEYMATCH_PRIV_KEY,
    CM_GUID,
    CHATLOOT_TIMEOUT_NOTIF_INTERVAL,
)
from utils.util import (
    log,
    scope,
    now_stamp,
    calc_msg_activity,
    get_addrs_from_content_or_file,
)
from wax_chain.collection_config import (
    collections,
    determine_collection,
    adjust_daily_limit,
)
from wax_chain.wax_market_utils import get_assets_from_template, atomic_api
from wax_chain.wax_util import (
    WaxConnection,
    get_template_id,
    send_link_start_to_finish,
    get_card_dict,
)
from wax_chain.link_deletion import delete_old_links
from wax_chain.wax_addresses import (
    is_valid_wax_address,
    async_get_special_wax_address_list,
)


class EmptyClass:
    pass


# Helper function to get cryptomonKey template id from card #


class Wax(MetaCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.recent_drops = deque([0] * 3, maxlen=3)
        self.last_timeout = dict()
        self.bot.nifty_usage_cache = dict()
        self.bot.nifty_usage_cache_age = 0
        self.update_bot_known_assets.start()
        self.bot.log("Started the update_bot_known_assets task (1).", self.bot.debug)
        self.bot.wax_ac = dict()
        self.bot.wax_ac["crptomonkeys"] = EosAccount(
            name=WAX_ACC_NAME, private_key=WAX_PRIV_KEY
        )
        self.bot.wax_ac["lgnd.art"] = EosAccount(
            name=YOSHI_ACC_NAME, private_key=YOSHI_PRIV_KEY
        )
        self.bot.wax_ac["monkeysmatch"] = EosAccount(
            name=MONKEYMATCH_ACC_NAME, private_key=MONKEYMATCH_PRIV_KEY
        )
        if not hasattr(self.bot, "green_api"):
            self.bot.green_api = GreenApi(self.session)
        self.wax_con = WaxConnection(self.bot)

    def cog_unload(self):
        self.update_bot_known_assets.cancel()
        self.bot.log("Ended the update_bot_known_assets task.", self.bot.debug)

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        await get_card_dict(self.session)

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
        failed: Counter = Counter()
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
            to_send += f"One address couldn't be blacklisted because {st}"
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
    async def filter(self, ctx: commands.Context, *, provided: str = None):
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
        description="Transfer wax_chain funds from bot account to selected account"
    )
    @commands.check(monkeyprinter())
    @commands.check(scope())
    async def send_wax(self, ctx: commands.Context, amount: int, destination: str):
        result = await self.wax_con.transfer_funds(
            destination, amount, sender=ctx.author.name
        )
        if result == 0:
            await ctx.send(f"Sent {amount} WAX to {destination}.")
        else:
            await ctx.send(result)

    @commands.command(
        description="Transfer specified asset ids from the tipbot account to selected account"
    )
    @commands.check(monkeyprinter())
    @commands.check(scope())
    async def send_nft(self, ctx: commands.Context, destination: str, *, asset_id: int):
        asset_ids = [asset_id]
        result = await self.wax_con.transfer_assets(
            destination, asset_ids, sender=ctx.author.name
        )
        if result == 0:
            await ctx.send(f"Sent {asset_ids} to {destination}.")
        else:
            await ctx.send(result)

    @commands.command(
        description="Mint the specified template id to selected account",
        aliases=["mintnft"],
    )
    @commands.check(monkeyprinter())
    @commands.check(scope())
    async def mint_nft(
        self,
        ctx,
        destination: str,
        template_id: int,
        num=1,
        test: Optional[bool] = False,
        schema: str = None,
    ):
        if template_id < 1000 and not schema:
            template_id = await get_template_id(template_id, self.session)
        response = await ctx.send(f"Minting {num}x {template_id}...")
        ready = 0
        max_group = 25
        groups = num // max_group
        if test:
            col = "testcol12345"
            schema = "testcard"
        else:
            col = DEFAULT_WAX_COLLECTION
            schema = schema or DEFAULT_WAX_COLLECTION
        for i in range(groups):
            await self.wax_con.mint_asset(
                destination,
                template_id,
                amount=max_group,
                collection=col,
                schema=schema,
            )
            ready += max_group
            await response.edit(
                content=f"Successfully minted {ready}/{num}x of template id #{template_id} to"
                f" account {destination}."
            )
        remainder = num % max_group
        if remainder <= 0:
            return
        await self.wax_con.mint_asset(
            destination, template_id, amount=remainder, collection=col, schema=schema
        )
        ready += remainder
        await response.edit(
            content=f"Successfully minted {ready}/{num}x of template id #{template_id}."
        )

    @commands.command(
        description="Create a claim link for the specified asset id from the tipbot account"
    )
    @commands.check(monkeyprinter())
    @commands.check(scope())
    async def claimlink_id(self, ctx: commands.Context, asset_id: int):
        success, result = await self.wax_con.create_claimlink([asset_id])
        await ctx.send(result)

    @commands.command(description="Cancel the specified claimlink.")
    @commands.check(monkeyprinter())
    @commands.check(scope())
    async def cancel_link(self, ctx: commands.Context, link_id: int):
        result, tx_id = await self.wax_con.cancel_claimlink(link_id)
        await ctx.send(f"Deleted claimlink {link_id}. Transaction id: {tx_id}.")

    @commands.command(description="Cancel old claimlinks.")
    @commands.check(monkeyprinter())
    @commands.check(scope())
    async def cancel_old_links(self, ctx: commands.Context, *, links):
        try:
            links_dict = json.loads(links)
        except json.JSONDecodeError:
            raise InvalidInput("Invalid list of claimlink ints.")
        await delete_old_links(ctx, self.wax_con, links_dict)
        await ctx.send("Delete complete.")

    @commands.command(
        description="DMs someone a claim link for one of the specified card # from the tipbot account"
    )
    @commands.check(monkeyprinter())
    @commands.check(scope())
    async def claimlink(
        self, ctx: commands.Context, member: discord.Member, card: int = 0, *, memo=None
    ):
        if card != 0 and card < 1000:
            # convert card # to template id
            template_id = await get_template_id(card, self.session)
        else:
            template_id = card
        # basic verifications
        if (
            member is None
            or not hasattr(member, "roles")
            or member.roles is None
            or member.roles is []
        ):
            return await ctx.send(
                "I could not find that member. This command requires a discord mention or user id."
            )
        if template_id == -1:
            return await ctx.send("That card doesn't exist or hasn't been minted yet.")
        asset_ids = await get_assets_from_template(
            template_id, WAX_ACC_NAME, self.session
        )
        if len(asset_ids) < 1:
            return await ctx.send(
                f"I don't have any of that card to send. To reload, transfer some to `{WAX_ACC_NAME}`."
            )
        # good to go, choose an asset and make a claim link
        asset_id = random.choice(asset_ids)
        success, link = await self.wax_con.create_claimlink([asset_id], memo=memo)
        # If an error occurred, report it
        if success != 0:
            return await ctx.send(link)

        to_send = "Congratulations! You have won a random cryptomonKey "
        if memo:
            to_send += f"for {memo} "
        to_send += (
            f"by request of {ctx.author}. You can claim it at the following link (just login "
            f"with your wax_chain wallet, might require allowing popups):\n{link}"
            f"\nWARNING: Any one you share this link with can claim the NFT. "
            f"Do not share with anyone!\nMore information about cryptomonKeys at "
            f"https://cryptomonkeys.cc/"
        )
        claim_id = link.split("?")[0].split("/")[-1]

        try:
            await member.send(to_send)
            await ctx.send(
                f"I have successfully sent {member} a cryptomonKey claim link."
            )
            to_announce = (
                f"<:vase:769372650387537951> **{memo} Giveaway**\n{member} has been "
                f"sent a random cryptoMonkeys NFT by {ctx.author}, claim link #{claim_id}. Congrats!"
            )
            channel = self.bot.get_guild(CM_GUID).get_channel(763776455338360883)
            await channel.send(to_announce)
        except (discord.Forbidden, discord.HTTPException):
            await ctx.author.send(
                f"I couldn't send {member} their NFT claim link, so here it is: \n{link}"
            )
            await ctx.send(
                "Something went wrong sending that card. Most likely this user has restricted who "
                "can send them DMs in their privacy settings. I've DM'd you the link instead."
            )

    @commands.command(description="Generate several claimlinks")
    @commands.check(monkeyprinter())
    async def claimlinks(
        self, ctx: commands.Context, amount: int = 1, card: int = 0, *, memo=None
    ):
        if card != 0 and card < 1000:
            # convert card # to template id
            template_id = await get_template_id(card, self.session)
        else:
            template_id = card
        # basic verifications
        if template_id == -1:
            return await ctx.send("That card doesn't exist or hasn't been minted yet.")
        asset_ids = await get_assets_from_template(
            template_id, WAX_ACC_NAME, self.session
        )
        if len(asset_ids) < amount:
            return await ctx.send(
                f"I don't have that many of that card to send, I only have {len(asset_ids)}."
                f" To reload, transfer some to `{WAX_ACC_NAME}`."
            )
        to_send = []
        for i in range(amount):
            asset_id = random.choice(asset_ids)
            asset_ids.remove(asset_id)
            success, link = await self.wax_con.create_claimlink(
                [asset_id], memo=memo, wait_for_confirmation=False
            )
            to_send += [link]
            if len(to_send) >= 10:
                await ctx.send("\n".join([j for j in to_send]))
                to_send = []
        await ctx.send("\n".join([j for j in to_send]))

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

    @commands.command(
        aliases=["monkeydrop", "monKeydrop", "monkey42"],
        description="Sends the specified discord user/id a claim link for a random cryptomonKey.",
    )
    @commands.guild_only()
    async def drop(
        self,
        ctx,
        member: Union[discord.Member, str],
        num: Optional[int] = 1,
        *,
        reason: str = "No reason",
    ):
        """
        Sends the target member a random cryptomonkey claim link from the cryptomonkeys account.
        Target may be a discord member (will DM a claimlink) or a wax address (will directly transfer assets).
        If there aren't any stored, tells you so. You can specify a reason after the name. Drop admins such
        as monKeyprinters may optionally specify a number of cards to send, before the reason but after the
        name. Defaults to 1. (Others can also specify a number, but it will always be overwritten by 1)
        """
        if num is None:
            num = 1
        if not 1 <= num <= 10:
            raise InvalidInput("Num must be between 1 and 10.")

        if type(member) == discord.Member:
            log(
                f"Sending {num} random cryptomonKeys to discord user {member} as a DMed claimlink for reason {reason}",
                "DBUG",
            )
            return await send_link_start_to_finish(
                self.wax_con, self.bot, ctx.message, member, ctx.author, reason, num
            )
        member = str(member)
        if len(member) > 12:
            raise InvalidInput(
                "Provide either a discord member, a discord user id, or a valid wax address."
            )

        raise InvalidInput(
            "You can't yet drop to addresses, and didn't enter a valid user mention."
        )  # TODO

        if (
            ".wam" in member
            or len(member) == 12
            or member in self.bot.special_addr_list
            or ("." in member and member.split(".")[1] in self.bot.special_addr_list)
        ):
            log(
                f"Sending {num} random cryptomonKeys by direct transfer to wax "
                f"wallet address {member} for reason {reason}."
            )
            # TODO

        raise InvalidInput(
            f"{member} isn't a valid wax address, though it is of the correct length."
        )

    @drop.error
    async def drop_error(self, ctx: commands.Context, error):
        lines = traceback.format_exception(type(error), error, error.__traceback__)
        traceback_text = "```py\n" + "".join(lines) + "\n```"
        if hasattr(error, "args") and len(error.args) > 0:
            self.log(
                f"{ctx.author} triggered {type(error)}::{error} in command {ctx.command}: {error.args[0]} "
                f"({error.args})\n\n{traceback_text}"
            )
        else:
            self.log(
                f"{ctx.author} triggered {type(error)}::{error} in command {ctx.command}"
                f"\n\n{traceback_text}"
            )

        try:
            await ctx.message.clear_reactions()
            await ctx.message.add_reaction("❌")
        except HTTPException:
            pass

        try:
            await ctx.author.send(error)
        except Forbidden:
            await ctx.send(error)

    @commands.command(
        aliases=["monkeyloot"], description="Drop an NFT to the nth respondent"
    )
    @commands.guild_only()
    async def chatloot(
        self,
        ctx,
        number: Optional[int] = 10,
        channel: TextChannel = None,
        *,
        reason: str = None,
    ):
        """Drop an NFT to approximately the nth respondent in this channel.
        Slightly randomized to avoid abuse."""

        # Determine which collection is being dropped to
        authd, cinfo = determine_collection(ctx.guild, ctx.author, self.bot)
        collection = cinfo.collection
        # Determine whether the user can send an unlimited number of drops per day
        if authd == 0:
            raise InvalidInput(f"You can't drop {collection}s here.")
        if number is None:
            number = 10
        counter, resp = 0, None
        await ctx.message.delete()
        if reason is None:
            reason = (
                f"Monkeyloot from {ctx.author} for being the {number}th respondent!"
            )
        if channel is None:
            channel = ctx.channel

        # Randomize the winner slightly
        number = max(random.randrange(number - 3, number + 3), 2)

        def check_ch(given_channel, giver):
            def in_check(message) -> bool:
                log(
                    f"Checking appropriateness of message {message.content} for loot in {given_channel} by {giver}.",
                    "DBUG",
                )
                if (
                    message.channel != given_channel
                    or message.author.bot
                    or message.author == giver
                ):
                    return False
                return calc_msg_activity(self.bot, message.author, message.content) > 0

            return in_check

        while True:
            try:
                resp = await self.bot.wait_for(
                    "message",
                    check=check_ch(channel, ctx.author),
                    timeout=60 * 15,
                )
            except asyncio.TimeoutError:
                # Send failure message, but only at most once per five minutes per channel
                if not hasattr(self, "last_timeout"):
                    self.last_timeout = dict()
                if (
                    time.time() - self.last_timeout.get(channel.id, 0)
                    < CHATLOOT_TIMEOUT_NOTIF_INTERVAL
                ):
                    return
                self.last_timeout[channel.id] = time.time()
                return await channel.send(
                    "A loot has been cancelled, either because of not enough chatting or too much spam.",
                    delete_after=60 * 5,
                )
            counter += 1
            self.log(
                f"Chatloot - number = {number} counter = {counter}, resp = "
                f"[{resp.content}/{resp.id} by {resp.author.name}/{resp.author.id}],"
                f" self.recent_drops = {self.recent_drops}",
                "CHLO",
            )
            if counter >= number and resp.author.id not in set(self.recent_drops):
                break
        assert resp is not None
        # Prevents the same person from receiving two drops in a row
        self.recent_drops.appendleft(resp.author.id)
        log("attempting to send a loot", "DBUG")
        reward_id = await send_link_start_to_finish(
            self.wax_con, self.bot, resp, resp.author, ctx.author, reason
        )
        if reward_id:
            if resp.channel != ctx.channel:
                # Send log in invoking channel
                await ctx.send(f"Successfully sent loot to {resp.author} in {channel}.")
            # Send response in recieving channel
            return await resp.channel.send(f"Enjoy your loot, {resp.author}!")
        raise AssertionError(
            f"Invalid reward_id {reward_id} reached on attempted loot distribution"
            f" to {resp.author} by {ctx.author} for {reason}."
        )

    @chatloot.error
    async def chatloot_error(self, ctx: commands.Context, error):
        if hasattr(error, "args"):
            self.log(
                f"{ctx.author} triggered {type(error)}::{error} in command {ctx.command}: {error.args[0]} "
                f"({error.args})"
            )
        else:
            self.log(
                f"{ctx.author} triggered {type(error)}::{error} in command {ctx.command}"
            )

        try:
            await ctx.message.clear_reactions()
            await ctx.message.add_reaction("❌")
        except (HTTPException, NameError):
            pass

        try:
            await ctx.author.send(error)
        except Forbidden:
            await ctx.send(error)

    @tasks.loop(seconds=60)
    async def update_bot_known_assets(self):
        if self.session.closed:
            return
        for key, value in collections.items():
            asset_ids = set()
            page = 1
            while True:
                async with self.session.get(
                    atomic_api
                    + f'assets?owner={value["drop_ac"]}&limit=1000&collection_whitelist={key}&page={page}'
                ) as resp:
                    try:
                        response = (await resp.json())["data"]
                    except KeyError:
                        self.bot.log(
                            f"Unable to update bot known assets for {key} at {now_stamp()}",
                            "WARN",
                        )
                        return
                asset_ids.update(int(item["asset_id"]) for item in response)
                if len(response) < 1000:
                    break
                page += 1
            # https://wax.api.aa.atomichub.io/atomicmarket/v1/stats/accounts/b52qw.wam?collection_whitelist=crptomonkeys&symbol=WAX
            self.bot.log(
                f"{now_stamp()} Updated cached card ids for {key}: {len(asset_ids)} cards found."
            )
            if not hasattr(self.bot, "cached_card_ids"):
                self.bot.cached_card_ids = dict()

            self.bot.cached_card_ids[key] = list(asset_ids)
            random.shuffle(self.bot.cached_card_ids[key])
        # By shuffling here, can simulate on the spot random shuffling without needing to use O(n) deletion time.

    @update_bot_known_assets.before_loop
    async def before_update_bot_known_assets(self):
        await self.bot.wait_until_ready()

    @commands.command(description="Fetch the top monkeysmatch completers")
    @commands.check(monkeyprinter())
    async def monkeysmatch(self, ctx: commands.Context, completions: Optional[int] = 1):
        """Fetches all wax addresses who have completed at least n games of monkeysmatch. Default 1."""
        res = await self.wax_con.monkeysmatch_top(completions)

        with open("res/tmp/monkeysmatch_results.json", "w+", encoding="utf-8") as f:
            json.dump(res, f, indent=4)

        await ctx.send(
            f"Found {len(res)} wallets that have completed monkeysmatch at least {completions} times."
            f" Here is the full data.",
            file=discord.File("res/tmp/monkeysmatch_results.json"),
        )

    @commands.command(
        description="Adjust the daily drop limit for niftys until the next bot restart"
    )
    @commands.check(monkeyprinter())
    async def adjustlimit(self, ctx: commands.Context, limit: int = 20):
        """Temporarily adjust the daily drop limit. Value must be an integer between 0 and 1000."""
        if not (0 <= limit <= 1000):
            raise UnableToCompleteRequestedAction(
                "Daily drop limit must be between 0 and 1000."
            )
        adjust_daily_limit("crptomonkeys", limit)
        return await ctx.send(f"Daily drop limit temporarily updated to {limit}.")


async def setup(bot):
    await bot.add_cog(Wax(bot))
