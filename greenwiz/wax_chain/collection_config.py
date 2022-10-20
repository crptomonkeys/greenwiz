from dataclasses import dataclass
from typing import Callable, Any, Union

from discord import User

from utils.cryptomonkey_util import cryptomonkey_dropper_admin, has_nifty
from utils.exceptions import UnableToCompleteRequestedAction
from utils.settings import (
    YOSHI_PRIV_KEY,
    WAX_PRIV_KEY,
    WAX_ACC_NAME,
    DEFAULT_WAX_COLLECTION,
    MONKEYMATCH_PRIV_KEY,
    MONKEYMATCH_ACC_NAME,
    CM_GUID,
    DEFAULT_FALLBACK_CHANNEL,
)


def yoshi_admin(user: User, bot):
    """Uplift team members can drop an unlimited number of cards per day"""
    member = bot.get_guild(805449582124466206).get_member(user.id)
    for role in member.roles:
        if role.id in [869557082452553768]:
            return True
    return False


def user_is_authd_to_drop_yoshis(user: User, bot):
    """Uplift team members and community moderators can drop some cards every day."""
    member = bot.get_guild(805449582124466206).get_member(user.id)
    if member is None:
        return False
    for role in member.roles:
        if role.id in [
            848630244844109914,
            870013351391035422,
            869557082452553768,
            894809331411853366,
        ]:
            return True
    return False


collections = {
    "crptomonkeys": {
        "collection": "crptomonkeys",
        "name": "cryptomonKeys",
        "web": "https://cryptomonkeys.cc/",
        "drop_ac": WAX_ACC_NAME,
        "emoji": "<:vase:769372650387537951>",
        "guild": CM_GUID,
        "announce_ch": 763776455338360883,
        "intro_role": 766225390023868416,
        "intro_ch": 758054443479597077,
        "priv_key": WAX_PRIV_KEY,
        "drop_func": has_nifty,
        "admin_func": cryptomonkey_dropper_admin,
        "daily_limit": 15,
    },
    "lgnd.art": {
        "collection": "lgnd.art",
        "name": "LGND",
        "web": "https://lgnd.art/",
        "drop_ac": "dropsofyoshi",
        "guild": 805449582124466206,
        "announce_ch": 894708209149968405,
        "priv_key": YOSHI_PRIV_KEY,
        "drop_func": yoshi_admin,
        "admin_func": user_is_authd_to_drop_yoshis,
    },
    "monkeysmatch": {
        "collection": "none",
        "drop_ac": MONKEYMATCH_ACC_NAME,
        "priv_key": MONKEYMATCH_PRIV_KEY,
    },
}

active_collections = dict()
# Server ids for which lgnd.art should be the relevant collection
for g in [848626465373552701, 867775761163091999, 805449582124466206]:
    active_collections[g] = "lgnd.art"


@dataclass
class CollectionData:
    @staticmethod
    def _drop_func(_user: User, _bot):
        return False

    @staticmethod
    def _admin_func(_user: User, _bot):
        return False

    collection: str = ""
    drop_ac: str = ""
    priv_key: str = ""
    name: str = "Unnamed Collection"
    web: str = "[No website]"
    emoji: str = "🎁"
    guild: int = 348929154114125827
    announce_ch: int = DEFAULT_FALLBACK_CHANNEL
    drop_func: Callable = _drop_func
    admin_func: Callable = _admin_func
    intro_role: int = None
    intro_ch: int = None
    daily_limit: int = 5
    link_message_append: str = (
        "WARNING: Tip bot claimlinks may be cancelled 91 days after issuance."
    )

    def __repr__(self):
        return self.collection

    def __hash__(self):
        return hash(self.collection)


def get_collection_info(
    collection: Union[str, CollectionData], full: bool = False
) -> CollectionData:
    """Fetch configuration data for a given wax_chain collection"""
    if type(collection) == CollectionData:
        collection = collection.collection
    res = collections.get(collection, None)
    if res is None:
        raise UnableToCompleteRequestedAction
    res = CollectionData(**res)
    if not full:
        # Reduce opportunities for sensitive data to accidentally leak in a debugging printout or similar
        # by only including private key in calls that explicitly ask for it.
        del res.priv_key
    return res


def adjust_daily_limit(collection: str, limit: int) -> None:
    """Alter the daily drop limit until the next bot restart."""
    collections[collection]["daily_limit"] = limit


def get_guild_collection_info(guild_id: int) -> CollectionData:
    """Fetch configuration data for the given server's collection"""
    return get_collection_info(active_collections.get(guild_id, DEFAULT_WAX_COLLECTION))


def determine_collection(guild: Any, sender: User, bot) -> (bool, CollectionData):
    """Determine which collection a user can/wants to send cards from based on the guild and user. Also determines
    level of user's authorization: 0 is not auth'd for this collection, 1 is normal auth, 2 is unlimited."""
    if not guild:
        raise UnableToCompleteRequestedAction("I can not send drops in DMs.")
    appropriate_collection = get_guild_collection_info(guild.id)
    user_is_authd = (
        appropriate_collection.drop_func(sender, bot) or sender.id == bot.user.id
    )
    if (
        user_is_authd
        and appropriate_collection.admin_func(sender, bot)
        or sender.id == bot.user.id
    ):
        auth = 2
    elif user_is_authd:
        auth = 1
    else:
        auth = 0
    return auth, appropriate_collection
