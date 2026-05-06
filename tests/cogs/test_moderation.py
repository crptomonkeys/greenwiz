import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "greenwiz"))

from cogs.moderation import (  # noqa: E402
    CM_INTRO_CHANNEL_ID,
    CM_NEW_USER_WATCH_MESSAGE_LIMIT,
    CM_NEW_USER_WARNING,
    Moderation,
    has_assigned_roles,
    is_link_only_message,
)
from utils.settings import CM_GUID  # noqa: E402


class FakeRole:
    def __init__(self, role_id: int) -> None:
        self.id = role_id


class FakeGuild:
    def __init__(self, guild_id: int) -> None:
        self.id = guild_id
        self.default_role = FakeRole(guild_id)

    def get_channel(self, _channel_id):
        return None


class FakeMember:
    def __init__(
        self, user_id: int, *, guild, bot: bool = False, roles=None
    ) -> None:
        self.id = user_id
        self.guild = guild
        self.bot = bot
        self.roles = roles if roles is not None else [FakeRole(guild.id)]
        self.mention = f"<@{user_id}>"

    def __str__(self) -> str:
        return f"FakeMember({self.id})"


class FakeChannel:
    def __init__(self) -> None:
        self.send = AsyncMock()


class FakeMessage:
    def __init__(self, *, author, guild, channel, content="", attachments=None) -> None:
        self.author = author
        self.guild = guild
        self.channel = channel
        self.content = content
        self.attachments = attachments or []
        self.mentions = []
        self.jump_url = "https://discord.test/messages/1"
        self.delete = AsyncMock()


class FakeNewMemberStorage:
    def __init__(self) -> None:
        self.counts: dict[int, int] = {}
        self.get_count_calls = 0

    async def watch_new_member_messages(self, user) -> None:
        self.counts[user.id] = 0

    async def increment_watched_new_member_messages(self, user) -> int:
        self.counts[user.id] += 1
        return self.counts[user.id]

    async def get_watched_new_member_message_count(self, user) -> int | None:
        self.get_count_calls += 1
        return self.counts.get(user.id)

    async def clear_watched_new_member_messages(self, user) -> None:
        self.counts.pop(user.id, None)


def make_moderation_cog(guild, storage: FakeNewMemberStorage) -> Moderation:
    bot = SimpleNamespace(
        session=None,
        storage={guild: storage},
        log=lambda *_args, **_kwargs: None,
        MAX_MASS_PING_AMOUNT=30,
    )
    return Moderation(bot)


def test_is_link_only_message_detects_bare_and_discord_wrapped_links() -> None:
    assert is_link_only_message("https://example.com")
    assert is_link_only_message("<https://example.com/path>")
    assert is_link_only_message("www.example.com")
    assert is_link_only_message("https://example.com https://example.org")


def test_is_link_only_message_rejects_intro_text_with_link() -> None:
    assert not is_link_only_message("")
    assert not is_link_only_message("hi https://example.com")
    assert not is_link_only_message("hello everyone")


def test_has_assigned_roles_ignores_everyone_role() -> None:
    guild = FakeGuild(CM_GUID)

    assert not has_assigned_roles(FakeMember(1, guild=guild))
    assert has_assigned_roles(
        FakeMember(1, guild=guild, roles=[FakeRole(CM_GUID), FakeRole(123)])
    )


def test_new_cm_member_link_message_is_deleted_while_watched() -> None:
    async def run_test() -> None:
        guild = FakeGuild(CM_GUID)
        channel = FakeChannel()
        member = FakeMember(123, guild=guild)
        message = FakeMessage(
            author=member,
            guild=guild,
            channel=channel,
            content="https://example.com",
        )
        storage = FakeNewMemberStorage()
        cog = make_moderation_cog(guild, storage)

        await cog.on_member_join(member)
        await cog.on_message(message)

        message.delete.assert_awaited_once()
        channel.send.assert_awaited_once_with(f"{member.mention} {CM_NEW_USER_WARNING}")
        assert storage.counts[member.id] == 1

    asyncio.run(run_test())


def test_new_cm_member_attachment_only_message_is_deleted_while_watched() -> None:
    async def run_test() -> None:
        guild = FakeGuild(CM_GUID)
        channel = FakeChannel()
        member = FakeMember(456, guild=guild)
        message = FakeMessage(
            author=member,
            guild=guild,
            channel=channel,
            attachments=[SimpleNamespace(url="https://cdn.discord.test/file.png")],
        )
        storage = FakeNewMemberStorage()
        cog = make_moderation_cog(guild, storage)

        await cog.on_member_join(member)
        await cog.on_message(message)

        message.delete.assert_awaited_once()
        channel.send.assert_awaited_once()
        assert f"<#{CM_INTRO_CHANNEL_ID}>" in channel.send.await_args.args[0]

    asyncio.run(run_test())


def test_new_cm_member_intro_text_is_not_deleted_while_watched() -> None:
    async def run_test() -> None:
        guild = FakeGuild(CM_GUID)
        channel = FakeChannel()
        member = FakeMember(789, guild=guild)
        message = FakeMessage(
            author=member,
            guild=guild,
            channel=channel,
            content="Hi, I'm new here and like monkeys.",
        )
        storage = FakeNewMemberStorage()
        cog = make_moderation_cog(guild, storage)

        await cog.on_member_join(member)
        await cog.on_message(message)

        message.delete.assert_not_awaited()
        channel.send.assert_not_awaited()
        assert storage.counts[member.id] == 1

    asyncio.run(run_test())


def test_new_cm_member_is_removed_after_tenth_message() -> None:
    async def run_test() -> None:
        guild = FakeGuild(CM_GUID)
        channel = FakeChannel()
        member = FakeMember(790, guild=guild)
        storage = FakeNewMemberStorage()
        cog = make_moderation_cog(guild, storage)

        await cog.on_member_join(member)
        for _ in range(CM_NEW_USER_WATCH_MESSAGE_LIMIT):
            await cog.on_message(
                FakeMessage(
                    author=member,
                    guild=guild,
                    channel=channel,
                    content="Hi, I'm still chatting.",
                )
            )

        assert member.id not in storage.counts

    asyncio.run(run_test())


def test_new_cm_member_is_removed_when_role_is_assigned() -> None:
    async def run_test() -> None:
        guild = FakeGuild(CM_GUID)
        member = FakeMember(791, guild=guild)
        storage = FakeNewMemberStorage()
        cog = make_moderation_cog(guild, storage)

        await cog.on_member_join(member)
        member.roles.append(FakeRole(123))
        await cog.on_member_update(member, member)

        assert member.id not in storage.counts

    asyncio.run(run_test())


def test_cm_member_with_role_skips_new_member_redis_check_on_message() -> None:
    async def run_test() -> None:
        guild = FakeGuild(CM_GUID)
        channel = FakeChannel()
        member = FakeMember(
            792, guild=guild, roles=[FakeRole(CM_GUID), FakeRole(123)]
        )
        storage = FakeNewMemberStorage()
        cog = make_moderation_cog(guild, storage)

        await cog.on_message(
            FakeMessage(
                author=member,
                guild=guild,
                channel=channel,
                content="https://example.com",
            )
        )

        assert storage.get_count_calls == 0

    asyncio.run(run_test())
