import discord


async def send(
    target: discord.abc.Messageable,
    message: str,
    page_length=1990,
    pre_text="",
    post_text="",
) -> None:
    buffer = len(pre_text) + len(post_text)
    page_length -= buffer
    cursor = 0
    while cursor < len(message):
        page = f"{pre_text}{message[cursor:cursor+page_length]}{post_text}"
        await target.send(page)
        cursor += page_length
    return
