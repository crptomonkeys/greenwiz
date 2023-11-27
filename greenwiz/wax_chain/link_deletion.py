from datetime import datetime, timedelta

from utils.exceptions import InvalidResponse
from utils.settings import DEFAULT_WAX_COLLECTION
from wax_chain.collection_config import get_collection_info


async def delete_old_links(
    ctx, wax_con, links_to_delete: list[str], collection=DEFAULT_WAX_COLLECTION
) -> tuple[str, str]:
    """Delete the specified claim links."""
    links: list[int] = [int(i) for i in links_to_delete]
    result, tx_id = await wax_con.cancel_claimlinks(links, collection=collection)
    return str(result), str(tx_id)


async def find_old_links_to_delete(
    ctx,
    wax_con,
    collection: str = DEFAULT_WAX_COLLECTION,
    days_old: int = 91,
    max_num=50,
) -> list[str]:
    """Fetch a list of old links to delete for the specified collection.
    State 1: unclaimed
    State 2: ???
    State 3: claimed"""
    now: datetime = datetime.now()
    earliest_still_valid = now - timedelta(days=days_old)
    endpoint: str = "https://wax.eosusa.io/atomictools/v1/links"
    page: int = 1
    drop_ac = get_collection_info(collection).drop_ac
    params: str = (
        f"limit=100&order=asc&page={page}&sort=created&creator={drop_ac}&state=1"
    )
    async with wax_con.session.get(f"{endpoint}?{params}") as resp:
        content = await resp.json()
    if not content["success"]:
        raise InvalidResponse(f"{content}")
    responses: list[str] = []
    for i in content["data"]:
        if i["state"] != 1:
            continue
        if i["creator"] != drop_ac:
            ctx.bot.log(f"creator {i['creator']=} is not drop_ac {drop_ac=}", "DBUG")
            continue
        try:
            created_at = datetime.fromtimestamp(int(i["created_at_time"]) // 1000)
        except ValueError:
            raise InvalidResponse(
                f"{i['created_at_time']} is not a valid timestamp: atomicassets API returned garbage."
            )
        if created_at > earliest_still_valid:
            # ctx.bot.log(
            #    f"Link {i['link_id']} created at {created_at} is newer than {earliest_still_valid}, skipping.",
            #    "DBUG",
            # )
            continue
        responses.append(i["link_id"])
        if len(responses) >= max_num:
            return responses
    return responses
