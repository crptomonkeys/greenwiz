import json
import typing
from datetime import datetime, timezone, timedelta

import discord

from utils.exceptions import InvalidInput, InvalidResponse

# Returns current timestamp in the desired format, in this case MM/DD/YYYY HH:MM:SS
from utils.settings import (
    NUMBER_REACTIONS,
    BANANO_GUID,
    CM_GUID,
    ACTIVITY_COOLDOWN,
    DONT_LOG,
    BIGNUMS,
)


def epoch() -> float:
    """
    Returns the current epoch in utc, timezone aware.
    :return: Current epoch as a float
    """
    return datetime.now(timezone.utc).timestamp()


def now_stamp():
    """
    Returns the current timestamp as a MM/DD/YYYY HH:MM:SS timestamp.
    :return: The current timestamp as a MM/DD/YYYY HH:MM:SS timestamp.
    :rtype:
    """
    return datetime.now().strftime("%m/%d/%y %H:%M:%S")


def utcnow():
    """
    Returns the current time as a timezone aware utc datetime object.
    :return: the current time as a timezone aware utc datetime object.
    :rtype:
    """
    return datetime.now(tz=timezone.utc)


def load_json_var(name):
    """For loading a list from a json file"""
    with open(f"./res/{name}.json", "r", encoding="utf-8") as f:
        return json.load(f)


