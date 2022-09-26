import re
import requests

import aiohttp
from utils.settings import QUERY_SPECIALS_URL

# This is a fallback list, last updated September 12 2022
special_wax_addresses = {
    "vault",
    "anyo",
    "bp",
    "items",
    "wdw",
    "d",
    "sam",
    "mini",
    "id",
    "lunr",
    "hasbroinc",
    "bluewizard",
    "de",
    "bitrrex",
    "kit",
    "gaia",
    "5",
    "cat",
    "america",
    "sx",
    "tcg",
    "rarez",
    "sl",
    "bittex",
    "jp",
    "hype",
    "earn",
    "place",
    "greenrabbit",
    "capcom",
    "kardomance",
    "m",
    "net",
    "souljaboy",
    "startups",
    "venice",
    "john",
    "united",
    "ws",
    "waxitems",
    "runway",
    "blockchain",
    "rude",
    "honeyhunt",
    "matt",
    "gems",
    "dibbs",
    "admin",
    "cj",
    "tycoon",
    "zip",
    "shinies",
    "man",
    "xy",
    "upbit",
    "bricks",
    "ogs",
    "nbc",
    "fast",
    "bratz",
    "banxa",
    "spinach",
    "l",
    "tg",
    "wx",
    "growyournft",
    "reduxearth",
    "dicks",
    "neffers",
    "grawaii",
    "calvster",
    "labs",
    "bull",
    "wecan",
    "r2",
    "42o",
    "sixpm",
    "us",
    "china",
    "rich",
    "pwnage",
    "waxnbinance",
    "gs",
    "war",
    "ak",
    "immortals",
    "dl",
    "stockx",
    "mafia",
    "myd",
    "ebay",
    "item",
    "ax",
    "city",
    "fun",
    "fomocity",
    "usa",
    "atomic",
    "stash",
    "adex",
    "nfl",
    "volt",
    "liquiid",
    "nftree",
    "org",
    "popmart",
    "oso",
    "worlds",
    "taco",
    "g33k",
    "4",
    "bluedac",
    "j",
    "meta",
    "gratitude",
    "coinex",
    "waxobinance",
    "ultrarare",
    "sacredleaf",
    "fuck",
    "lh",
    "nifty",
    "alusia",
    "inc",
    "art",
    "pos",
    "brpg",
    "binance",
    "atomichub",
    "dust",
    "gift",
    "bank",
    "eosn",
    "cocacola",
    "chain",
    "theunity",
    "bid",
    "nftg",
    "satoshi",
    "star",
    "42",
    "im",
    "coinbase",
    "skullz",
    "gamestop",
    "martia",
    "rio",
    "crt",
    "cards",
    "waxlord",
    "funimation",
    "bloc",
    "web",
    "3",
    "eastern",
    "eu",
    "leap",
    "xp",
    "oig",
    "tt",
    "moonie",
    "flex",
    "fam",
    "waxbinance",
    "itachi",
    "heisenberg",
    "gucci",
    "dracodice",
    "kard",
    "tld",
    "uplifters",
    "gameboy",
    "facebook",
    "x",
    "intel",
    "community",
    "burn",
    "farm",
    "drops",
    "bitstamp",
    "i",
    "p",
    "nimoy",
    "hi",
    "band",
    "drgn",
    "tww",
    "co",
    "liq",
    "xyz",
    "land",
    "pirates",
    "pink",
    "uplift",
    "steam",
    "dab",
    "gif",
    "max",
    "droppp",
    "tw",
    "greymass",
    "novo",
    "dick",
    "wtokens",
    "sus",
    "afterland",
    "hotwheels",
    "luminayanft",
    "cabal",
    "blaze",
    "mt",
    "card",
    "onessus",
    "coronavirus",
    "yoda",
    "ing",
    "bpg",
    "dilla",
    "lyl",
    "goldar",
    "info",
    "com",
    "nftgamertv",
    "pop",
    "qtt",
    "shatner",
    "karma",
    "shockshouse",
    "nerd",
    "facings",
    "topps",
    "creek",
    "huobiwaxdep",
    "mrderkin",
    "century",
    "sshiphop",
    "me",
    "json",
    "r",
    "cn",
    "bihut",
    "smartlock",
    "es",
    "kogs",
    "tokenwave",
    "nfty",
    "free",
    "usdt",
    "relic",
    "cheesman",
    "ow3ns",
    "gr",
    "z",
    "ly",
    "fanfavez",
    "pp",
    "cock",
    "marvel",
    "y",
    "idle",
    "invyverse",
    "freeguy",
    "qq",
    "p2e",
    "it",
    "zenft",
    "133",
    "kendra",
    "ion",
    "bsb",
    "simba",
    "hazl",
    "reaper",
    "null",
    "lego",
    "hero",
    "decide",
    "tribebooks",
    "xxx",
    "world",
    "derkin",
    "ok",
    "ca",
    "bitverse",
    "diege",
    "canna",
    "dp",
    "f",
    "nlp",
    "tribe",
    "sw",
    "activision",
    "io",
    "ers",
    "marketplace",
    "galaxy",
    "darkpinup",
    "illuminati",
    "za",
    "joelcomm",
    "gov",
    "name",
    "deadmau5",
    "waxclaim",
    "nug",
    "cash",
    "live",
    "hits",
    "ascendance",
    "jqker",
    "freak",
    "th",
    "now",
    "myk",
    "louis",
    "theuplift",
    "play",
    "res",
    "b1",
    "steak",
    "legendart",
    "miner",
    "works",
    "gateio",
    "life",
    "n",
    "dapplica",
    "antelope",
    "space",
    "dank",
    "stamps",
    "princessb",
    "nike",
    "kucoin",
    "evildead",
    "puzzlr",
    "cow",
    "fanfavz",
    "army",
    "comix",
    "mint",
    "steph",
    "nftdrops",
    "fi",
    "sanyika",
    "realm",
    "sex",
    "nfts",
    "shop",
    "omc",
    "trevor",
    "shn",
    "shyn",
    "huobi",
    "biz",
    "1",
    "phoenix",
    "go",
    "moneyrjr",
    "jigsaw",
    "mail",
    "box",
    "cert",
    "ghost",
    "jobs",
    "en",
    "includenull",
    "team",
    "bludac",
    "fr",
    "cpu4",
    "ar",
    "artwork",
    "waxcraft",
    "tornado",
    "robotech",
    "coke",
    "imtoken",
    "stache",
    "koq",
    "king",
    "weed",
    "mtg",
    "reptile",
    "token",
    "group",
    "gods",
    "boid",
    "faded",
    "ram",
    "games",
    "sony",
    "decluttr",
    "niftydrops",
    "sh",
    "mi",
    "tribalbooks",
    "feet",
    "kylelozansd",
    "moonboys",
    "terraracers",
    "no",
    "ed",
    "studio",
    "limbo",
    "dac",
    "gang",
    "thedac",
    "comics",
    "ender",
    "bitteex",
    "zen",
    "hive",
    "mud",
    "a",
    "marsmadness",
    "beeworlds",
    "bithumbwaxr",
    "nftrippy",
    "gem",
    "smc",
    "eq",
    "charm",
    "ez",
    "hk",
    "metaforce",
    "catinthehat",
    "tc",
    "metadac",
    "meow",
    "microsoft",
    "ninja",
    "ea",
    "cpu",
    "pepe",
    "ultracomics",
    "tools",
    "parzival",
    "ufo",
    "u",
    "3d",
    "waxonbiance",
    "bet",
    "mj",
    "upxworld",
    "tokenhead",
    "bandroyalty",
    "geek",
    "nsd",
    "ampd",
    "clan",
    "martin",
    "disney",
    "moon",
    "itgame",
    "divi",
    "v",
    "cunt",
    "yoshi",
    "51",
    "aa",
    "up",
    "eskimo",
    "yandere",
    "gt",
    "lgndmusic",
    "hodlgod",
    "metacarbon",
    "goldfish",
    "bj",
    "nyan",
    "blokchainme",
    "pandora",
    "rland",
    "fracs",
    "animoca",
    "carrier",
    "defactor",
    "race",
    "neon",
    "island",
    "donate",
    "dna",
    "gumi",
    "eos",
    "k",
    "yoshidrops",
    "finance",
    "boom",
    "waxio",
    "sean",
    "school",
    "gg",
    "vox",
    "rd",
    "godzilla",
    "mbl",
    "at",
    "funko",
    "g",
    "linkedin",
    "boss",
    "fc",
    "oid",
    "kyfbot",
    "stby",
    "tube",
    "vk",
    "mintworld",
    "sol",
    "ass",
    "b",
    "hottopic",
    "cg",
    "saw",
    "nifties",
    "isaiah",
    "nate",
    "apple",
    "op",
    "s",
    "hodl",
    "zeddy",
    "theolddude",
    "dice",
    "tag",
    "octalmage",
    "xd",
    "cxc",
    "mf",
    "rewards",
    "h",
    "hope",
    "council",
    "dome",
    "bestbuy",
    "digifinex",
    "sega",
    "freakshow",
    "pickle",
    "shopkins",
    "tx",
    "t",
    "choyna",
    "ladz",
    "crypto",
    "hub",
    "degen",
    "brobros42o",
    "writer",
    "atom",
    "ava",
    "krown",
    "se",
    "fan",
    "dragonballz",
    "kong",
    "drizzt",
    "clock",
    "bitfinex",
    "waxonbinace",
    "ex",
    "pwn",
    "11",
    "cait",
    "col",
    "gold",
    "hydro",
    "bot",
    "cpus",
    "start",
    "chrono",
    "wa",
    "pack",
    "rfox",
    "mars",
    "badcrypto",
    "eden",
    "nova",
    "quest",
    "pd",
    "cherrycoin",
    "blocdraig",
    "nftorigins",
    "wrc",
    "love",
    "starwars",
    "bro",
    "waxonbinanc",
    "kid",
    "wizardx",
    "ryles",
    "jedi",
    "waltdisney",
    "supergoal",
    "film",
    "br",
    "umbranox",
    "tnft",
    "tps",
    "cap",
    "yeah",
    "set",
    "5g",
    "cocks",
    "ai",
    "waxtown",
    "justaguy",
    "gidle",
    "backed",
    "thegazers",
    "squad",
    "puft",
    "rep",
    "tarot",
    "metaverse",
    "morevgo",
    "pro",
    "lgnd",
    "kb",
    "lettos",
    "dao",
    "cunts",
    "mynifties",
    "myth",
    "heroes",
    "nftnt",
    "louie",
    "shit",
    "nftgamer",
    "uw",
    "ultracomix",
    "twitter",
    "an",
    "gemini",
    "paul",
    "wat",
    "magic",
    "onmars",
    "marscards",
    "sea",
    "korea",
    "pokemon",
    "nodo42",
    "yoshiradio",
    "upliftworld",
    "cafe",
    "cworld",
    "japan",
    "rental",
    "amazon",
    "cw",
    "sando",
    "hasbro",
    "btc",
    "o",
    "rplanet",
    "efc",
    "sirius",
    "hasbronft",
    "game",
    "nefty",
    "tiger",
    "fish",
    "to",
    "dm",
    "mix",
    "gm",
    "tresequis",
    "weezer",
    "pinup",
    "pk",
    "tibs",
    "iplr",
    "ka4",
    "drop",
    "one",
    "mirrorpool",
    "cx",
    "unlinked",
    "ftw",
    "w",
    "rpg",
    "imt",
    "faction",
    "e",
    "lou",
    "owens",
    "kr",
    "ru",
    "sudo",
    "mo",
    "tyranno",
    "alibaba",
    "honeycomb",
    "usmint",
    "atari",
    "motel",
    "degree",
    "c",
    "dogecoin",
    "nba",
    "wiz",
    "legend",
    "cherrycoins",
    "google",
    "konami",
    "eosd",
    "2",
    "apiary",
    "elvar",
    "cc",
    "vip",
    "spongebob",
    "tp",
    "1stmint",
    "gene",
    "staff",
    "13",
    "dmerch",
    "dropp",
    "bitterx",
    "dc",
    "yoshibucks",
    "usd",
    "earnbet",
    "nah",
    "car",
    "store",
    "balenciaga",
    "bh",
    "ch",
    "meme",
    "link",
    "champs",
    "clt",
    "lgndart",
    "federation",
    "wizard",
    "bb",
    "gmail",
    "nb",
    "richie",
    "voice",
    "orng",
    "1up",
    "kribs",
    "test",
    "casino",
    "1m",
    "af",
    "media",
    "gameset",
    "pgl",
    "ux",
    "img",
    "grow",
    "crew",
    "zombie",
    "club",
    "bitrex",
    "bitcoin",
    "mios",
    "dragonball",
    "tv",
    "zos",
    "ibc",
    "mmc",
    "mvp",
    "adidas",
    "pixygon",
    "goldenhills",
    "dlt",
    "names",
    "longhair",
    "ark",
    "head",
    "kickback",
    "netflix",
    "defi",
    "tyrano",
    "disneynft",
    "utd",
    "mlb",
    "f1",
    "ape",
    "vr",
    "inuk",
    "leaf",
    "hemp",
    "dex",
    "architect",
    "dirty",
    "network",
    "dwarfisland",
    "sweden",
    "dec",
    "van",
    "in",
    "tech",
    "q",
    "upx",
    "lord",
    "warsaken",
    "upliftart",
    "cv",
    "lefthouse",
    "bacca",
    "immersys",
    "hunter",
    "uk",
    "lambo",
    "scam",
}

