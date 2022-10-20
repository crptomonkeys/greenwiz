import datetime
import os

from discord.ext import commands

from utils.meta_cog import MetaCog
from utils.settings import BANANO_GUID
from utils.util import log, now_stamp


# Returns current datestamp as YYYY-MM-DD
def today():
    return datetime.date.today().strftime("%Y-%m-%d")


def writeline(path: str, line: str):
    with open(path, "a+", encoding="utf-8") as f:
        try:
            f.write(line + "\n")
        except UnicodeEncodeError:
            f.write(
                f"[WRN] {now_stamp()}: A UnicodeEncodeError occurred trying to write a message log.\n"
            )


def do_log_msg(message):
    # Build a log of this message
    log_msg = f"{message.author}"
    if message.author.bot:
        log_msg += f" [B]"
    if message.system_content is not None:
        log_content = message.system_content.replace("\n", "\\n")
    elif message.content is not None:
        log_content = message.content.replace("\n", "\\n")
    else:
        log_content = "Unknown Message"
    log_msg += f" >  {log_content}  |  {now_stamp()}"
    if len(message.embeds) > 0:
        eb = message.embeds[0]
        fields = "  &  ".join(f"'{field.name}': {field.value}" for field in eb.fields)
        log_msg += f'  |  Embed "{eb.author.name}  {eb.description}": {fields}'
    if len(message.attachments) > 0:
        log_msg += f"  |  Attachment: {message.attachments[0].url}"
    try:
        log(f"{log_msg}  |  {message.channel.name}  |  {message.guild.name}", "MESG")
        send_log(log_msg, message.guild.name, message.channel.name)
    except AttributeError:
        log(f"{log_msg}  |  DMs  |  {message.channel.recipient}", "MESG")
        try:
            send_log(log_msg, "DMs", message.channel.recipient)
        except OSError:
            send_log(log_msg, "DMs", message.channel.id)


# Log a message.
def send_log(message: str, guild: str, channel: str):
    try:
        writeline(f"./logs/{guild}/{channel}_{today()}_log.log", message)
    except OSError:
        try:
            os.makedirs(f"./logs/{guild}")
            log(f"Created a new guild log folder for {guild}.")
            writeline(f"./logs/{guild}/{today()}_log.log", message)
        except OSError:
            os.makedirs(f"./logs")
            os.makedirs(f"./logs/{guild}")
            log(f"Created a new guild log folder for {guild}.")
            writeline(f"./logs/{guild}/{today()}_log.log", message)

    return


class Logging(MetaCog):

    # =============================Message handler=========================
    @commands.Cog.listener()
    async def on_message(self, message):
        # Don't do stuff for messages in d.py or banano guilds
        if message.guild is not None and message.guild.id in [
            336642139381301249,
            BANANO_GUID,
        ]:
            return
        # ===========================LOG=============================
        do_log_msg(message)


async def setup(bot):
    await bot.add_cog(Logging(bot))
