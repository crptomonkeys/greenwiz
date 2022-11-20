# ==================== Discord Settings =============================
import os

# ===================================================================


# ================ Safe To Change, Global ===========================
# 'MESG', 'INFO', 'DBUG', 'CMMD', 'TRFR', 'PRIO', 'WARN' etc are all options here. These values will *not* be logged.
DONT_LOG = ["MESG", "DBUG"]
# Seconds before querying api again to refresh user dict
WAX_CACHE_TIME = 60
# The default collection that can be used (with appropriate privileges) to drop NFTs in servers without a configured
# collection .
DEFAULT_WAX_COLLECTION = "crptomonkeys"
# The wax permissions for each type of use
TIP_ACC_PERMISSION = "claimlink"
SALT_ACC_PERMISSION = "match"
MINT_ACC_PERMISSION = "mint"
# The minimum number of seconds after last activity to have a message count as activity for spam filtering purposes
ACTIVITY_COOLDOWN = 10
try:
    from utils import settings_priv

    # The text to show in the bot's "Playing" field on its profile.
    STATUS = settings_priv.STATUS
except AttributeError:
    settings_priv = None
    STATUS = "The first, fastest and most magical NFT tipbot."
# The default channel for a variety of log messages that aren't able to be sent on a server-specific basis.
DEFAULT_FALLBACK_CHANNEL = 893230290137395260
# After sending a 'chatloot has timed out because you weren't chatting enough here' message, the default duration in
# seconds to wait before sending this message again
CHATLOOT_TIMEOUT_NOTIF_INTERVAL = 5 * 60
# The suffix of the prefix for a non-prod bot
TEST_PREFIX_OVERRIDE = ",,"
# ===================================================================

# The cryptomonKeys and Banano server ids
BANANO_GUID = 415935345075421194
CM_GUID = 733122024448458784
# The endpoint to get special wax addresses from
QUERY_SPECIALS_URL = (
    "https://eosauthority.com/api/spa/bidnames?dir=asc&limit=1000&network=wax&page="
)
# The endpoint to get upland recent visitors from.
UPLAND_QUERY_URL = "https://api.upland.me/teleports/visitors/"
# The list of upland property ids eligible for metaforce and cryptomonkeys rewards, respectively.
METAFORCE_PROPERTY_LIST = [
    81379264919556,
    81379365582846,
    81357471319485,
    81331349194353,
    82107596989987,
    79520901742515,
    79539289572034,
    79539474123067,
    79560646973286,
    78897829598110,
    78049858823898,
    81864629532013,
]
CRYPTOMONKEY_PROPERTY_LIST = [
    81378912598000,
    81356145919400,
    81333278573795,
    82107328554437,
    79520616529774,
    79566619660565,
    78897980593015,
    78053214267194,
    81856693908761,
]

# The people who can drop unlimitted daily cryptomonKeys and have some other cryptomonKey drop related overrides
CRYPTOMONKEY_DROP_ADMINS = [
    125449182663278592,  # Vyryn
    404674851836657674,  # Bantano
    517484768791756822,  # Soggy
    682514501865570408,  # green
    118923557265735680,  # Kron
    204638784942243850,  # Piga
    416929638426869762,  # ghostcam
    846686858981146627,  # Mayor
    707092320767705122,  # Aku
    533663361770979369,  # WhiteFlag
]

# ============= Defaults for Per-Server Settings ====================
# The default prefix the bot should respond to, in addition to mentions.
DEFAULT_PREFIX = ","
# The default $$ payout per-unit of activity.
# Set to 0 to disable activity payouts.
DEFAULT_ACTWEIGHT = 5
# Minimum number of seconds after last activity to have a message count as activity
DEFAULT_ACTIVITY_COOLDOWN = 7
# ===================================================================

SERVER_DEFAULT_VALUES = {
    "prefix": DEFAULT_PREFIX,
    "actweight": DEFAULT_ACTWEIGHT,
    "log_channel": -1,
    "payout_channel": -1,
}
# ===================================================================


