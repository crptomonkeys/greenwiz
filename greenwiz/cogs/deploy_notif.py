import json

from discord.ext import commands

from utils.meta_cog import MetaCog
from utils.settings import DEPLOY_HOOK_URL

headers = {"Content-Type": "application/json"}


class DeployNotif(MetaCog):

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        data = {
            "embeds": [
                {
                    "description": f"Re-deployed successfully for {len(self.bot.users)} users in"
                    f" {len(self.bot.guilds)} guilds.",
                    "title": f"{self.bot.user} Deployment notification",
                }
            ]
        }
        result = await self.session.post(
            DEPLOY_HOOK_URL, data=json.dumps(data), headers=headers
        )
        if result.status != 200 and result.status != 204:
            self.log(
                f"Failed to send deployment notification, code {result.status}.", "WARN"
            )
        else:
            self.log("Deployment notification successfully sent.")
        await super().on_ready()


async def setup(bot):
    await bot.add_cog(DeployNotif(bot))
