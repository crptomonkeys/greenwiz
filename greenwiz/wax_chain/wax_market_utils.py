from math import ceil

import aiohttp

from utils.util import log

base_atomic_api = "https://wax.api.atomicassets.io/"
wax_chain_api = "https://api.waxsweden.org"
atomic_api = base_atomic_api + "atomicassets/v1/"
market_api = base_atomic_api + "atomicmarket/v1/"


def ema(close, prev_close, num):
    """Updates an exponential moving average one step."""
    ema_weight = 2 / float(num + 1)
    return ((close - prev_close) * ema_weight) + prev_close


def fair_est(ema_: float, lowest_offer: float):
    """Attempts to calculate an estimate of fair price for a template id by taking the geometric mean of lowest
    offer and exponential moving average of recent sales."""
    if lowest_offer < 0:
        return ema_
    if lowest_offer <= ema_:
        return lowest_offer
    factor = 3
    regressed_average = (
        ema_
        + lowest_offer
        - ((ema_**factor) / 2 + lowest_offer**factor / 2) ** (1 / factor)
    )
    log(
        f"Regressed Average: {round(regressed_average)}, EMA: {round(ema_)}, lowest_offer: {round(lowest_offer)}",
        "DBUG",
    )
    return regressed_average


async def get_assets_from_template(
    template_id: int, owner: str, session: aiohttp.ClientSession
) -> [int]:
    """Helper function to get all assets of specified template id owned by specified account, or all from that
    account if template id is 0"""
    if template_id == 0:
        query = atomic_api + f"assets?owner={owner}"
    else:
        query = atomic_api + f"assets?owner={owner}&template_id={template_id}"
    async with session.get(query) as resp:
        response = (await resp.json())["data"]
    ids = [int(item["asset_id"]) for item in response]
    return ids


async def get_owners(template_id: int, session: aiohttp.ClientSession, num=1000):
    """
    Returns a tuple, the template id and a list of all the current owners of the card with that template id.
    """
    prep_list = []
    for i in range(1, ceil(num // 1000) + 2):
        params = {
            "limit": 1000,
            "sort": "updated",
            "order": "desc",
            "template_id": template_id,
            "page": i,
        }
        async with session.get(atomic_api + "assets", params=params) as response:
            json_obj = await response.json()
            if response.status == 429:
                log(
                    f"I've been rate limited by the wax_chain api at i = {i}. Waiting 3 seconds...",
                    "DBUG",
                )
                log(str(prep_list), "DBUG")
                return template_id, prep_list
            elif not json_obj["data"]:
                break  # This page doesn't exist
            else:
                prep_list += [i["owner"] for i in json_obj["data"]]
    return template_id, prep_list


async def get_sales(template_id: int, session: aiohttp.ClientSession):
    """Returns a list of past sale prices in WAX for the specified template_id"""
    params = {"symbol": "WAX", "template_id": template_id}
    async with session.get(market_api + "prices/sales", params=params) as response:
        json_obj = await response.json()
    data = json_obj["data"]
    return [int(item["price"]) / (10 ** item["token_precision"]) for item in data]


async def get_lowest_current_offer(template_id: int, session: aiohttp.ClientSession):
    """Returns the lowest current market offer in WAX for the specified template_id"""
    params = {
        "state": 1,
        "limit": 10,
        "template_id": template_id,
        "order": "asc",
        "sort": "price",
        "page": 1,
    }
    async with session.get(market_api + "sales", params=params) as response:
        json_obj = await response.json()
    if not json_obj.get("data", None):
        print(json_obj)
        return -1
    min_priced_item = json_obj["data"][0]
    for item in json_obj["data"]:
        if int(item["price"]["amount"]) < int(min_priced_item["price"]["amount"]):
            min_priced_item = item
    return int(min_priced_item["price"]["amount"]) / (
        10 ** int(min_priced_item["price"]["token_precision"])
    )


async def get_geometric_regressed_sale_price(
    template_id: int, session: aiohttp.ClientSession
):
    """Returns the exponential moving average of sales price based on recent sales for a given template id"""
    prices = await get_sales(template_id, session)
    num_data_points = len(prices)
    if num_data_points < 1:
        return -1
    if num_data_points < 2:
        return prices[0]
    prices.reverse()
    max_precision = 10
    ma = prices[0]
    for i in range(num_data_points):
        num_data_points = max_precision if i > max_precision else i
        ma = ema(prices[i], ma, num_data_points)
    return ma
