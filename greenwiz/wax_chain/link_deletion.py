import asyncio


async def delete_old_links(ctx, wax_con, links_to_delete: list[str]):
    deleted = 0
    for link_id in links_to_delete:
        result, tx_id = await wax_con.cancel_claimlink(int(link_id))
        await ctx.send(f"Deleted claimlink {link_id}. Transaction id: {tx_id}.")
        deleted += 1
        await asyncio.sleep(1)
    await ctx.send(f"Deleted {deleted} claimlinks.")
