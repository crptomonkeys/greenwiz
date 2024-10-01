import random
from datetime import datetime
from time import time
from typing import Any

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import BucketType

from utils.meta_cog import MetaCog
import utils.settings as settings
from utils.exceptions import InvalidInput
from utils.util import (
    log,
    load_json_var,
    write_json_var,
    now_stamp,
    has_cm_role,
    is_citizen,
)
from wax_chain.wax_util import announce_and_send_link

drop_banano_endpoint = "/accounts/api/v1/drop_ban_discord/"
connect_url = "https://connect.cryptomonkeys.cc"
success_emoji = "<:candy_emoji:761873733366448148>"
cache_time = 600  # seconds before querying api again to refresh user dict

cached_active_users: dict[Any, Any] = {}
cached_active_users_age: float = 0


class ConnectFailedToSendBan(ValueError):
    """monKeyconnect returned an unsuccessful response to my request to send bannao."""


async def send_ban_to_user(
    session: aiohttp.ClientSession, user: discord.User, amount=1.0
) -> bool:
    """Sends the specified amount of banano to the specified user.
    Takes a ClientSession object, and a discord user object.
    Returns True on success, raises ConnectFailedToSendBan otherwise."""
    params = (
        f"uid={user.id}&code={settings.BANANO_DISTRIBUTION_AUTH_CODE}&amount={amount}"
    )
    response = await session.get(f"{connect_url}{drop_banano_endpoint}?{params}")

    json_resp: dict[str, Any] = {}
    try:
        json_resp = await response.json()
        log(json_resp)
    except aiohttp.ClientConnectionError:
        log("Unable to connect to api to fetch usernames.", "WARN")
    except aiohttp.ContentTypeError:
        log("ContentTypeError trying to fetch usernames.", "WARN")

    success = json_resp.get("success")
    if not success:
        if not json_resp.get("wax"):
            log(
                "Unable to send {user} bannao because they aren't registered for monKeyconnect."
            )
        else:
            log(
                "Unable to send {user} banano for some reason other than not being registered."
                "Perhaps the account is empty?"
            )
        raise ConnectFailedToSendBan()
    return True


def today():
    return str(datetime.today().date())


def check_user_opened_today_gift(uid: int):
    global cached_active_users
    global cached_active_users_age
    if (
        time() - cached_active_users_age > cache_time
    ):  # If cache time hasn't yet passed, use cached dict
        cached_active_users = load_json_var("trickortreat_records")
        cached_active_users_age = time()
    try:
        return str(uid) in cached_active_users[today()]
    except KeyError:
        cached_active_users[today()] = []
        return False


def record_user_opened_today_gift(uid: int, gift):
    try:
        cached_active_users[today()][str(uid)] = gift
    except TypeError:
        cached_active_users[today()] = {}
        cached_active_users[today()][str(uid)] = gift
    # log(cached_active_users, 'DBUG')
    write_json_var("trickortreat_records", cached_active_users)


async def err(ctx, msg: str):
    await ctx.message.add_reaction("❌")
    try:
        await ctx.author.send(msg)
    except (discord.Forbidden, discord.HTTPException):
        await ctx.send(
            f"{ctx.author} blocked me or has closed DMs, so I'll say this here:\n{msg}",
            delete_after=60,
        )


async def attempt_to_send_daily_reward_ban_or_send_cm_instead(
    session: aiohttp.ClientSession, user: discord.User, bot, amount: float = 1
) -> str:
    """Attempts to send banano. Failing that if the user hasn't registered, sends a cryptomonkey."""
    try:
        await send_daily_reward_ban(bot.session, user, bot, float(amount))
        msg = f"You got {amount} ban for Halloween, lucky you!"
        if amount > 200:
            msg = f"You got {amount} ban for Halloween, jackpot!"
    except ConnectFailedToSendBan:
        await send_daily_reward_cryptomonkey(bot, user)  # type: ignore[arg-type]
        msg = """Looks like you haven't yet registered for https://connect.cryptomonkeys.cc/
        or haven't yet added your ban address to it. You would have gotten banano, but
        I couldn't send it so instead you get a cryptomonKeys NFT for halloween, pretty cool."""
    return msg


