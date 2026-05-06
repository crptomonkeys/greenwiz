from typing import Set, Any, Optional, Union, Protocol

import aiohttp.web_exceptions

from utils.exceptions import InvalidInput
from utils.settings import (
    BLACKLIST_GET,
    AW_BLACKLIST,
    BLACKLIST_AUTH_CODE,
    AW_BLACKLIST_AUTH_KEY,
    CMSTATS_SERVER,
    DISCORD_USER_LIST_AUTH_CODE,
    MONKEYCONNECT_DISCORD_USER_LIST_WAX_GET,
)
from utils.util import utcnow


class GreenApiException(Exception):
    def __repr__(self):
        return self.args[0]

    pass


class ReprProtocol(Protocol):
    def __repr__(self) -> str: ...


class GreenApi:
    def __init__(self, session, server=CMSTATS_SERVER):
        self.session = session
        self.limit = 1000
        self.server = server
        self.url_base = f"http://{self.server}"
        self.cached_blacklist: Set[str] = set()
        self.cached_awblacklist: Set[str] = set()
        self.cached_monkeyconnect_wax_users: Set[str] = set()
        self.cached_monkeyconnect_wallet_to_discord_ids: dict[str, set[int]] = {}
        self.cache_updated = 0
        self.monkeyconnect_cache_updated = 0

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

    async def get_resp(
        self,
        url: str,
        headers: Optional[dict[str, str]] = None,
        data: Optional[Union[str, dict[str, str]]] = None,
        _type: str = "get",
    ) -> Any:
        if headers is None:
            headers = dict()
        if _type == "get":
            resp = await self.session.get(url, headers=headers)
        elif _type == "post":
            resp = await self.session.post(url, data=data, headers=headers)
        elif _type == "delete":
            resp = await self.session.delete(url, data=data, headers=headers)
        elif _type == "put":
            resp = await self.session.put(url, data=data, headers=headers)
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
                f"{BLACKLIST_GET}add?code={BLACKLIST_AUTH_CODE}&wallet={address}"
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
                f"{BLACKLIST_GET}remove?code={BLACKLIST_AUTH_CODE}&wallet={address}"
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
                self.cache_updated = int(utcnow().timestamp())
            except aiohttp.web_exceptions.HTTPError as e:
                print(
                    f"Encountered an error attempting to fetch the monKeyconnect blacklist, returning cached "
                    f"blacklist. {e}"
                )

        return self.cached_blacklist

    async def get_monkeyconnect_wallet_to_discord_ids(
        self, force: bool = False, expiry: float = 300.0
    ) -> dict[str, set[int]]:
        """Fetch monkeyconnect discord->wax mappings and return wallet->discord_ids."""
        if (
            not force
            and utcnow().timestamp() - self.monkeyconnect_cache_updated < expiry
        ):
            return self.cached_monkeyconnect_wallet_to_discord_ids

        if not DISCORD_USER_LIST_AUTH_CODE:
            print(
                "DISCORD_USER_LIST_AUTH_CODE is empty, returning cached monkeyconnect "
                "wax user list."
            )
            return self.cached_monkeyconnect_wallet_to_discord_ids

        url = f"{MONKEYCONNECT_DISCORD_USER_LIST_WAX_GET}{DISCORD_USER_LIST_AUTH_CODE}"
        try:
            response = await self.get_resp(url)
            if not isinstance(response, dict) or not response.get("success"):
                raise GreenApiException(
                    "monKeyconnect user list request did not return success=true."
                )

            data = response.get("data", [])
            if not isinstance(data, list):
                raise GreenApiException(
                    "monKeyconnect user list request returned non-list data."
                )

            wallet_to_discord_ids: dict[str, set[int]] = {}
            for item in data:
                if not isinstance(item, dict):
                    continue
                for discord_id, wallet in item.items():
                    if not isinstance(wallet, str):
                        continue
                    try:
                        parsed_discord_id = int(str(discord_id).strip())
                    except ValueError:
                        continue
                    address = wallet.replace(" ", "").strip().lower()
                    if address == "":
                        continue
                    wallet_to_discord_ids.setdefault(address, set()).add(
                        parsed_discord_id
                    )

            self.cached_monkeyconnect_wallet_to_discord_ids = wallet_to_discord_ids
            self.cached_monkeyconnect_wax_users = set(wallet_to_discord_ids.keys())
            self.monkeyconnect_cache_updated = int(utcnow().timestamp())
        except (aiohttp.web_exceptions.HTTPError, GreenApiException) as e:
            print(
                "Encountered an error attempting to fetch the monKeyconnect whitelist, "
                f"returning cached list. {e}"
            )

        return self.cached_monkeyconnect_wallet_to_discord_ids

    async def get_monkeyconnect_wax_users(
        self, force: bool = False, expiry: float = 300.0
    ) -> Set[str]:
        """Fetch the monkeyconnect discord user list wax mappings and return just the wallet set."""
        wallet_to_discord_ids = await self.get_monkeyconnect_wallet_to_discord_ids(
            force=force, expiry=expiry
        )
        if len(wallet_to_discord_ids) < 1:
            return self.cached_monkeyconnect_wax_users
        return set(wallet_to_discord_ids.keys())

    async def awblacklist_add(self, address: str) -> dict[str, Any]:
        """Add a wax address to the blacklist"""
        if "<" in address or ">" in address or "!" in address or "@" in address:
            raise InvalidInput(f"{address} is not a valid wax address.")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AW_BLACKLIST_AUTH_KEY}",
        }
        try:
            resp: dict[str, Any] = await self.get_resp(
                f"{AW_BLACKLIST}add",
                data=address,
                headers=headers,
                _type="post",
            )
        except GreenApiException as e:
            return {"success": False, "exception": repr(e)}
        self.awcache_updated = 0
        return resp

    async def awblacklist_remove(self, address: str) -> dict[str, Any]:
        """Remove an address from the blacklist"""
        if "<" in address or ">" in address or "!" in address or "@" in address:
            raise InvalidInput(f"{address} is not a valid wax address.")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AW_BLACKLIST_AUTH_KEY}",
        }
        try:
            resp: dict[str, Any] = await self.get_resp(
                f"{AW_BLACKLIST}delete",
                data=address,
                headers=headers,
                _type="delete",
            )
        except GreenApiException as e:
            return {"success": False, "exception": repr(e)}
        self.awcache_updated = 0
        return resp

    async def awget_blacklist(
        self, force: bool = False, expiry: float = 60.0
    ) -> Set[str]:
        """Fetch the blacklist from source. Cache for a minute, but cache is rendered out of date by a call to
        awblacklist_add or awblacklist_remove."""
        if not force and utcnow().timestamp() - self.awcache_updated < expiry:
            return self.cached_awblacklist
        # Refresh cached_blacklist
        limit: int = 1000
        offset: int = 0
        res = set()

        def err(msg: ReprProtocol) -> set[str]:
            print(
                f"Encountered an error attempting to fetch the AW blacklist, returning cached "
                f"blacklist. Result: {msg}"
            )
            return self.cached_awblacklist

        while True:
            results: Optional[list[dict[str, Any]]] = None
            try:
                response: dict[str, list[dict[str, Any]]] = await self.get_resp(
                    f"{AW_BLACKLIST}list?limit={limit}&offset={offset}"
                )
                if results is None or not hasattr(results, "data"):
                    return err(str(results))
                results = response["data"]
                if results is not None and len(results) > 0:
                    res |= set([i["wallet"].replace(" ", "") for i in results])
            except aiohttp.web_exceptions.HTTPError as e:
                return err(e)
            if not results:
                return err("")
            if len(results) < limit:
                self.cache_updated = int(utcnow().timestamp())
                self.cached_awblacklist = res
                return self.cached_awblacklist
            offset += limit
