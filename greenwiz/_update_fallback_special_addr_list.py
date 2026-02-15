import asyncio

import aiohttp


async def update_specials():
    from wax_chain.wax_addresses import async_get_special_wax_address_list

    session = aiohttp.ClientSession()
    specials = await async_get_special_wax_address_list(session)
    print(specials)
    print("======")
    for special in specials:
        print(special)


if __name__ == "__main__":
    asyncio.run(update_specials())
