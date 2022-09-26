import aiohttp

price_api = "https://web-api.coinmarketcap.com/v1/cryptocurrency/price-performance-stats/latest?id="
wax_id = 2300
ban_id = 4704


async def get_coin_price(session: aiohttp.ClientSession, asset_id: int) -> float:
    """Use session to fetch the price of the specified asset from coinmarketcap."""
    async with session.get(price_api + str(asset_id)) as resp:
        if resp.status != 200:
            raise aiohttp.ClientConnectionError(resp.status)
        raw = await resp.json()
    return float(
        raw["data"][str(asset_id)]["periods"]["all_time"]["quote"]["USD"]["close"]
    )


async def get_wax_price(session: aiohttp.ClientSession) -> float:
    """Fetches the wax_chain price in USD"""
    return await get_coin_price(session, wax_id)


async def get_ban_price(session: aiohttp.ClientSession) -> float:
    """Fetches the banano price in USD"""
    return await get_coin_price(session, ban_id)
