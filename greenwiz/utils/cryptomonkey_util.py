import discord

from utils.settings import CM_GUID, BANANO_GUID, CRYPTOMONKEY_DROP_ADMINS


def has_nifty(member: discord.Member, bot):
    """Niftys can drop some cards every day."""
    if member.guild.id != CM_GUID:
        _member = bot.get_guild(CM_GUID).get_member(member.id)
    else:
        _member = member
    if _member is None:
        return False
    if _member.id in [
        224974384710811649,  # triggerhaven
        417522436792254475,  # anemone
    ]:
        return True
    for role in _member.roles:
        if role.id in [733313560247140422, 800575369090039838, 733313838375632979]:
            return True

    # Also let banano Jungle Juntas drop like niftys
    _member = bot.get_guild(BANANO_GUID).get_member(_member.id)
    for role in _member.roles:
        if role.id in [416789711034777600]:
            return True
    return False


# Checks if a user has nifty or monkeyprinter roles specifically
def nifty():
    async def user_auth_check(ctx):
        if not hasattr(ctx.author, "roles"):
            return False
        return has_nifty(ctx.author, ctx.bot)

    return user_auth_check


def cryptomonkey_dropper_admin(member: discord.Member, bot):
    return member.id in CRYPTOMONKEY_DROP_ADMINS


def monkeyprinter():
    async def user_auth_check(ctx):
        if not hasattr(ctx.author, "roles"):
            return False
        if ctx.author.guild.id != CM_GUID:
            member = ctx.bot.get_guild(CM_GUID).get_member(ctx.author.id)
        else:
            member = ctx.author
        if member is None:
            return False
        if member.id == 118923557265735680:  # Special override for Kron
            return True
        for role in member.roles:
            if role.id in [733313560247140422]:
                return True
        return False
        # monkeyprinter is 733313560247140422:

    return user_auth_check


def print_orpiga():
    async def user_auth_check(ctx):
        if not hasattr(ctx.author, "roles"):
            return False
        return ctx.author.id in CRYPTOMONKEY_DROP_ADMINS

    return user_auth_check
