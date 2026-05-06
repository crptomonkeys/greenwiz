import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "greenwiz"))

from utils.storage import StorageManager  # noqa: E402


class FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, int]] = {}

    async def hset(self, key: str, field: str, value: int) -> int:
        self.hashes.setdefault(key, {})[field] = value
        return 1

    async def hincrby(self, key: str, field: str, amount: int) -> int:
        self.hashes.setdefault(key, {})[field] = self.hashes.setdefault(key, {}).get(
            field, 0
        ) + amount
        return self.hashes[key][field]

    async def hget(self, key: str, field: str) -> int | None:
        return self.hashes.get(key, {}).get(field)

    async def hdel(self, key: str, field: str) -> int:
        if key not in self.hashes or field not in self.hashes[key]:
            return 0
        del self.hashes[key][field]
        return 1


def test_new_member_message_watch_is_persisted_and_removed() -> None:
    async def run_test() -> None:
        guild = SimpleNamespace(id=1234)
        user = SimpleNamespace(id=5678)
        storage = StorageManager(SimpleNamespace(redis=FakeRedis()), guild=guild)

        await storage.watch_new_member_messages(user)
        assert await storage.get_watched_new_member_message_count(user) == 0

        assert await storage.increment_watched_new_member_messages(user) == 1
        assert await storage.get_watched_new_member_message_count(user) == 1

        await storage.clear_watched_new_member_messages(user)
        assert await storage.get_watched_new_member_message_count(user) is None

    import asyncio

    asyncio.run(run_test())
