"""
The command error handler.
"""
import asyncio
import traceback
from json import JSONDecodeError

import discord
from aioeos.exceptions import EosAssertMessageException
from discord.ext import commands

from utils.exceptions import (
    UnableToCompleteRequestedAction,
    InvalidResponse,
    InvalidInput,
)
from utils.paginate import send as p_send


async def handle_command_error(bot, ctx, error: BaseException) -> None:
    debug = "DBUG"
    # Ignore local command error handlers, but not assertion errors as if they happen we need all the
    # info on them
    if hasattr(ctx.command, "on_error") and not isinstance(
        error, (AssertionError, TypeError)
    ):
        return

    # Strip CommandInvokeError and ignore errors that require no reaction whatsoever.
    error = getattr(error, "original", error)
    ignored = (
        commands.CommandNotFound,
        commands.DisabledCommand,
        commands.NotOwner,
    )
    if isinstance(error, ignored):
        return

    bad_quotes = (
        commands.UnexpectedQuoteError,
        commands.InvalidEndOfQuotedStringError,
        commands.ExpectedClosingQuoteError,
        commands.ArgumentParsingError,
    )
    bot_or_command_missing_perms = (
        commands.BotMissingPermissions,
        commands.BotMissingRole,
        commands.BotMissingAnyRole,
        commands.MissingRole,
        commands.MissingAnyRole,
        commands.MissingPermissions,
    )
    bad_argument_errors = (
        commands.BadArgument,
        commands.BadUnionArgument,
        commands.UserInputError,
        commands.ConversionError,
    )

    # Log anything not totally ignored
    lines = traceback.format_exception(type(error), error, error.__traceback__)
    traceback_text = f"```py\n{''.join(lines)}\n```"
    if hasattr(error, "args") and len(error.args) > 0:
        addin = f": {error.args[0]} ({error.args})"
    else:
        addin = ""
    bot.log(
        f"{ctx.author} triggered {type(error)}::{error} in command {ctx.command}{addin}"
        f"\n\n{traceback_text}",
        debug,
    )

    # Several common errors that do require handling
    # Intentionally raised user facing errors
    if isinstance(
        error, (InvalidResponse, UnableToCompleteRequestedAction, InvalidInput)
    ):
        await bot.quiet_fail(ctx, str(error))
        return
    elif isinstance(error, AssertionError):  # Don't return. *also* send this one to dev
        await bot.quiet_fail(ctx, str(error), delete=False)
    # Wrong place or no perms errors:
    elif isinstance(error, commands.NoPrivateMessage):
        await bot.quiet_fail(
            ctx, f"the {ctx.command} command can not be used in private messages."
        )
        return
    elif isinstance(error, commands.PrivateMessageOnly):
        await bot.quiet_fail(
            ctx, f"{ctx.command} command can only be used in private messages."
        )
        return
    elif isinstance(error, bot_or_command_missing_perms):
        await bot.quiet_fail(ctx, f"{error}")
        return
    elif isinstance(error, commands.NSFWChannelRequired):
        await bot.quiet_fail(
            ctx,
            f"the {ctx.command} command must be used in an NSFW-marked channel.",
        )
        return
    elif isinstance(error, discord.ext.commands.errors.CommandOnCooldown):
        await bot.quiet_fail(
            ctx,
            "you are on cooldown for that command. Try again in a little while.",
        )
        return
    elif isinstance(error, commands.MaxConcurrencyReached):
        await bot.quiet_fail(
            ctx, "too many instances of this command are being run at the moment."
        )
        return
    elif isinstance(error, commands.CheckFailure):
        await bot.quiet_fail(ctx, "you are not authorized to perform this command.")
        return
    # User misformulated command errors
    elif isinstance(error, commands.BadBoolArgument):
        await bot.quiet_fail(
            ctx,
            'boolean arguments must be "yes"/"no", "y"/"n", "true"/"false", "t"/"f", '
            '"1"/"0", "enable"/"disable" or "on"/"off".',
        )
        return
    elif isinstance(error, commands.PartialEmojiConversionFailure):
        await bot.quiet_fail(ctx, "that is not an CM_EMOJIS.")
        return
    elif isinstance(error, commands.EmojiNotFound):
        await bot.quiet_fail(ctx, "I didn't find that CM_EMOJIS.")
        return
    elif isinstance(error, commands.BadInviteArgument):
        await bot.quiet_fail(ctx, "that invite is invalid or expired.")
        return
    elif isinstance(error, commands.RoleNotFound):
        await bot.quiet_fail(ctx, "I didn't find that role.")
        return
    elif isinstance(error, commands.BadColourArgument):
        await bot.quiet_fail(ctx, "that's not a valid color")
        return
    elif isinstance(error, commands.ChannelNotReadable):
        await bot.quiet_fail(
            ctx, "I don't have permission to read messages in that channel."
        )
        return
    elif isinstance(error, commands.ChannelNotFound):
        await bot.quiet_fail(ctx, "I didn't find that channel.")
        return
    elif isinstance(error, commands.MemberNotFound):
        await bot.quiet_fail(ctx, "I didn't find that member.")
        return
    elif isinstance(error, commands.UserNotFound):
        await bot.quiet_fail(ctx, "I didn't find that user.")
        return
    elif isinstance(error, commands.UserNotFound):
        await bot.quiet_fail(ctx, "I didn't find that message.")
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send_help(ctx.command)
        await bot.quiet_fail(ctx, "incomplete command, missing a required value.")
        return
    elif isinstance(error, commands.TooManyArguments):
        await ctx.send_help(ctx.command)
        await bot.quiet_fail(ctx, "too many values passed to this command.")
        return
    elif isinstance(error, bad_quotes):  # User messed up quotes
        await bot.quiet_fail(
            ctx,
            "quotation marks do not balance. Make sure you close every quote you "
            "open.",
        )
        return
    elif isinstance(error, bad_argument_errors):
        await bot.quiet_fail(
            ctx,
            f"improper command. Check help {ctx.command} to help you "
            f"formulate this command correctly.",
        )
        return
    # Extension and command registration errors
    elif isinstance(error, commands.ExtensionAlreadyLoaded):
        await bot.quiet_fail(ctx, "that extension is already loaded.")
        return
    elif isinstance(error, commands.ExtensionNotLoaded):
        await bot.quiet_fail(ctx, "that extension is not loaded.")
        return
    elif isinstance(error, commands.NoEntryPointError):
        await bot.quiet_fail(ctx, "that extension does not have a setup function.")
        return
    elif isinstance(error, commands.ExtensionNotFound):
        await bot.quiet_fail(ctx, "I see no such extension.")
        return
    elif isinstance(error, commands.ExtensionFailed):
        await bot.quiet_fail(ctx, "that extension refused to load.")
        return
    elif isinstance(error, commands.ExtensionError):
        await bot.quiet_fail(ctx, "uncaught ExtensionError.", delete=False)
        return
    elif isinstance(error, commands.CommandRegistrationError):
        await bot.quiet_fail(
            ctx,
            f"failed to register a duplicate command name: {error}",
            delete=False,
        )
        return
    # Unknown, likely runtime environment-dependent non-deterministic, discord.py-triggered error
    elif isinstance(error, discord.ClientException):
        await bot.quiet_fail(
            ctx, "hmm, something went wrong. Try that command again.", delete=False
        )
        return
    # Other
    elif isinstance(error, EosAssertMessageException):
        try:
            text = (
                error.__repr__().split("'details': [{'message': '")[1].split("', '")[0]
            )
        except IndexError:
            text = error.__repr__()
        await bot.quiet_fail(ctx, text, delete=False)
        return
    elif isinstance(error, discord.HTTPException):
        await bot.quiet_fail(
            ctx,
            "I received an HTTP exception from discord. Most likely, the result was longer than 4000 characters.",
            delete=False,
        )
        return
    elif isinstance(error, JSONDecodeError):
        await bot.quiet_fail(
            ctx,
            f"the api for {ctx.command} appears to be down at the moment. Try again later.",
        )
        return
    elif isinstance(error, asyncio.TimeoutError):
        await bot.quiet_fail(
            ctx,
            "you took too long. Please re-run the command to continue when you're ready.",
        )
        return
    else:
        # Get data from exception and format
        lines = traceback.format_exception(type(error), error, error.__traceback__)
        traceback_text = "".join(lines)
        # If something goes wrong with sending the dev these errors it's a bit of a yikes so take some
        #  special care here.
        try:
            await ctx.send(
                f"Hmm, something went wrong with {ctx.command}. "
                f"I have let the developer know, and they will take a look."
            )
            owner = bot.get_user(bot.owner_id)
            await owner.send(
                f"Hey {owner}, there was an error in the command {ctx.command}: {error}."
                f"\n It was used by {ctx.author} in {ctx.guild}, {ctx.channel}."
            )
            await p_send(owner, traceback_text, pre_text="```py\n", post_text="\n```")
        except discord.errors.Forbidden:
            await ctx.message.add_reaction("❌")
            bot.log(f"{ctx.command} invoked in a channel I do not have write perms in.")
        bot.log(
            f"Error triggered in command {ctx.command}: {error}, {lines}",
            "critical",
        )
        return