async def send_daily_reward(ctx, bot, base_luck_for_user: float = 1.0):
    author = ctx.author
    luck = random.random()
    reroll = random.random()
    secondary_success = (
        reroll < base_luck_for_user
    )  # Secondary roll to make rewards more likely for higher role users
    if not secondary_success:
        amount = random.randint(4, 10)
        msg = await attempt_to_send_daily_reward_ban_or_send_cm_instead(
            bot.session, author, bot, float(amount)
        )
    if luck > 0.99:
        msg = await attempt_to_send_daily_reward_ban_or_send_cm_instead(
            bot.session, author, bot, 500.0
        )
    elif luck > 0.6:
        amount = random.randint(19, 42)
        msg = await attempt_to_send_daily_reward_ban_or_send_cm_instead(
            bot.session, author, bot, float(amount)
        )
    elif luck > 0.3:
        await send_daily_reward_cryptomonkey(bot, author)
        msg = "Treat! You got a cryptomonKeys NFT"
    else:
        amount = random.randint(10, 19)
        msg = await attempt_to_send_daily_reward_ban_or_send_cm_instead(
            bot.session, author, bot, float(amount)
        )

    await err(ctx, msg)


async def send_daily_reward_cryptomonkey(bot, user: discord.Member) -> None:
    memo = f"Halloween treat for {user.name} on {today()}"
    link = await bot.wax_con.get_random_claim_link(str(user), memo=memo)
    claim_id = await announce_and_send_link(bot, link, user, memo)
    record_user_opened_today_gift(user.id, f"cryptomonKey #{claim_id}")


async def send_daily_reward_ban(
    session: aiohttp.ClientSession, user: discord.User, bot, amount: float
):
    """
    Sends a random amount of banano between max_treat and min_treat to the user's bananobot address
    :param uid: user's discord id
    :param bot: the bot object
    :param amount: how much ban to send
    """
    log(f"Sending {amount} to {user.id}")
    success = await send_ban_to_user(session, user, amount=amount)
    if success:
        record_user_opened_today_gift(user.id, f"{amount} ban")
    return 1


async def get_luck_threshold_for_user(user: discord.User, bot) -> float:
    """Returns the threshold for a secondary check that scales trickortreat failure odds by achieved rank.
    1 always passes this secondary check, 0 never does."""
    if has_cm_role(user, "reeestricted", bot):
        raise InvalidInput("Sorry, REEEstricted users can't get treats for halloween.")
    if has_cm_role(user, "legendary monkey", bot):
        return 1.0
    elif has_cm_role(user, "epic monkey", bot):
        return 0.95
    elif has_cm_role(user, "rare monkey", bot):
        return 0.75
    elif is_citizen(user, bot):
        return 0.7
    elif has_cm_role(user, "uncommon monkey", bot):
        return 0.5
    elif has_cm_role(user, "common monkey", bot):
        return 0.35
    else:
        return 0.0


class TrickOrTreat(MetaCog):

    # Commands
    @commands.command(
        aliases=[
            "trickortreat",
            "plsgivemefreestuffkthx",
        ]
    )
    @commands.guild_only()
    @commands.max_concurrency(1, per=BucketType.user, wait=False)
    async def gift(self, ctx):
        """Halloween gift command. Allows users to, once a day, have a chance of claiming
         a banano reward or random cryptomonKey reward.
        Has a rare chance of a large banano jackpot, and random cryptomonKey rewards
         may rarely be extremely rare and valuable cards.
        Users must have achieved Citizen role on the banano server or be active on
         the cryptomonKey server in order to use this command.
        This command must be used in one of the designated bot spam channels."""
        log(f"Entering trickortreat gift for {ctx.author}", "DBUG")  # type: ignore[unreachable]
        # Verification checks
        await ctx.message.add_reaction("⌛")
        if ctx.channel.id not in [
            915123315176247316,
            524557798416187392,
            631948638062641152,
        ]:
            await ctx.message.clear_reactions()
            return await err(
                ctx,
                "You can't use this command here. Make sure it's in an appropriate channel.",
            )
        opened = check_user_opened_today_gift(ctx.author.id)
        if opened:
            await ctx.message.clear_reactions()
            return await err(ctx, "You already opened your halloween treat for today.")
        base_luck = await get_luck_threshold_for_user(ctx.author, self.bot)
        if base_luck < 0.001:
            await ctx.message.clear_reactions()
            return await err(
                ctx,
                "Sorry, you must either be a Banano citizen or active on the cryptomonKeys "
                "server to use this command.",
            )
        await send_daily_reward(ctx, self.bot, base_luck_for_user=base_luck)
        try:
            await ctx.message.clear_reactions()
            await ctx.message.add_reaction(success_emoji)
        except discord.errors.NotFound:
            # Message was deleted, no problem
            pass
        log(f"Gift command used by {ctx.author} at {now_stamp()}.", "CMMD")

    @commands.command()
    @commands.is_owner()
    async def trickortreat_records(self, ctx):
        await ctx.send(
            "Here's my trickortreat rewards records:",
            file=discord.File("res/trickortreat_records.json"),
        )


async def setup(bot):
    await bot.add_cog(TrickOrTreat(bot))