extra_specials = {"wam", "waa", "wax"}
system_accounts = {
    "eosio.bpay",
    "eosio.msig",
    "eosio.names",
    "eosio.ram",
    "eosio.ramfee",
    "eosio.saving",
    "eosio.stake",
    "eosio.token",
    "eosio.vpay",
    "eosio.rex",
}


def is_valid_wax_address(addr: str, valid_specials: list | set = None) -> bool:
    """Returns whether the provided string is a valid wax address.
    An optional valid_specials allows injecting an up to date list of special wax addresses, otherwise the stored list will be used.
    It is recommended to use get_special_wax_address_list to provide this function with an up to date list."""
    if len(addr) > 12:
        return False
    match = re.match(r"[a-z1-5\.]{1,12}", addr, flags=re.I)
    if match is None:
        return False
    if len(match.group()) == 12:
        return True
    if match.group() in system_accounts:
        return True
    base = re.search(r"\.?(?P<a>[a-z1-5]+$)", match.group(), flags=re.I)
    if base is None:
        return False
    valid_specials = valid_specials or special_wax_addresses
    return base.group("a") in valid_specials | extra_specials


def parse_wax_address(text: str, valid_specials: list | set = None) -> str:
    """Returns the first valid wax address in a provided string, if there is one. To match, an address must be surrounded by whitespace.
    Returns None on no match.
    An optional valid_specials allows injecting an up to date list of special wax addresses, otherwise the stored list will be used.
    It is recommended to use get_special_wax_address_list to provide this function with an up to date list."""
    for item in text.split():
        if is_valid_wax_address(item, valid_specials=valid_specials):
            return item
    return None