# ============ Not Recommended to Change, Global ====================
# Which database within the redis instance to connect to
DB_NUM = 2
# The max number of characters that fit into a logged message
CONTENT_MAX = 1970
# A lookup table for how long an hour, a day etc are in seconds.
TIME_VALUES = {
    "s": 1,
    "m": 60,
    "h": 60 * 60,
    "d": 60 * 60 * 24,
    "w": 60 * 60 * 24 * 7,
    "y": 60 * 60 * 24 * 365,
}
# A lookup table to match numbers 1-0 with reaction unicode values.
NUMBER_REACTIONS = [
    "1\u20e3",
    "2\u20e3",
    "3\u20e3",
    "4\u20e3",
    "5\u20e3",
    "6\u20e3",
    "7\u20e3",
    "8\u20e3",
    "9\u20e3",
]
# The inverse of the above
REACTION_NUMBERS = {
    "1⃣": 1,
    "2⃣": 2,
    "3⃣": 3,
    "4⃣": 4,
    "5⃣": 5,
    "6⃣": 6,
    "7⃣": 7,
    "8⃣": 8,
    "9⃣": 9,
}
# The previxes for converting big numbers
BIGNUMS = {24: "Y", 21: "Z", 18: "E", 15: "Q", 12: "T", 9: "B", 6: "M", 3: "K"}
# Which discord perms are considered basic/important
BASIC_PERMS = ["administrator", "manage_guild", "ban_members", "manage_roles"]
# Which discord perms are consider significant/notable
SIGNIFICANT_PERMS = [
    "deafen_members",
    "kick_members",
    "manage_channels",
    "manage_emojis",
    "manage_messages",
    "manage_nicknames",
    "manage_webhooks",
    "mention_everyone",
    "move_members",
    "mute_members",
    "priority_speaker",
    "view_audit_log",
]
# A mapping of cryptomonKey rarities to their corresponding custom emojis
CM_EMOJIS = {
    "Common": "<:CMCommon:753660997377589391>",
    "Uncommon": "<:CMUncommon:753660997130256385>",
    "Rare": "<:CMRare:753660996928667730>",
    "Epic": "<:CMEpic:753660996941381753>",
    "Legendary": "<:CMLegendary:753660996790255830>",
    "Unique": "<:CMUnique:753660997180457050>",
}
# ===================================================================


# ==========Imported From Environment/Secret, Global ================
# If you wish, you can safely overwrite the 'os.getenv' with your own
# values for each of these directly in this file. Just don't share
# the file with anyone else if you do that. Leaking any of these
# isn't great, and leaking your token would be especially bad.
try:
    # If settings_priv.py exists and is fully filled out, use it over env variables
    TOKEN = settings_priv.TOKEN
    DEPLOY_HOOK_URL = settings_priv.DEPLOY_HOOK_URL
    REDIS_IP = settings_priv.REDIS_IP
    REDIS_AUTH = settings_priv.REDIS_AUTH
    WAX_PRIV_KEY = settings_priv.WAX_PRIV_KEY
    WAX_ACC_NAME = settings_priv.WAX_ACC_NAME
    YOSHI_ACC_NAME = settings_priv.YOSHI_ACC_NAME
    YOSHI_PRIV_KEY = settings_priv.YOSHI_PRIV_KEY
    MONKEYMATCH_ACC_NAME = settings_priv.MONKEYMATCH_ACC_NAME
    MONKEYMATCH_PRIV_KEY = settings_priv.MONKEYMATCH_PRIV_KEY
    BLACKLIST_AUTH_CODE = settings_priv.BLACKLIST_AUTH_CODE
    SURVEY_1_SHEET_CODE = settings_priv.SURVEY_1_SHEET_CODE
    SURVEY_2_SHEET_CODE = settings_priv.SURVEY_2_SHEET_CODE
    SURVEY_3_SHEET_CODE = settings_priv.SURVEY_3_SHEET_CODE
    CMSTATS_SERVER = settings_priv.CMSTATS_SERVER
    BLACKLIST_ADD = settings_priv.BLACKLIST_ADD
    BLACKLIST_REMOVE = settings_priv.BLACKLIST_REMOVE
    BLACKLIST_GET = settings_priv.BLACKLIST_GET
    ENV = settings_priv.ENV
    print("Using settings_priv")


except ImportError:
    print("Attempting to use env variables")
    # Set the token in deployment through an environment variable
    TOKEN = os.getenv("BOT_TOKEN")
    # Deployment notification webhook
    DEPLOY_HOOK_URL = os.getenv("DEPLOY_HOOK_URL")
    # Redis IP and password
    REDIS_IP = os.getenv("REDIS_IP")
    REDIS_AUTH = os.getenv("REDIS_AUTH")
    # For the tipbot functionality, the default NFT Tipbot account private key and name
    WAX_PRIV_KEY = os.getenv("WAX_PRIV_KEY")
    WAX_ACC_NAME = os.getenv("WAX_ACC_NAME")
    YOSHI_ACC_NAME = os.getenv("YOSHI_ACC_NAME")
    YOSHI_PRIV_KEY = os.getenv("YOSHI_PRIV_KEY")
    MONKEYMATCH_ACC_NAME = os.getenv("MONKEYMATCH_ACC_NAME")
    MONKEYMATCH_PRIV_KEY = os.getenv("MONKEYMATCH_PRIV_KEY")
    BLACKLIST_AUTH_CODE = os.getenv("BLACKLIST_AUTH_CODE")
    SURVEY_1_SHEET_CODE = os.getenv("SURVEY_1_SHEET_CODE")
    SURVEY_2_SHEET_CODE = os.getenv("SURVEY_2_SHEET_CODE")
    SURVEY_3_SHEET_CODE = os.getenv("SURVEY_3_SHEET_CODE")
    CMSTATS_SERVER = os.getenv("CMSTATS_SERVER")
    BLACKLIST_ADD = os.getenv("BLACKLIST_ADD")
    BLACKLIST_REMOVE = os.getenv("BLACKLIST_REMOVE")
    BLACKLIST_GET = os.getenv("BLACKLIST_GET")

    ENV = os.getenv("ENV")

# ===================================================================
