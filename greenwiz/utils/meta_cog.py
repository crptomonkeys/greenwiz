from discord.ext import commands


class MetaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = bot.session
        self.log = bot.log
        self.storage = self.bot.storage

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.log(f"{self.qualified_name} is ready.")
        self.bot.cogs_ready[self.qualified_name] = True