def get_special_wax_address_list() -> set[str]:
    """Attempts to fetch and return the full list of special wax addresses from eosauthority's api's records of auctions.
    Failing that, it returns a hardcoded list as a fallback. This method is syncronous, using requests."""
    page = 1
    specials = special_wax_addresses
    while True:
        with requests.get(f"{QUERY_SPECIALS_URL}{page}&sort=rank&type=sold") as resp:
            if int(resp.status_code) != 200:
                specials.update(special_wax_addresses)
                print(
                    f"Unable to update special wax addresses at the moment, using stored list. Received status {resp.status}"
                )
                return specials
            try:
                respo = resp.json()
                response = respo["sold"]["data"]
            except KeyError:
                print(
                    "Key error attempting to decode data in get_special_wax_address_list"
                )
                return specials
        specials.update([x["newname"] for x in response])
        if len(response) < 1000:
            break
        page += 1
    return specials


async def async_get_special_wax_address_list(
    session: aiohttp.ClientSession,
) -> set[str]:
    """Attempts to fetch and return the full list of special wax addresses from eosauthority's api's records of auctions.
    Failing that, it returns a hardcoded list as of as a fallback. This method is asyncronous, using aiohttp."""
    if session.closed:
        return
    page = 1
    specials = special_wax_addresses
    while True:
        async with session.get(
            f"{QUERY_SPECIALS_URL}{page}&sort=rank&type=sold"
        ) as resp:
            if int(resp.status) != 200:
                specials.update(special_wax_addresses)
                print(
                    f"Unable to update special wax addresses at the moment, using stored list. Received status {resp.status}"
                )
                return specials
            try:
                respo = await resp.json()
                response = respo["sold"]["data"]
            except KeyError:
                print(
                    "Key error attempting to decode data in get_special_wax_address_list"
                )
                return specials
        specials.update([x["newname"] for x in response])
        if len(response < 1000):
            break
        page += 1
    return specials
