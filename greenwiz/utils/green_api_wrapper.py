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

    async def all_miners_for_cycle(self, cycle: int = None) -> list:
        assert cycle is not None, "Cycle is a required field."
        page = 1
        responses = 1000
        time = None
        users = dict()
        while responses >= 1000:
            resp = await self.miner(cycle=cycle, page=page)
            responses = resp["count"]
            if time is None:
                time = resp["last_update"]
            elif time != resp["last_update"]:
                # Start again
                time = resp["last_update"]
                page = 0
                users = dict()
            page += 1
            users.update({item["user"]: item for item in resp["data"]})

        blacklist = self.get_blacklist()
        miners = [i for i in users.values() if i["user"] not in blacklist]
        return sorted(miners, key=lambda x: x["rank"])

    async def miner(self, cycle: int = None, page: int = 1, user: str = None) -> dict:
        assert cycle is not None, "Cycle is a required field."
        if user is None:
            url = f"{self.url_base}/miner/{cycle}?page={page}"
        else:
            url = f"{self.url_base}/miner/{cycle}?page={page}&user={user}"
        return await self.get_resp(url)

    async def get_resp(self, url: str):
        resp = await self.session.get(url)
        resp.raise_for_status()
        js = await resp.json()
        if hasattr(js, "get") and js.get("error"):
            raise GreenApiException(js.get("error"))
        return js

    async def blacklist_add(self, address: str) -> dict:
        """Add a wax address to the blacklist"""
        if "<" in address or ">" in address or "!" in address or "@" in address:
            raise InvalidInput(f"{address} is not a valid wax address.")

        try:
            resp = await self.get_resp(
                f"{BLACKLIST_ADD}?code={BLACKLIST_AUTH_CODE}&wallet={address}"
            )
        except GreenApiException as e:
            return {"success": False, "exception": repr(e)}
        self.cache_updated = 0
        return resp

    async def blacklist_remove(self, address: str) -> dict:
        """Remove an address from the blacklist"""
        if "<" in address or ">" in address or "!" in address or "@" in address:
            raise InvalidInput(f"{address} is not a valid wax address.")

        try:
            resp = await self.get_resp(
                f"{BLACKLIST_REMOVE}?code={BLACKLIST_AUTH_CODE}&wallet={address}"
            )
        except GreenApiException as e:
            return {"success": False, "exception": repr(e)}
        self.cache_updated = 0
        return resp

    async def get_blacklist(self, force: bool = False, expiry: float = 30.0) -> set:
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
