import re
import requests
from typing import Optional

import aiohttp

from utils.exceptions import UnableToCompleteRequestedAction
from utils.settings import QUERY_SPECIALS_URL, ENV

fallback_file_name: str = "fallback_special_wax_addresses.txt"
_fallback_special_wax_addresses: set[str] = set()


def fallback_special_wax_addresses(
    filename: str = fallback_file_name,
) -> set[str]:
    """This loads a fallback list, last updated _::_October 17 2022_::_.
    Run only ones intentionally to avoid repeated loading of an unchanging list."""
    global _fallback_special_wax_addresses
    if not _fallback_special_wax_addresses:
        with open(f"res/{filename}", encoding="utf-8", errors="replace") as file:
            _fallback_special_wax_addresses = set(file.read().splitlines())
    return _fallback_special_wax_addresses


def _update_fallback_special_wax_addresses(filename: str = fallback_file_name) -> bool:
    """This can not be run in production.
    This will overwrite the existing fallback list with an up to date one.
    It also edits this file's code directly to update the date in the above function's docstring.
    Returns whether or not it updated the list."""
    if ENV.lower() == "prod":
        raise AssertionError("This can not be run in production.")
    updated_list = list(get_special_wax_address_list())
    if len(updated_list) < len(fallback_special_wax_addresses()):
        return False
    with open(f"res/{fallback_file_name}", "w+", encoding="utf-8") as file:
        file.write("\n".join(line for line in updated_list))

    # Edit this file to update the docstring for fallback_special_wax_addresses
    import datetime
    import re

    date = datetime.datetime.now()
    fmt = "%B %d %Y"
    str_date = date.strftime(fmt)
    with open(__file__, "r") as f:
        content = f.read()
    new_content = re.sub(r"_::_.*_::_", f"_::_{str_date}_::_", content, count=1)
    with open(__file__, "w") as f:
        f.write(new_content)
    return True


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


def is_valid_wax_address(addr: str, valid_specials: Optional[set[str]] = None) -> bool:
    """Returns whether the provided string is a valid wax address. An optional
    valid_specials allows injecting an up to date list of special wax addresses,
     otherwise the stored list will be used. It is recommended to use
     get_special_wax_address_list to provide this function with an up to date list."""
    if len(addr) > 12:
        return False
    match = re.match(r"[a-z1-5\.]{1,12}", addr, flags=re.I)
    if match is None:
        return False
    if match.group() != addr:
        return False
    if len(match.group()) == 12:
        return True
    if match.group() in system_accounts:
        return True
    base = re.search(r"\.?(?P<a>[a-z1-5]+$)", match.group(), flags=re.I)
    if base is None:
        return False
    valid_specials = valid_specials or fallback_special_wax_addresses()
    return base.group("a") in valid_specials | extra_specials


def parse_wax_address(
    text: str, valid_specials: Optional[set[str]] = None
) -> Optional[str]:
    """Returns the first valid wax address in a provided string, if there is one.
    To match, an address must be surrounded by whitespace. Returns None on no match.
    An optional valid_specials allows injecting an up to date list of special wax
    addresses, otherwise the stored list will be used. It is recommended to use
    get_special_wax_address_list to provide this function with an up to date list."""
    for item in text.split():
        if is_valid_wax_address(item, valid_specials=valid_specials):
            return item
    return None


def get_special_wax_address_list() -> set[str]:
    """Attempts to fetch and return the full list of special wax addresses from
    eosauthority's api's records of auctions. Failing that, it returns a hardcoded
    list as a fallback. This method is syncronous, using requests."""
    page = 1
    specials = fallback_special_wax_addresses()
    while True:
        with requests.get(f"{QUERY_SPECIALS_URL}{page}&sort=rank&type=sold") as resp:
            if int(resp.status_code) != 200:
                print(
                    f"Unable to update special wax addresses at the moment, "
                    f" using stored list. Received status {resp.status_code}"
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
    """Attempts to fetch and return the full list of special wax addresses from
    eosauthority's api's records of auctions. Failing that, it returns a hardcoded
    list as of as a fallback. This method is asyncronous, using aiohttp."""
    if session.closed:
        raise UnableToCompleteRequestedAction
    page = 1
    specials = fallback_special_wax_addresses()
    while True:
        async with session.get(
            f"{QUERY_SPECIALS_URL}{page}&sort=rank&type=sold"
        ) as resp:
            if int(resp.status) != 200:
                print(
                    f"Unable to update special wax addresses at the moment, "
                    f"using stored list. Received status {resp.status}"
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
        if len(response) < 1000:
            break
        page += 1
    return specials