def write_json_var(name, obj):
    """For writing a list to a json file"""
    with open(f"./res/{name}.json", "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=4)


# For requesting a footnote on someone
def embed_footer(author):
    return f"Requested by {str(author)} at {now_stamp()}."


# Turns 1000000 into 1.00M or 4358295029 into 4.36B
def biground(num, digits=4):
    digs = 10**digits
    try:
        num = int(num)
        num /= 1
    except TypeError:
        raise InvalidInput(f"{num} is not a number.")
    for i, prefix in BIGNUMS.items():
        if num / (10**i) >= 1:
            return str(round((num * digs) / (10**i)) / digs) + prefix
    return str(round((num * digs) / digs))


# Returns the base 10 order of magnitude of a number
def order(x, count=0):
    if x / 10 >= 1:
        count += order(x / 10, count) + 1
    return count


def get_activity_worth(msg: str) -> int:
    """Calcluates the activity points due for a given message"""
    # if not message.author.bot:
    if len(msg) < 3:
        return 0  # No activity score for teeny messages.
    if msg[0] == "(" or msg[0] == "/":  # or msg[0] == '$' or msg[0] == ',':
        return 0  # No activity score for ooc comments.
    words = msg.split(" ")
    valid_words = list(set([word.casefold() for word in words if len(word) > 3]))
    new_words = len(valid_words)
    return max(new_words - 2, 0)


async def count_command(ctx):
    ctx.bot.stats["commands_counter"].update([ctx.command])
    ctx.bot.stats["users_counter"].update([ctx.author])


def basic_timedelta_to_string(delta: timedelta) -> str:
    """Format a timedelta as a human friendly string. Basic, does not account for longer than weeks."""
    weeks, remainder = divmod(delta.total_seconds(), 3600 * 24 * 7)
    days, remainder = divmod(remainder, 3600 * 24)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    to_return = ""
    if weeks > 0:
        to_return += f"{int(weeks)} weeks "
    if days > 0:
        to_return += f"{int(days)} days "
    if hours > 0:
        to_return += f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
    else:
        to_return += f"{int(minutes):02d}:{int(seconds):02d}"
    return to_return


def parse_item(item):
    """Parse a single key="value" pair into a key value pair."""
    items = item.split("=", 1)  # Put extra occurances of = in the first
    key, value = items[0].strip(), items[1].replace('"', "")
    return key, value


def parse_args(items):
    """Split arguments provdied as a string into a dict."""
    args = dict()
    if not items:
        return args

    quotes = False
    starting, ending = 0, 0
    name = "undefined"
    for c in items:
        ending += 1
        if c == '"':
            quotes = not quotes
        elif c == "=" and not quotes:
            if items[ending - 2] == " ":
                raise InvalidInput("Can not preface an equals sign with a space.")
            name = items[starting : ending - 1].strip()
            starting = ending
        elif c == " " and not quotes and name != "undefined":
            args[name] = items[starting:ending].strip().replace('"', "")
            starting = ending
    else:
        args[name] = items[starting:ending].strip().replace('"', "")

    return args


def log(message: typing.Any, severity="INFO") -> None:
    """
    Prints message to console if bot's severity level warrants it. Allows more customizability in what to log and
    what not to log than classic critical, error, warn, info, debug.
    :param message:
    :type message:
    :param severity:
    :type severity:
    :return:
    :rtype:
    """
    if severity in DONT_LOG:
        return
    print(f"[{severity}] {repr(message)}")


def to_file(text=None) -> discord.File:
    """
    Convert a string to a discord File object.
    :param text:
    :return:
    """
    if isinstance(text, list):
        text = "\n".join(item for item in text)
    with open("./res/long_result.txt", "w+", encoding="utf-8") as f:
        f.write(text)
    return discord.File("./res/long_result.txt")


def load_words() -> [str]:
    """Loads up the top 20,000 most common words into a nice list."""
    with open("res/top_20k_words.txt", encoding="utf-8", errors="replace") as word_file:
        valid_words = list(set(word_file.read().split()))

        return valid_words


def dt(raw: str) -> datetime:
    """Converts a datetime formatted string into a datetime"""
    raw = raw.replace("T", " ")
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")


def today() -> str:
    return str(datetime.now(timezone.utc).date())


async def usage_react(num: int, message: discord.Message):
    """Converts a number from 1-9 to an CM_EMOJIS."""
    reactions_to_add = []
    if num < 10:
        try:
            await message.add_reaction(NUMBER_REACTIONS[num])
        except IndexError:
            pass
    return


async def parse_user(
    ctx, user: str
) -> typing.Union[discord.Member, discord.User, None]:
    """Attempts to turn a string into a user, in the following order of preference:
    ID
    Parsed ID
    username#discrim
    username
    nickname
    Returns a member over a user where possible."""
    user = user.replace("<", "").replace(">", "").replace("@", "")
    try:
        uid = int(user)
        user_obj = ctx.guild.get_member(uid) or ctx.bot.get_user(uid)
        if user_obj is not None:
            return user_obj
    except ValueError:
        pass
    try:
        return ctx.guild.get_member_named(user) or ctx.guild.get_member_named(user[1:])
    except (ValueError, TypeError):
        return None


def scope():
    async def not_in_excluded_guild(ctx):
        """Checks if a command is authorized to be used in this context"""
        excluded_guilds = [BANANO_GUID]
        if ctx.author.id == 125449182663278592:
            return True
        if ctx.guild is None:
            return True
        if ctx.channel.id == 524557798416187392:  # #events-and-giveaways-and-bots
            return True
        return ctx.guild.id not in excluded_guilds

    return not_in_excluded_guild


def has_cm_role(user: discord.User, role: str, bot):
    member = bot.get_guild(CM_GUID).get_member(user.id)
    if not member:
        return False
    for role_obj in member.roles:
        if role_obj.name.lower() == role.lower():
            return True
    return False


def is_citizen(user, bot):
    member = bot.get_guild(BANANO_GUID).get_member(user.id)
    if not member:
        return False
    for role in member.roles:
        if role.name.lower() == "citizens" or role.name.lower() == "citizen":
            return True
    return False


def calc_msg_activity(bot, author: discord.User, content: str):
    # if not message.author.bot:
    words = content.lower().split(" ")
    # valid_words = []
    # for word in words:
    #     if len(word) > 2 and word not in valid_words:
    #         valid_words.append(word)
    valid_words = set(word for word in words if len(word) > 2)
    added_activity_score = max(len(valid_words) - 2, 0)
    if not hasattr(bot, "recent_actives"):
        bot.recent_actives = dict()
    recently_spoke = (
        datetime.now().timestamp() - bot.recent_actives.get(author.id, 0)
        < ACTIVITY_COOLDOWN
    )
    log(
        f"Checking activity for {author}. recently_spoke: {recently_spoke}. added_activity_score:"
        f" {added_activity_score}. content: {content}",
        "DBUG",
    )
    if added_activity_score > 0 and not recently_spoke:
        bot.recent_actives[author.id] = datetime.now().timestamp()
        return added_activity_score
    return 0


async def save_temp_then_share(ctx, content: str, message: str, filename: str) -> None:
    with open(filename, "w+", encoding="utf-8") as f:
        f.write(content)
    await ctx.send(message, file=discord.File(filename))


async def get_addrs_from_content_or_file(
    message: discord.Message, provided: str = None
) -> (bool, [str]):
    """Returns a tuple of bool and list of str.
    The bool is whether the results shoould be relayed inline or in a file.
    The list is a list of addresses from either the message attachment, if available, or the message content."""
    if hasattr(message, "attachments") and len(message.attachments) > 0:
        return (False, await addrs_from_file(message.attachments[0]))
    deliniator = r"\n"
    if provided is None:
        raise InvalidInput(
            "No addresses provided. Please either attach a .txt list or put a list of addresses in this command."
        )
    i_list = list(
        set(
            [address.lower().replace(" ", "") for address in provided.split(deliniator)]
        )
    )
    return True, i_list


async def addrs_from_file(file: discord.File) -> [str]:
    """Reads a discord attachment and returns a list of strings of addresses in it."""
    if file.filename[-4:] not in [".txt", ".csv"]:
        raise InvalidInput("Please provide a .txt or .csv file, I can't read that one.")
    if file.filename[-4:] == ".csv":
        return await addrs_from_csv(file)
    return await addrs_from_txt(file)


async def addrs_from_txt(file: discord.File) -> [str]:
    """Reads a txt discord attachment and returns a list of strings of addresses in it."""
    result_string = str(await file.read())[2:-1].replace("\\r", "")
    return [i.lower() for i in result_string.split(r"\n")]


async def addrs_from_csv(file: discord.File) -> [str]:
    """Reads a csv discord atachment and returns a list of strings of addresses in it."""
    result_string = str(await file.read())[2:-1]
    return [i.lower() for i in result_string.split(",")]
