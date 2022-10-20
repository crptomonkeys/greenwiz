import os.path
import pickle
from typing import Optional

import discord
from discord.ext import commands
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from utils.cryptomonkey_util import monkeyprinter
from utils.exceptions import InvalidInput
from utils.green_api_wrapper import GreenApi
from utils.meta_cog import MetaCog
from utils.util import parse_user


def fetch_google_sheet_values(sheet):
    def inner(spreadsheet_id: str, sheet_range: str):
        sheet_result = (
            sheet.values()
            .get(spreadsheetId=spreadsheet_id, range=sheet_range)
            .execute()
        )
        values = sheet_result.get("values", [])
        return values

    return inner


class Googleapi(MetaCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.creds = None
        if not hasattr(self.bot, "green_api"):
            self.bot.green_api = GreenApi(self.session)
        self.log("Configuring spreadsheet loader...", "DBUG")
        # Find the authorizations file
        if os.path.exists("token.pickle"):
            with open("token.pickle", "rb") as token:
                self.creds = pickle.load(token)
        # If there are no (valid) credentials available, update creds with login
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json",
                    ["https://www.googleapis.com/auth/spreadsheets.readonly"],
                )
                self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.pickle", "wb") as token:
                pickle.dump(self.creds, token)
        service = build("sheets", "v4", credentials=self.creds)
        # Load in buy and sell prices from google sheets using sheets api
        self.sheet = service.spreadsheets()
        self.bot.sheet_values = fetch_google_sheet_values(self.sheet)
        self.log("Spreadsheet loader successfully initialized", "DBUG")
        self.bot.cogs_initialized["googleapi"] = True

    @commands.command()
    @commands.check(monkeyprinter())
    async def fetch_addresses_from_sheet(
        self,
        ctx,
        sheet_code: str,
        role_required: Optional[str] = None,
        discord_range: str = None,
        wax_range: str = None,
    ):
        """Makes a list of addresses from a spreadsheet that fit the following criteria: discord usernames are
        unique, present in the cryptomonkeys server, and have the specified role in the cryptomonkeys server. Should
        be of the form:
        fetch_addresses_from_sheet XXXXXX-XXXXXXX 'Sheet1!B2:C' spoke
        or
        fetch_addresses_from_sheet XXXXXX-XXXXXXX 'Sheet1!A2:A' 'Sheet1!C2:C' introduced
        """
        if sheet_code == "survey1":
            sheet_code = self.bot.settings.SURVEY_1_SHEET_CODE
            discord_range = "'Form Responses 1'!H2:H"
            wax_range = "'Form Responses 1'!G2:G"

        if not discord_range or not wax_range:
            raise InvalidInput(
                "discord_range and wax_range are required if the sheet isn't a known one."
            )

        if role_required is None:
            role = None
        else:
            role = discord.utils.find(
                lambda m: role_required.lower() in m.name.lower(), ctx.guild.roles
            )
            if role is None:
                raise InvalidInput(
                    f"I could not find a role named {role_required} in this server's roles."
                )
        discord_names = self.bot.sheet_values(sheet_code, discord_range)
        wax_addresses = self.bot.sheet_values(sheet_code, wax_range)
        if not discord_names or not wax_addresses:
            return await ctx.send(
                "Something went wrong, no data found in the spreadsheet or the request was "
                "malformed."
            )
        valid_addresses = set()
        discord_names = [i[0] for i in discord_names]
        wax_addresses = [i[0] for i in wax_addresses]
        self.log(discord_names, "DBUG")
        self.log(wax_addresses, "DBUG")
        for name, address in zip(discord_names, wax_addresses):
            if address in valid_addresses:
                continue
            user = await parse_user(ctx, name)
            if user is None:
                continue
            if role_required is None or role in user.roles:
                valid_addresses.add(address)
        self.log(valid_addresses, "DBUG")
        blacklist = await self.bot.green_api.get_blacklist()
        adders = valid_addresses - blacklist
        with open("res/tmp/addresses_from_sheet.txt", "w+", encoding="utf-8") as f:
            f.write(",".join(adders))

        await ctx.send(
            f"Found {len(adders)} unique wallet entries of valid discord users with the role "
            f"{role_required} and who are not blacklisted (out of {len(wax_addresses)} form submissions). "
            f"Here's a csv of them all:",
            file=discord.File("res/tmp/addresses_from_sheet.txt"),
        )


async def setup(bot):
    await bot.add_cog(Googleapi(bot))
