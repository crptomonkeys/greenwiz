from typing import Set, Any, Optional

import aiohttp.web_exceptions

from utils.exceptions import InvalidInput
from utils.settings import (
    BLACKLIST_ADD,
    BLACKLIST_REMOVE,
    BLACKLIST_GET,
    BLACKLIST_AUTH_CODE,
    CMSTATS_SERVER,
)
from utils.util import utcnow


class GreenApiException(Exception):
    def __repr__(self):
        return self.args[0]

    pass


class GreenApi:
    def __init__(self, session, server=CMSTATS_SERVER):
        self.session = session
        self.limit = 1000
        self.server = server
        self.url_base = f"http://{self.server}"
        self.cached_blacklist = set()
        self.cache_updated = 0

    async def all_miners_for_cycle(
        self, cycle: Optional[int] = None
    ) -> list[dict[str, Any]]:
        assert cycle is not None, "Cycle is a required field."
        page: int = 1
        responses: int = 1000
        time: str = ""
        users: dict[str, Any] = dict()
        while responses >= 1000:
            resp = await self.miner(cycle=cycle, page=page)
            responses = resp["count"]
            if time == "":
                time = resp["last_update"]
            elif time != resp["last_update"]:
                # Start again
                time = resp["last_update"]
                page = 0
                users = dict()
            page += 1
            users.update({item["user"]: item for item in resp["data"]})

        blacklist = await self.get_blacklist()
        miners = [i for i in users.values() if i["user"] not in blacklist]
        result_list: list[dict[str, Any]] = sorted(miners, key=lambda x: x["rank"])  # type: ignore[no-any-return]
        return result_list

    async def miner(
        self, cycle: Optional[int] = None, page: int = 1, user: str = ""
    ) -> dict[str, Any]:
        assert cycle is not None, "Cycle is a required field."
        if user == "":
            url = f"{self.url_base}/miner/{cycle}?page={page}"
        else:
            url = f"{self.url_base}/miner/{cycle}?page={page}&user={user}"
        resp: dict[str, Any] = await self.get_resp(url)
        return resp

    async def get_resp(self, url: str) -> Any:
        resp = await self.session.get(url)
        resp.raise_for_status()
        js = await resp.json()
        if hasattr(js, "get") and js.get("error"):
            raise GreenApiException(js.get("error"))
        return js

    async def blacklist_add(self, address: str) -> dict[str, Any]:
        """Add a wax address to the blacklist"""
        if "<" in address or ">" in address or "!" in address or "@" in address:
            raise InvalidInput(f"{address} is not a valid wax address.")

        try:
            resp: dict[str, Any] = await self.get_resp(
                f"{BLACKLIST_ADD}?code={BLACKLIST_AUTH_CODE}&wallet={address}"
            )
        except GreenApiException as e:
            return {"success": False, "exception": repr(e)}
        self.cache_updated = 0
        return resp

    async def blacklist_remove(self, address: str) -> dict[str, Any]:
        """Remove an address from the blacklist"""
        if "<" in address or ">" in address or "!" in address or "@" in address:
            raise InvalidInput(f"{address} is not a valid wax address.")

        try:
            resp: dict[str, Any] = await self.get_resp(
                f"{BLACKLIST_REMOVE}?code={BLACKLIST_AUTH_CODE}&wallet={address}"
            )
        except GreenApiException as e:
            return {"success": False, "exception": repr(e)}
        self.cache_updated = 0
        return resp

    async def get_blacklist(
        self, force: bool = False, expiry: float = 30.0
    ) -> Set[str]:
        """Fetch the blacklist from source. Cache for a minute, but cache is rendered out of date by a call to
        blacklist_add or blacklist_remove."""

        if force or utcnow().timestamp() - self.cache_updated > expiry:
            # Refresh cached_blacklist
            try:
                results = await self.get_resp(BLACKLIST_GET)

                if results is not None and len(results) > 0:
                    self.cached_blacklist = set(
                        [i["wallet"].replace(" ", "") for i in results]
                    )
                self.cache_updated = utcnow().timestamp()
            except aiohttp.web_exceptions.HTTPError as e:
                print(
                    f"Encountered an error attempting to fetch the monKeyconnect blacklist, returning cached "
                    f"blacklist. {e}"
                )

        return self.cached_blacklist
