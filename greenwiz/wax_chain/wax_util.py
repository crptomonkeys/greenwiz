"""
Utilities for interacting with unreliable Wax endpoints for transactions on that network.
    Copyright (C) 2021  Vyryn

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import asyncio
import binascii
import hashlib
import traceback
from json import JSONDecodeError, dumps
from time import time
from typing import Any, List, Optional, Union

import aiohttp
import discord
from aioeosabi import (
    EosAccount,
    EosAction,
    EosJsonRpc,
    EosKey,
    EosTransaction,
    serializer,
)
from aioeosabi.contracts import eosio_token
from aioeosabi.exceptions import EosAssertMessageException, EosRpcException
from aioeosabi.rpc import ERROR_NAME_MAP
from aiohttp import ClientConnectorError, ClientOSError, ServerDisconnectedError
from discord import Forbidden, HTTPException
from utils.exceptions import (
    InvalidInput,
    InvalidResponse,
    UnableToCompleteRequestedAction,
)
from utils.settings import (
    DEFAULT_WAX_COLLECTION,
    MINT_ACC_PERMISSION,
    MONKEYMATCH_ACC_NAME,
    MONKEYMATCH_PRIV_KEY,
    SALT_ACC_PERMISSION,
    TIP_ACC_PERMISSION,
    WAX_CACHE_TIME,
)
from utils.util import WaxNFT, load_json_var, log, today, usage_react, write_json_var

from wax_chain.collection_config import determine_collection, get_collection_info
from wax_chain.wax_contracts import atomicassets, atomictoolsx, monkeysmatch
from wax_chain.wax_contracts.monkeysmatch import gen_salt
from wax_chain.wax_market_utils import (
    atomic_api,
    fair_est,
    get_geometric_regressed_sale_price,
    get_lowest_current_offer,
    get_owners,
)

wax_history_api = "/v2/history/get_transaction"
wax_actions_api = "/v2/history/get_actions"
HYPERION_429_COOLDOWN_SECONDS = 10 * 60
PREFERRED_HYPERION_ENDPOINTS = [
    "https://api.waxsweden.org",
    "https://wax.eosphere.io",
    "https://wax.cryptolions.io",
]
# 'https://wax.eu.eosamsterdam.net/', 'https://api.wax.liquidstudios.io/', 'https://api.wax.bountyblok.io/'
full_api_weighted_list = [
    {"node_url": "https://wax.eu.eosamsterdam.net", "type": "api", "weight": 10},
    {"node_url": "https://wax.blacklusion.io", "type": "api", "weight": 10},
    {"node_url": "https://wax.dapplica.io", "type": "api", "weight": 10},
    {"node_url": "https://api-wax.eosauthority.com", "type": "api", "weight": 10},
    {"node_url": "https://api.wax.greeneosio.com", "type": "api", "weight": 10},
    {"node_url": "https://waxapi.ledgerwise.io", "type": "api", "weight": 10},
    {"node_url": "https://wax.pink.gg", "type": "api", "weight": 10},
    {"node_url": "https://wax.greymass.com", "type": "api", "weight": 10},
    {"node_url": "https://atomic.ledgerwise.io", "type": "atomic", "weight": 10},
    {"node_url": "https://apiwax.3dkrender.com", "type": "api", "weight": 10},
    {"node_url": "https://eu.wax.eosrio.io", "type": "api", "weight": 10},
    {"node_url": "https://wax.eu.eosamsterdam.net", "type": "history", "weight": 9},
    {"node_url": "https://wax.cryptolions.io", "type": "api", "weight": 9},
    {"node_url": "https://wax.dapplica.io", "type": "history", "weight": 9},
    {"node_url": "https://wax.dapplica.io", "type": "hyperion", "weight": 9},
    {"node_url": "https://api-wax.eosarabia.net", "type": "api", "weight": 9},
    {"node_url": "https://api-wax.eosauthority.com", "type": "history", "weight": 9},
    {"node_url": "https://api-wax.eosauthority.com", "type": "hyperion", "weight": 9},
    {"node_url": "https://api.wax.greeneosio.com", "type": "history", "weight": 9},
    {"node_url": "https://waxapi.ledgerwise.io", "type": "history", "weight": 9},
    {"node_url": "https://waxapi.ledgerwise.io", "type": "hyperion", "weight": 9},
    {"node_url": "https://wax.greymass.com", "type": "history", "weight": 9},
    {"node_url": "https://api.waxsweden.org", "type": "history", "weight": 9},
    {"node_url": "https://api.waxsweden.org", "type": "api", "weight": 9},
    {"node_url": "https://wax.eosdublin.io", "type": "history", "weight": 9},
    {"node_url": "https://wax.eosdublin.io", "type": "api", "weight": 9},
    {"node_url": "https://api.waxeastern.cn", "type": "history", "weight": 9},
    {"node_url": "https://api.waxeastern.cn", "type": "api", "weight": 9},
    {"node_url": "https://wax-atomic.eosiomadrid.io", "type": "atomic", "weight": 9},
    {"node_url": "https://aa.dapplica.io", "type": "atomic", "weight": 9},
    {"node_url": "https://wax.eosdac.io", "type": "api", "weight": 9},
    {"node_url": "https://wax-public.neftyblocks.com", "type": "api", "weight": 9},
    {"node_url": "https://atomic-wax-mainnet.wecan.dev", "type": "atomic", "weight": 9},
    {"node_url": "https://wax.defibox.xyz", "type": "api", "weight": 9},
    {"node_url": "https://wax.blokcrafters.io", "type": "api", "weight": 8},
    {"node_url": "https://wax.cryptolions.io", "type": "history", "weight": 8},
    {"node_url": "https://wax.cryptolions.io", "type": "hyperion", "weight": 8},
    {"node_url": "https://wax.eosphere.io", "type": "history", "weight": 8},
    {"node_url": "https://wax.eosphere.io", "type": "api", "weight": 8},
    {"node_url": "https://api.wax.greeneosio.com", "type": "hyperion", "weight": 8},
    {"node_url": "https://api.waxsweden.org", "type": "hyperion", "weight": 8},
    {"node_url": "https://api-wax-aa.eosarabia.net", "type": "atomic", "weight": 8},
    {"node_url": "https://aa-api-wax.eosauthority.com", "type": "atomic", "weight": 8},
    {"node_url": "https://wax.api.atomicassets.io", "type": "atomic", "weight": 8},
    {"node_url": "https://wax.eosdublin.io", "type": "hyperion", "weight": 8},
    {"node_url": "https://api.waxeastern.cn", "type": "hyperion", "weight": 8},
    {"node_url": "https://wax-bp.wizardsguild.one", "type": "api", "weight": 8},
    {"node_url": "https://wax.eosdac.io", "type": "history", "weight": 8},
    {"node_url": "https://wax.eosdac.io", "type": "hyperion", "weight": 8},
    {"node_url": "https://wax.defibox.xyz", "type": "history", "weight": 8},
    {"node_url": "https://wax-aa.eosdac.io", "type": "atomic", "weight": 8},
    {
        "node_url": "https://atomic-api.wax.cryptolions.io",
        "type": "atomic",
        "weight": 8,
    },
    {"node_url": "https://wax.eosusa.io", "type": "history", "weight": 8},
    {"node_url": "https://wax.eosusa.io", "type": "api", "weight": 8},
    {"node_url": "https://api.wax.alohaeos.com", "type": "history", "weight": 7},
    {"node_url": "https://api.wax.alohaeos.com", "type": "api", "weight": 7},
    {"node_url": "https://api.wax.alohaeos.com", "type": "hyperion", "weight": 7},
    {"node_url": "https://wax.eu.eosamsterdam.net", "type": "hyperion", "weight": 7},
    {"node_url": "https://wax.blacklusion.io", "type": "history", "weight": 7},
    {"node_url": "https://wax.blacklusion.io", "type": "hyperion", "weight": 7},
    {"node_url": "https://wax.blokcrafters.io", "type": "history", "weight": 7},
    {"node_url": "https://wax.blokcrafters.io", "type": "hyperion", "weight": 7},
    {"node_url": "https://api-wax.eosarabia.net", "type": "history", "weight": 7},
    {"node_url": "https://api-wax.eosarabia.net", "type": "hyperion", "weight": 7},
    {"node_url": "https://wax.eosphere.io", "type": "hyperion", "weight": 7},
    {"node_url": "https://api.wax.liquidstudios.io", "type": "hyperion", "weight": 7},
    {"node_url": "https://wax-aa.eu.eosamsterdam.net", "type": "atomic", "weight": 7},
    {"node_url": "https://aa.wax.blacklusion.io", "type": "atomic", "weight": 7},
    {"node_url": "https://wax.blokcrafters.io", "type": "atomic", "weight": 7},
    {"node_url": "https://wax-atomic-api.eosphere.io", "type": "atomic", "weight": 7},
    {"node_url": "https://wax-atomic.wizardsguild.one", "type": "atomic", "weight": 7},
    {"node_url": "https://atomic.3dkrender.com", "type": "atomic", "weight": 7},
    {"node_url": "https://atomic.hivebp.io", "type": "atomic", "weight": 7},
    {"node_url": "https://api.hivebp.io", "type": "api", "weight": 7},
    {"node_url": "https://apiwax.3dkrender.com", "type": "history", "weight": 7},
    {"node_url": "https://apiwax.3dkrender.com", "type": "hyperion", "weight": 7},
    {"node_url": "https://atomic.wax.eosrio.io", "type": "atomic", "weight": 7},
    {"node_url": "https://wax.defibox.xyz", "type": "hyperion", "weight": 7},
    {"node_url": "https://wax.eosusa.io", "type": "atomic", "weight": 7},
    {"node_url": "https://eu.wax.eosrio.io", "type": "hyperion", "weight": 7},
    {"node_url": "https://wax.eosusa.io", "type": "hyperion", "weight": 7},
    {"node_url": "https://atomic-wax.tacocrypto.io", "type": "atomic", "weight": 7},
    {"node_url": "https://wax.csx.io", "type": "history", "weight": 0},
    {"node_url": "https://wax.csx.io", "type": "api", "weight": 0},
    {"node_url": "https://wax.csx.io", "type": "hyperion", "weight": 0},
    {"node_url": "https://wax.eoseoul.io", "type": "history", "weight": 0},
    {"node_url": "https://wax.eoseoul.io", "type": "api", "weight": 0},
    {"node_url": "https://wax.eoseoul.io", "type": "hyperion", "weight": 0},
    {"node_url": "https://api.wax.liquidstudios.io", "type": "history", "weight": 0},
    {"node_url": "https://api.wax.liquidstudios.io", "type": "api", "weight": 0},
    {"node_url": "https://wax.eosn.io", "type": "history", "weight": 0},
    {"node_url": "https://wax.eosn.io", "type": "api", "weight": 0},
    {"node_url": "https://wax.eosn.io", "type": "hyperion", "weight": 0},
    {"node_url": "https://wax.pink.gg", "type": "history", "weight": 0},
    {"node_url": "https://wax.pink.gg", "type": "hyperion", "weight": 0},
    {"node_url": "https://wax.greymass.com", "type": "hyperion", "weight": 0},
    {"node_url": "https://api.wax-aa.bountyblok.io", "type": "atomic", "weight": 0},
    {"node_url": "https://api.atomic.greeneosio.com", "type": "atomic", "weight": 0},
    {"node_url": "https://api.wax.liquidstudios.io", "type": "atomic", "weight": 0},
    {"node_url": "https://api.wax.eosdetroit.io", "type": "history", "weight": 0},
    {"node_url": "https://api.wax.eosdetroit.io", "type": "api", "weight": 0},
    {"node_url": "https://api.wax.eosdetroit.io", "type": "hyperion", "weight": 0},
    {"node_url": "https://api.hivebp.io", "type": "history", "weight": 0},
    {"node_url": "https://api.hivebp.io", "type": "hyperion", "weight": 0},
    {"node_url": "https://wax-aa.eosdublin.io", "type": "atomic", "weight": 0},
    {"node_url": "https://api.wax.mainnet.wecan.dev", "type": "history", "weight": 0},
    {"node_url": "https://api.wax.mainnet.wecan.dev", "type": "api", "weight": 0},
    {"node_url": "https://api.wax.mainnet.wecan.dev", "type": "hyperion", "weight": 0},
    {"node_url": "https://wax-bp.wizardsguild.one", "type": "history", "weight": 0},
    {"node_url": "https://wax-bp.wizardsguild.one", "type": "hyperion", "weight": 0},
    {"node_url": "https://wax.hkeos.com/aa", "type": "atomic", "weight": 0},
    {"node_url": "https://atomic.tokengamer.io", "type": "atomic", "weight": 0},
    {"node_url": "https://wax-hyperion.eosiomadrid.io", "type": "history", "weight": 0},
    {"node_url": "https://wax-hyperion.eosiomadrid.io", "type": "api", "weight": 0},
    {
        "node_url": "https://wax-hyperion.eosiomadrid.io",
        "type": "hyperion",
        "weight": 0,
    },
    {"node_url": "https://wax-public.neftyblocks.com", "type": "history", "weight": 0},
    {"node_url": "https://wax-public.neftyblocks.com", "type": "hyperion", "weight": 0},
    {
        "node_url": "https://aa-wax-public.neftyblocks.com",
        "type": "atomic",
        "weight": 0,
    },
    {"node_url": "https://atomic.wax.eosdetroit.io", "type": "atomic", "weight": 0},
    {"node_url": "https://eu.wax.eosrio.io", "type": "history", "weight": 0},
]

wax_dict: dict[str, dict[int, dict[str, str]]] = {}
cache_ages: dict[str, dict[int, float]] = {}
cache_cards, card_cache_age = {}, 0
template_id_price_cache: dict[int, tuple[float, float]] = {}
template_id_price_cache_ages: dict[int, float] = {}


# https://validate.eosnation.io/wax/reports/endpoints.html
# http://waxmonitor.cmstats.net/api/endpoints?format=json


def configure_wax_endpoints(full_weighted_list):
    """Parses a full_api_weighted_list json from waxmonitor.cmstats.net into a list of active endpoints of each type."""
    history_endpoints, api_endpoints, atomic_endpoints, hyperion_endpoints = (
        [],
        [],
        [],
        [],
    )
    for entry in full_weighted_list:
        if entry["weight"] == 0:
            continue
        if entry["type"] == "history":
            history_endpoints.append(entry["node_url"])
        elif entry["type"] == "api":
            # api_endpoints.extend([entry['node_url']] * entry['weight'])
            api_endpoints.append(entry["node_url"])
        elif entry["type"] == "atomic":
            atomic_endpoints.append(entry["node_url"])
        elif entry["type"] == "hyperion":
            hyperion_endpoints.append(entry["node_url"])
    hyperion_endpoints = prioritize_endpoints(
        endpoints=hyperion_endpoints,
        preferred_endpoints=PREFERRED_HYPERION_ENDPOINTS,
    )
    return history_endpoints, api_endpoints, atomic_endpoints, hyperion_endpoints


def prioritize_endpoints(endpoints: list[str], preferred_endpoints: list[str]) -> list[str]:
    """Reorders endpoints so preferred entries appear first while preserving relative order otherwise."""
    preferred_order = {
        entry.rstrip("/"): index for index, entry in enumerate(preferred_endpoints)
    }
    unique_endpoints: list[str] = []
    seen: set[str] = set()
    for endpoint in endpoints:
        normalized = endpoint.rstrip("/")
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_endpoints.append(endpoint)
    prioritized = sorted(
        [entry for entry in unique_endpoints if entry.rstrip("/") in preferred_order],
        key=lambda entry: preferred_order[entry.rstrip("/")],
    )
    remaining = [entry for entry in unique_endpoints if entry.rstrip("/") not in preferred_order]
    return prioritized + remaining


def format_wax_amount(amount):
    """Formats a float into the string format that the wax network typically accepts as a full precision WAX amount."""
    total = f"{amount:.8f}"
    return f"{total} WAX"


def get_resp_code(response):
    """Wax nodes don't always follow HTTP standards let alone RESTful best practices."""
    code = response.get("code", 0)
    if code == 0 or not isinstance(code, int):
        code = response.get("statusCode", 0)
    try:
        code = int(code)
    except TypeError:
        pass
    return code


class InvalidWaxCardSend(InvalidResponse):
    """Invalid Wax Card Send"""

    pass


class NoCardsException(UnableToCompleteRequestedAction):
    """The bot account is empty of NFTs."""

    pass


class Claimlink:
    link_id: str
    priv_key: str

    def __init__(self, link_id: str, priv_key: str) -> None:
        self.link_id = link_id
        self.priv_key = priv_key

    @property
    def ah(self) -> str:
        return f"https://wax.atomichub.io/trading/link/wax-mainnet/{self.link_id}?key={self.priv_key}"

    @property
    def nefty(self) -> str:
        return f"https://neftyblocks.com/links/{self.link_id}?key={self.priv_key}"

    @property
    def public(self) -> str:
        return f"https://wax.atomichub.io/trading/link/wax-mainnet/{self.link_id}"

    def __repr__(self) -> str:
        return self.nefty


class EosJsonRpcWrapper(EosJsonRpc):
    """Wrapper class for EosJsonRpc to reuse an aiohttp session which is good practice."""

    def __init__(self, url: str, ses: Optional[aiohttp.ClientSession] = None) -> None:
        self.ses = ses
        super().__init__(url)

    async def post(self, endpoint: str, json=None) -> dict[str, Any]:
        """Override EosJsonRpc to reuse an aiohttp session and handle non-standard endpoint errors somewhat
        more robustly"""
        if json is None:
            json = {}
        if self.ses is not None:
            async with self.ses.post(f"{self.URL}/v1{endpoint}", json=json) as res:
                resp_dict: Optional[dict[str, Any]] = None
                try:
                    resp_dict = await res.json(content_type=None)
                except JSONDecodeError:
                    resp_dict = {"code": 500, "error": {"name": "JSONDecodeError"}}
                finally:
                    if resp_dict is None:
                        resp_dict = {
                            "code": 500,
                            "error": {"name": "NonStandardErrorRaisedByEndpoint"},
                        }
                # Poor coding practice, but this is what the lib uses. I've added use of status but kept code too as
                # it is what the lib uses.
                if isinstance(resp_dict, dict) and resp_dict.get("code") == 500:
                    error = resp_dict.get("error", {})
                    raise ERROR_NAME_MAP.get(error.get("name"), EosRpcException)(error)
                try:
                    if res.status == 500:
                        error = resp_dict.get("error", {})
                        raise ERROR_NAME_MAP.get(error.get("name"), EosRpcException)(error)
                except TypeError:
                    pass
                return resp_dict
        # If self has no session, just use super.post which creates a session and cleans up each time. This is done
        # instead of making a self.ses if one isn't provided in order to ensure proper cleanup without requiring use
        # of a context manager to invoke this object.
        super_dict: dict[str, Any] = await super().post(endpoint, json=json)
        return super_dict


class WaxConnection:
    """Manager class for idempotently coordinating multiple EosJsonRpcWrappers to increase robustness of
    connection to the network with unreliable APIs. Replaces sign_and_push_transaction with custom
    execute_transaction so this is a generalized class but also provides methods for some specialized
    high level interactions. I suppose this is what you do when you really want to use a library you don't like.
    Bot object can be any object with a session attribute, log function and wax_ac attribute. Wax_ac should be a
    list of wax_chain account objects, and session an aiohttp client session."""

    def __init__(self, bot) -> None:
        (
            self.history_endpoints,
            self.api_endpoints,
            self.atomic_endpoints,
            self.hyperion_endpoints,
        ) = configure_wax_endpoints(full_api_weighted_list)
        self.wax_ac = bot.wax_ac
        self.session = bot.session
        self.bot = bot
        self.cl_reentrancy_guard = False
        self.history_rpc = [EosJsonRpcWrapper(addr, ses=self.session) for addr in self.history_endpoints]
        self.api_rpc = [EosJsonRpcWrapper(addr, ses=self.session) for addr in self.api_endpoints]
        self.atomic_rpc = [EosJsonRpcWrapper(addr, ses=self.session) for addr in self.atomic_endpoints]
        self.hyperion_rpc = [EosJsonRpcWrapper(addr, ses=self.session) for addr in self.hyperion_endpoints]
        self.log(f"Wax history endpoints: {self.history_endpoints}")
        self.log(f"Wax core api endpoints: {self.api_endpoints}")
        self.log(f"Wax atomic endpoints: {self.atomic_endpoints}")
        self.log(f"Wax hyperion endpoints: {self.hyperion_endpoints}")

    def log(self, message, severity="DBUG"):
        self.bot.log(message, severity=severity)

    async def execute_transaction(
        self,
        actions: Union[EosAction, List[EosAction]],
        context_free_bytes: bytes = bytes(32),
        sender_ac: str = DEFAULT_WAX_COLLECTION,
    ) -> dict[str, Any]:
        """
        Attempts to sign and push a transaction to one of several API endpoints.
        Uses a first non-exception result approach so that the first successful broadcast is returned,
        while other pending tasks are cancelled.
        """
        # Convert to list if it isn't one already
        if not isinstance(actions, list):
            actions = [actions]
        failed_rpcs, suc = set(), "None"
        chain_id: bytes = b""
        block: Optional[dict[str, Any]] = None
        if len(actions) < 1:
            raise AssertionError("Invalid transaction composed, a transaction must have at least one action.")
        self.log(f"Executing a transaction, actions: {actions}")

        # Try getting the head block from each rpc until one succeeds
        for rpc in self.api_rpc:
            try:
                self.log(f"Attempting to get head block from {rpc.URL}")
                block = await rpc.get_head_block()
                chain_id = await rpc.get_chain_id()
                for action in actions:
                    if not isinstance(action.data, dict):
                        continue
                    self.log(f"Attempting to prepare action {action.account}::{action.name}::{action.data}")
                    abi_bin = await rpc.abi_json_to_bin(action)
                    action.data = binascii.unhexlify(abi_bin["binargs"])
                suc = rpc.URL
                self.log(f"Successfully got head block {str(block)[:2000]}, {chain_id=} from {rpc.URL}.")
                break
            except (
                IndexError,
                ClientConnectorError,
                InvalidResponse,
                EosRpcException,
                ServerDisconnectedError,
                AssertionError,
                EosAssertMessageException,
                TypeError,
                ClientOSError,
                KeyError,
                asyncio.TimeoutError,
                aiohttp.ClientError,
            ) as e:
                self.log(f"{e} error attempting to set up a transaction with {rpc.URL}")
                if e is not None:
                    trace = e.__traceback__
                    lines = traceback.format_exception(type(e), e, trace)
                else:
                    lines = [""]
                traceback_text = "```py\n"
                traceback_text += "".join(lines)
                traceback_text += "\n```"
                self.log(traceback_text)
                failed_rpcs.add(rpc.URL)
                continue
        if block is None:
            raise InvalidWaxCardSend(
                f"Failed to get head block from any of my {len(self.api_endpoints)} configured API endpoints."
            )

        if failed_rpcs:
            self.log(f"Failed to get head block from {failed_rpcs} but eventually got {block} from {suc}.")

        # Create the transaction using the block parameters
        transaction = EosTransaction(
            ref_block_num=block["block_num"] & 65535,
            ref_block_prefix=block["ref_block_prefix"],
            actions=actions,
        )

        # Serialize the transaction once for idempotence
        bytes_serialized_transaction: bytes = serializer.serialize(transaction)
        digest = hashlib.sha256(b"".join((chain_id, bytes_serialized_transaction, context_free_bytes))).digest()
        signatures = [self.wax_ac[sender_ac].key.sign(digest)]
        serialized_transaction = binascii.hexlify(bytes_serialized_transaction).decode()
        self.log(f"Serialized transaction {transaction}, creating broadcast tasks.")

        # Send the transaction to all connected nodes simultaneously.
        tasks = [asyncio.create_task(self.tx(rpc, signatures, serialized_transaction)) for rpc in self.api_rpc]

        async def get_first_non_exception_result(tasks: List[asyncio.Task], timeout: int = 60) -> Any:
            """
            Awaits the first task to successfully complete without raising an exception

            """
            try:
                for completed_task in asyncio.as_completed(tasks, timeout=timeout):
                    try:
                        result = await completed_task
                        return result
                    except Exception as exc:
                        self.log(f"In wax execute, task failed with error: {exc}")
                        continue
                # If we get here, none of the tasks succeeded
                self.log("Failed to broadcast a wax transaction; all my connected endpoints appear to be down.")
                raise InvalidWaxCardSend(
                    "Hmm, all the APIs I am connected to seem to be down or unhappy with me at the moment. "
                    "Try again later."
                )
            except asyncio.TimeoutError:
                self.log("Failed to broadcast a wax transaction; timeout reached.")
                raise InvalidWaxCardSend("Timed out waiting for a valid result from any node. Try again later.")
            finally:
                # Cancel any tasks that haven't completed
                for task in tasks:
                    task.cancel()

        # Wait for the first non-exception result
        result = await get_first_non_exception_result(tasks, timeout=60)
        self.log(f"Result is: {result}")
        return result

    async def tx(
        self,
        rpc: EosJsonRpcWrapper,
        signatures: List[str],
        serialized_transaction: str,
    ) -> dict[str, Any]:
        """
        Does a single transaction push to a single EosJsonRpcWrapper object, if it is successful sets the
        callback future.
        """
        try:
            tx_resp: dict[str, Any] = await rpc.push_transaction(
                signatures=signatures, serialized_transaction=serialized_transaction
            )
        except EosAssertMessageException as e:
            self.log(f"Received an EosAssertMessageException: {e}")
            raise
        else:
            content = dumps(tx_resp).replace("\\", "")
            if "authorization" in content and "block_num" in content:
                self.log(f"I think {content} is a valid tx.")
                return tx_resp
            else:
                self.log(f"Transaction response invalid: {content}")
                raise ValueError("Transaction response does not contain expected fields.")

    async def transfer_funds(
        self,
        receiver: str,
        amount,
        sender: str = "Unknown",
        sender_ac: str = DEFAULT_WAX_COLLECTION,
    ) -> dict[str, Any]:
        prep_amount = format_wax_amount(amount)
        actions = [
            eosio_token.transfer(
                from_addr=self.wax_ac[sender_ac].name,
                to_addr=receiver,
                quantity=prep_amount,
                memo=f"Funds transfer by {sender} on behalf of NFT Tip Bot.",
                authorization=[self.wax_ac[sender_ac].authorization(MINT_ACC_PERMISSION)],
            )
        ]

        return await self.execute_transaction(actions, sender_ac=sender_ac)

    async def transfer_assets(
        self,
        receiver: str,
        asset_ids: list[int],
        sender: str = "Unknown",
        sender_ac: str = DEFAULT_WAX_COLLECTION,
        memo: str = "",
    ) -> dict[str, Any]:
        if memo == "":
            memo = f"Asset transfer by {sender} on behalf of {sender_ac} by the NFT Tip Bot."
        actions = [
            atomicassets.transfer(
                from_addr=self.wax_ac[sender_ac].name,
                to_addr=receiver,
                asset_ids=asset_ids,
                memo=memo,
                authorization=[self.wax_ac[sender_ac].authorization(TIP_ACC_PERMISSION)],
            )
        ]

        return await self.execute_transaction(actions, sender_ac=sender_ac)

    async def mint_asset(
        self,
        to_addr: str,
        template_id: int,
        amount: int = 1,
        collection: str = DEFAULT_WAX_COLLECTION,
        schema: str = DEFAULT_WAX_COLLECTION,
    ) -> dict[str, Any]:
        actions = [
            atomicassets.mintasset(
                minter=self.wax_ac[collection].name,
                to_addr=to_addr,
                collection=collection,
                schema=schema,
                template_id=template_id,
                authorization=[self.wax_ac[collection].authorization(MINT_ACC_PERMISSION)],
            )
        ] * amount

        return await self.execute_transaction(actions, sender_ac=collection)

    def update_weighted_history_rpc(self, faulty: Optional[EosJsonRpcWrapper]) -> None:
        """Does one update of the semi-random weighted rpc list by removing the faulty entry and adding a random one
        if the selection is too thin or too small."""
        if faulty is None:
            return
        try:
            self.history_rpc.remove(faulty)
        except ValueError:
            pass

    def remove_all_from_history_rpc(self, faulty: str) -> None:
        """Removes all EosJsonRpcWrappers from the semi-random weighted list with the given URL because it isn't
        working for whatever reason."""
        to_remove = []
        for rpc in self.history_rpc:
            if rpc.URL == faulty:
                to_remove.append(rpc)
        self.log(f"Removing {len(to_remove)} EosJsonRpcWrappers from the semi-random weighted list as faulty.")
        for rpc_ in self.history_rpc:
            if rpc_.URL == faulty:
                self.history_rpc.remove(rpc_)

    async def get_hyperion_actions(self, params: dict[str, Any]) -> dict[str, Any]:
        """Query /v2/history/get_actions from available Hyperion endpoints until one succeeds."""
        if len(self.hyperion_rpc) < 1:
            raise UnableToCompleteRequestedAction(
                "I have no configured Hyperion endpoints at the moment."
            )
        attempts: list[str] = []
        for rpc in self.hyperion_rpc:
            try:
                async with self.session.get(rpc.URL + wax_actions_api, params=params) as resp:
                    response = await resp.json(content_type=None)
                    code = get_resp_code(response)
                    if code == 0:
                        code = resp.status
                    if code >= 400:
                        attempts.append(f"{rpc.URL} -> status {code}")
                        if code == 429:
                            self.log(
                                f"Hyperion endpoint {rpc.URL} returned 429. "
                                f"Pausing {HYPERION_429_COOLDOWN_SECONDS} seconds before continuing.",
                                "WARN",
                            )
                            await asyncio.sleep(HYPERION_429_COOLDOWN_SECONDS)
                        continue
                    if not isinstance(response, dict):
                        attempts.append(f"{rpc.URL} -> non-dict response")
                        continue
                    return response
            except (
                JSONDecodeError,
                aiohttp.ClientError,
                asyncio.TimeoutError,
                ServerDisconnectedError,
                ClientOSError,
            ) as e:
                attempts.append(f"{rpc.URL} -> {type(e).__name__}")
                continue
        raise UnableToCompleteRequestedAction(
            "All Hyperion endpoints failed while fetching actions: "
            f"{'; '.join(attempts[:8])}"
        )

    async def get_link_id_and_confirm_claimlink_creation(self, tx_id) -> str:
        """Attempts to confirm that a claimlink was successfully created and get its link_id to
        present to the recipient in a claimlink."""
        self.log("Generating a claimlink and attempting to confirm its creation.")
        cycles = 0
        params = {"id": tx_id}
        selected: Optional[EosJsonRpcWrapper] = None
        while cycles < 30:
            sleep_time = min(2**cycles, 64)
            self.log(
                f"Waiting to receive confirmation of transaction {tx_id}, on cycle {cycles} of 30."
                f" Waiting {sleep_time} seconds before continuing."
            )
            await asyncio.sleep(sleep_time)  # Exponential backoff
            if len(self.history_rpc) < 1:
                self.log(
                    "All APIs have been exhausted. Resetting the weighted RPC list and warning the user.",
                    "WARN",
                )
                self.history_rpc.extend([EosJsonRpcWrapper(x, ses=self.session) for x in self.history_endpoints])
                raise UnableToCompleteRequestedAction(
                    "All APIs I am connected to have reported invalid results, so I wasn't able to confirm"
                    " your transaction."
                )
            # Rotate through endpoints; do not pin retries to index 0.
            selected = self.history_rpc[cycles % len(self.history_rpc)]
            host = selected.URL
            self.log(f"Attempting to confirm transaction {tx_id} with url {selected.URL}")
            resp = None
            try:
                async with self.session.get(host + wax_history_api, params=params) as resp:
                    response = await resp.json(content_type=None)
                    self.log(f"Response to attempt to get history for {tx_id}: {response} (from {selected.URL})")
                    code = get_resp_code(response)
                    if code == 0:
                        code = resp.status
                    if code < 400 and response.get("executed", False):
                        try:
                            link_id: int = response["actions"][1]["act"]["data"]["link_id"]
                        except KeyError:
                            link_id = int(
                                str(response).split("{'link_id': '", maxsplit=1)[1].split("', ", maxsplit=1)[0]
                            )
                        self.log(
                            f"Received an apparently well-formed response for link_id {link_id} from {selected.URL}."
                        )
                        return str(link_id)
                    if code == 410 or code == 404:
                        self.log(
                            f"{selected.URL} reported the /get_transaction endpoint as 410 GONE, so removing "
                            f"them from my queries.",
                            "WARN",
                        )
                        self.remove_all_from_history_rpc(selected.URL)
                        cycles = 0
                    elif code >= 500:
                        self.log(
                            f"{selected.URL} returned status {code} from /get_transaction, so removing it from "
                            f"this weighted retry list.",
                            "WARN",
                        )
                        self.update_weighted_history_rpc(selected)
            except (JSONDecodeError, aiohttp.ClientConnectorError, AttributeError) as e:
                text = resp.text if hasattr(resp, "text") else "[No response text]"
                self.log(
                    f"{selected.URL} returned a {type(e)} invalid response {e}:: {text}, so removing them "
                    f"from my queries.",
                    "WARN",
                )
                self.remove_all_from_history_rpc(selected.URL)
                cycles = 0
            except (
                aiohttp.ContentTypeError,
                IndexError,
                KeyError,
                ValueError,
                ServerDisconnectedError,
                aiohttp.ClientConnectorCertificateError,
                ClientOSError,
                asyncio.TimeoutError,
                aiohttp.ClientError,
            ) as e:
                self.log(f"{type(e)}::{e} for tx_id {tx_id} from {selected.URL}. Continuing...")
                self.update_weighted_history_rpc(selected)
            cycles += 1

        self.update_weighted_history_rpc(selected)
        self.log(f"Timed out, failing to confirm {tx_id} after 30 iterations of an exponential backoff.")
        raise InvalidWaxCardSend(
            "I submitted the transaction, but WAX failed to process it within"
            f" 27 minutes, so the attempt has timed out. I have tried submitting"
            f" to {len(self.history_endpoints)} different APIs during this time but was "
            f"unable to confirm the transaction through any of them."
        )

    async def cancel_claimlinks(
        self,
        link_ids: list[int],
        collection: str = DEFAULT_WAX_COLLECTION,
        _max: int = 50,
    ) -> tuple[bool, str]:
        """Cancels all the links with the specified IDs.
        Raises an exception if there are more than _max links due to chain CPU constraints.
        """
        if len(link_ids) > _max:
            raise AssertionError(
                f"""{len(link_ids)} is too many claim links to cancel in one transaction,
                 max is {_max} due to on-chain CPU constraints."""
            )
        self.log(f"Cancellink claimlinks {link_ids} for collection {collection}.")
        actions = [
            atomictoolsx.cancellink(
                link_id=i,
                authorization=[self.wax_ac[collection].authorization(TIP_ACC_PERMISSION)],
            )
            for i in link_ids
        ]
        result = await self.execute_transaction(actions, sender_ac=collection)
        tx_id = result["transaction_id"]
        processed = result.get("processed", dict())
        receipt = processed.get("receipt", dict())
        self.log(receipt)
        status = receipt.get("status", "errored")
        self.log(f"Claimlinks {link_ids} cancellation. Result is: {result}, transaction id is {tx_id}")
        return status, tx_id

    async def cancel_claimlink(
        self,
        link_id: int,
        collection: str = DEFAULT_WAX_COLLECTION,
    ) -> tuple[bool, str]:
        """Cancels the claimlink with the specified id."""
        return await self.cancel_claimlinks([link_id], collection=collection)

    async def create_claimlink(
        self,
        asset_ids: list[int],
        memo=None,
        wait_for_confirmation=True,
        collection: str = DEFAULT_WAX_COLLECTION,
    ) -> Claimlink:
        """Creates and returns a claimlink for the specified asset ids."""
        if not memo:
            memo = "NFT Tip Bot reward claimlink."
        memo += f" {get_collection_info(collection).link_message_append}"

        # Generate the link's keypair
        keypair = EosKey()
        priv_key = keypair.to_wif()
        key = keypair.to_public()

        actions = [
            atomictoolsx.announcelink(
                creator=self.wax_ac[collection].name,
                key=key,
                asset_ids=asset_ids,
                memo=memo,
                authorization=[self.wax_ac[collection].authorization(TIP_ACC_PERMISSION)],
            ),
            atomicassets.transfer(
                from_addr=self.wax_ac[collection].name,
                to_addr="atomictoolsx",
                asset_ids=asset_ids,
                memo="link",
                authorization=[self.wax_ac[collection].authorization(TIP_ACC_PERMISSION)],
            ),
        ]
        result = await self.execute_transaction(actions, sender_ac=collection)
        tx_id = result["transaction_id"]
        self.log(f"Claimlink submission. Result is: {result}")

        # Need to confirm tx_id to know what link to give user. If wait_for_confirmation is off then take best guess.
        if wait_for_confirmation:
            link_id = await self.get_link_id_and_confirm_claimlink_creation(tx_id)
        else:
            link_id = str(result).split("link_id': ")[1].split(",")[0]
            link_id = link_id[1:].split("'")[0]

        return Claimlink(link_id, priv_key)

    async def get_random_assets_to_send(
        self, user: str, num=1, collection: str = DEFAULT_WAX_COLLECTION
    ) -> list[WaxNFT]:
        """Helper function that gets random NFTs to send for drops"""
        if not hasattr(self.bot, "cached_cards"):
            raise UnableToCompleteRequestedAction("I'm still loading my cache on startup, try again in a few minutes.")

        if len(self.bot.cached_cards[collection]) < 1:
            raise NoCardsException(f"The {collection} Tip Bot account is empty, so I can't send {user} any more cards")

        selected_asset_ids = []
        # Ensure parallel executions can't choose the same asset.
        while self.cl_reentrancy_guard:
            await asyncio.sleep(0.2)
        self.cl_reentrancy_guard = True
        n_cards = len(self.bot.cached_cards[collection])
        if n_cards < num:
            self.cl_reentrancy_guard = False
            raise NoCardsException(
                f"The bot account only has {n_cards} cards at the moment, so I can't send {user} {num} cards."
            )
        for i in range(num):
            # bot.cached_cards is refreshed every five minutes and shuffled at fetch time.
            selected_asset_ids.append(self.bot.cached_cards[collection].pop())
        self.cl_reentrancy_guard = False
        return selected_asset_ids

    def get_memo(self, user: str, memo: str = "", collection: str = DEFAULT_WAX_COLLECTION) -> str:
        """Helper function that creates a valid memo to use for a drop"""
        if memo == "":
            f"Random {collection} reward for ({user})."
        else:
            memo += f" ({user})"

        message_length = len(memo) + len(get_collection_info(collection).link_message_append) + 1
        if message_length >= 256:
            raise InvalidInput(
                f"Your memo must be less than 256 characters long. With the bit I add,"
                f"it is currently {message_length} characters long."
            )
        return memo

    async def get_random_claim_link(
        self, user: str, memo="", num=1, collection: str = DEFAULT_WAX_COLLECTION
    ) -> Claimlink:
        memo = self.get_memo(user, memo, collection)
        # Choose an asset and make a claim link.
        selected_assets = await self.get_random_assets_to_send(user, num, collection)
        selected_asset_ids = [asset.asset_id for asset in selected_assets]
        link: Claimlink = await self.create_claimlink(selected_asset_ids, memo=memo, collection=collection)
        return link

    async def update_salt(self) -> str:
        acc: EosAccount = EosAccount(name=MONKEYMATCH_ACC_NAME, private_key=MONKEYMATCH_PRIV_KEY)
        salt: str = gen_salt()
        actions = [monkeysmatch.setsalt(salt=salt, authorization=acc.authorization(SALT_ACC_PERMISSION))]
        await self.execute_transaction(actions, sender_ac=MONKEYMATCH_ACC_NAME)
        return salt

    async def monkeysmatch_top(self, _min: int = 1) -> dict[str, int]:
        """Fetches the users who have completed at least n games of monkeysmatch."""
        for rpc in self.api_rpc:
            try:
                res = await rpc.get_table_rows(
                    "monkeysmatch",
                    "monkeysmatch",
                    "users",
                    index_position=1,
                    limit=500,
                    reverse=False,
                    show_payer=False,
                    json=True,
                )
            except EosRpcException:
                continue
            return {item["owner"]: item["completed_sets"] for item in res["rows"] if item["completed_sets"] >= _min}
        raise UnableToCompleteRequestedAction("All the apis I am connected to appear to be down at the moment. (2)")


def incr_given_today(uid: int) -> None:
    usage = load_json_var("card_sends")
    log(f"Reading usage: {usage}", "TST")
    try:
        usage[today()][str(uid)] += 1
    except KeyError:
        try:
            usage[today()][str(uid)] = 1
        except KeyError:
            usage[today()] = dict()
            usage[today()][str(uid)] = 1
    log(f"Writing usage: {usage}", "DBUG")
    write_json_var("card_sends", usage)


def check_given_today(uid: int) -> int:
    usage = load_json_var("card_sends")
    res = int(usage.get(today(), {}).get(str(uid), 0))
    return res


async def schedule_dm_user(user, increments, message) -> None:
    await asyncio.sleep(increments)
    try:
        await user.send(message)
    except Forbidden:
        pass
    log(f"{user} has been sent their followup message, {message}")


async def get_template_id(card_num: int, session: aiohttp.ClientSession) -> int:
    global cache_cards, card_cache_age
    cache_cards = await update_cache_cards(session)
    try:
        card_info: dict[str, int] = cache_cards[card_num]
    except IndexError:
        await update_cache_cards(session)
        try:
            card_info = cache_cards[card_num]
        except IndexError:
            return -1
    return card_info["template_id"]


async def announce_drop(
    bot,
    wallet: str,
    assets: list[WaxNFT],
    user: discord.Member,
    memo: str,
    num: int = 1,
    announce: bool = True,
    collection: str = DEFAULT_WAX_COLLECTION,
) -> None:
    """Send a user a message that a random NFT has been sent to their wallet."""
    cinfo = get_collection_info(collection)
    if num == 1:
        nft_info = " NFT."
        if assets[0].ipfs_hash != "":
            nft_info = f" [NFT](https://ipfs.neftyblocks.io/ipfs/{assets[0].ipfs_hash})."
        to_send = (
            f"Congratulations! You have won a random {cinfo.name} {nft_info}"
            f" It's been sent directly to your linked wallet {wallet}, you can see it with the following link\n"
        )
    else:
        to_send = (
            f"Congratulations! You have won {num} random {cinfo.name} NFTs! They have been"
            f" sent directly to your linked wallet {wallet}, you can see them with the following links\n"
        )
    if num >= 5:
        to_send += "Note that only links for the first 5 are included, check out the rest in your profile!"
    channel = bot.get_guild(cinfo.guild).get_channel(cinfo.announce_ch)
    to_send += "\n".join(
        f"<https://wax.atomichub.io/explorer/asset/wax-mainnet/{asset.asset_id}>" for asset in assets[:5]
    )
    to_send += (
        f"\nAvoid scams: before clicking the link, ensure the top level domain is **atomichub.io**\n"
        f"As an additional security measure, make sure I pinged you in <#{channel.id}> for this link."
        f" Impostors can't send messages in that channel.\n"
        f"More information about {cinfo.name} at <{cinfo.web}>"
    )
    try:
        await user.send(to_send)
    except (HTTPException, Forbidden) as e:
        asyncio.create_task(schedule_dm_user(user, 60 * 15, to_send))
        raise UnableToCompleteRequestedAction(
            f"I couldn't send {user.mention} their drop DM confirmation because {e}. I will try again in 10 minutes."
        )

    if announce:
        to_announce = f"{cinfo.emoji} **{memo} Giveaway**"
        if user.guild is not None:
            to_announce += f" *(in {user.guild})*"
        assets_string = " ".join(
            [
                f"[#{item.asset_id}](<https://wax.atomichub.io/explorer/asset/wax-mainnet/{item.asset_id}>)"
                for item in assets
            ]
        )
        to_announce += (
            f"\n{user.mention} ({user.id}) has been sent a random {cinfo.name} NFT, asset {assets_string}. Congrats!"
        )
        channel = bot.get_guild(cinfo.guild).get_channel(cinfo.announce_ch)
        try:
            await channel.send(to_announce)
        except Forbidden:
            pass


async def announce_and_send_link(
    bot,
    link: Claimlink,
    user: discord.Member,
    memo: str,
    num: int = 1,
    announce: bool = True,
    collection: str = DEFAULT_WAX_COLLECTION,
) -> int:
    """Send a user their claimlink and make an announcement that they won. If unable to send link, send it to
    the person who ran the command instead."""
    cinfo = get_collection_info(collection)
    if num == 1:
        to_send = f"Congratulations! You have won a random {cinfo.name} NFT! You can claim it"
    else:
        to_send = f"Congratulations! You have won {num} random {cinfo.name} NFTs! You can claim them"
    channel = bot.get_guild(cinfo.guild).get_channel(cinfo.announce_ch)
    to_send += (
        f" at the following link (just login with your wax_chain wallet, might require allowing"
        f" popups):\n[AtomicHub](<{link.ah}>) or (same NFT) [NeftyBlocks](<{link.nefty}>)\n"
        f"WARNING: Any one you share this link with can claim it. "
        f"Do not share with anyone!\n"
        f"Avoid scams: before clicking a claim link, ensure the top level domain is **atomichub.io**\n"
        f"As an additional security measure, make sure I pinged you in <#{channel.id}> for this link."
        f" Impostors can't send messages in that channel.\n"
        f"More information about {cinfo.name} at <{cinfo.web}>\n"
        f"Want to have me send links to your wallet directly in the future?\n"
        f"Then you can use the `,setwallet <address>` command, for example,"
        f"if your address is `cmcdrops4all`, use `,setwallet cmcdrops4all`."
    )
    try:
        await user.send(to_send)
    except (HTTPException, Forbidden) as e:
        asyncio.create_task(schedule_dm_user(user, 60 * 15, to_send))
        raise UnableToCompleteRequestedAction(
            f"I couldn't send {user.mention} their NFT claim link because {e}. I "
            f"will try again in 10 minutes, but if they haven't fixed their"
            f" settings by then, they will lose it."
        )

    if announce:
        to_announce = f"{cinfo.emoji} **{memo} Giveaway**"
        if user.guild is not None:
            to_announce += f" *(in {user.guild})*"
        to_announce += (
            f"\n{user.mention} ({user.id}) has been sent a random {cinfo.name}"
            f" NFT, claim link [#{link.link_id}](<{link.public}>). Congrats!"
        )
        channel = bot.get_guild(cinfo.guild).get_channel(cinfo.announce_ch)
        try:
            await channel.send(to_announce)
        except Forbidden:
            pass

    return int(link.link_id)


async def send_and_announce_drop(
    bot_,
    member: discord.Member,
    reason: str,
    collection: str = DEFAULT_WAX_COLLECTION,
    wax_con=None,
    num: int = 1,
) -> list[int]:
    """Sends and announces a drop for the specified collection.
    If the user has a linked wallet, sends the NFT directly to that wallet, otherwise uses a claimlink
    """
    if wax_con is None:
        wax_con = bot_.wax_con

    linked_wallet = await bot_.storage[None].get_note(member, "LinkedWallet")
    if linked_wallet == "Not found.":
        link: Claimlink = await wax_con.get_random_claim_link(
            str(member)[:50], memo=reason, num=num, collection=collection
        )

        assert link.link_id, (
            f"I received an invalid claimlink trying to send a claimlink to {member}. This shouldn't have happened, "
            f"please let Vyryn know. Details: {link}"
        )

        memo = wax_con.get_memo(user=str(member)[:50], memo=reason, collection=collection)
        claim_id = await announce_and_send_link(bot_, link, member, memo)

        bot_.log(f"Announced and sent link {claim_id}", "DBUG")
        return [claim_id]

    else:
        memo = wax_con.get_memo(user=str(member)[:50], memo=reason, collection=collection)
        selected_assets = await wax_con.get_random_assets_to_send(user=str(member), num=num, collection=collection)
        selected_asset_ids = [asset.asset_id for asset in selected_assets]
        await wax_con.transfer_assets(
            receiver=linked_wallet,
            asset_ids=selected_asset_ids,
            sender_ac=collection,
            memo=memo,
        )
        bot_.log(f"Directly sent assets to user's wallet {selected_asset_ids}", "DBUG")
        await announce_drop(bot_, linked_wallet, selected_assets, member, memo, num=num)
        return selected_asset_ids


async def send_link_start_to_finish(
    wax_con,
    bot_,
    message: discord.Message,
    member: discord.Member,
    sender: discord.User,
    reason: str,
    num: int = 1,
) -> list[int]:
    # Verify member
    if member is None:
        raise InvalidInput("I could not find that member. This command requires a discord mention or user id.")

    # Determine which collection is being dropped to
    authd, cinfo = determine_collection(message.guild, sender, bot_)
    collection = cinfo.collection
    # Determine whether the user can send an unlimited number of drops per day
    if authd == 0:
        raise InvalidInput(f"You can't drop {collection}s here.")

    # Confirm dropable number
    if authd == 1 and num > 1:
        num = 1
    if authd > 1 and not 1 <= num <= 10:
        raise InvalidInput("Num must be between 1 and 10.")

    # If in introduction channel, only send to people without 'introduced' role, and assign this role upon
    # completion.
    intro = False
    introduced: discord.Role | None = None
    if (
        cinfo.intro_role and cinfo.intro_ch and isinstance(message.guild, discord.Guild)
    ):  # Only consider an intro role if one is configured for this collection
        introduced = message.guild.get_role(cinfo.intro_role)
        if message.channel.id == cinfo.intro_ch:
            if introduced in member.roles:
                raise InvalidInput(
                    "That user has already been introduced. Send in a different "
                    "channel if you want to send another one."
                )
            intro = True
            assert introduced is not None, "Introduced role is not configured."
    # Don't let non-collection admins use the command in parallel due to possible reentrancy exploit.
    if not hasattr(bot_, "drop_send_reentrancy"):
        bot_.drop_send_reentrancy = {}
    if bot_.drop_send_reentrancy.get(sender.id, False):
        raise InvalidInput(
            "You may only use this command once at a time. Wait for the previous drop to complete and then try again."
        )
    elif authd < 2:
        # Reentrancy guard is only important for non-printers, because reentrancy guard is only for preventing
        # doublespends of finite drops.
        bot_.drop_send_reentrancy[sender.id] = True

    used = 0
    if authd < 2:
        # Verify nifty not spamming
        used = check_given_today(sender.id)
        if used >= cinfo.daily_limit:
            bot_.drop_send_reentrancy[sender.id] = False
            raise InvalidInput("You have given out the maximum number of drops for today. Try again tomorrow.")
        # Allow for easy testing of the daily limit
        if "test42" in reason:
            try:
                incr_given_today(sender.id)
                await message.add_reaction("✔")
                await usage_react(used, message)
            finally:
                bot_.drop_send_reentrancy[sender.id] = False
            await message.channel.send(f"Command usages today: {used + 1}/{cinfo.daily_limit}")
            return [-1]

    try:
        await message.add_reaction("⌛")

        claim_ids = await send_and_announce_drop(
            bot_=bot_,
            member=member,
            reason=reason,
            collection=collection,
            wax_con=wax_con,
            num=num,
        )

        if authd < 2:
            incr_given_today(sender.id)
    finally:
        bot_.drop_send_reentrancy[sender.id] = False

    await message.clear_reactions()
    await message.add_reaction("✔")
    if authd < 2:
        await usage_react(used, message)

    if not isinstance(member, discord.abc.Snowflake):
        raise AssertionError("Guild member' should always be a Member.")
    while intro:
        if not isinstance(introduced, discord.abc.Snowflake):
            raise AssertionError(
                "When post is classed as an intro and introduced role is defined, introduced role should be addable."
            )
        # To ensure it gets added if discord messes up initially
        await member.add_roles(introduced)
        if introduced in member.roles:
            intro = False
            await message.add_reaction("✍")
        else:
            await asyncio.sleep(1)

    return claim_ids


async def get_card_dict(
    session: aiohttp.ClientSession,
    collection: str = DEFAULT_WAX_COLLECTION,
    force: bool = False,
    page: int = 1,
    show_prices: bool = False,
) -> dict[int, dict[str, str]]:
    """
    Returns card owned addresses, refreshing as necessary
    :param session: The aiohttp session to use to fetch this information.
    :param page: Page to get; 1 is first 24 cards and is default.
    :param collection: The collection to fetch data from
    :param force: Whether to query api even if cache time hasn't passed
    :return: the dict of relevant info, has the form
    :param show_prices: Whether to get the prices for each card as well
    {collection: {template_id: {'name': name, 'max_supply': max_supply, 'undistributed': undistributed,
     'distributed_percentage': distributed_percentage}}}
    """
    global wax_dict, cache_ages
    collection_caches = cache_ages.get(collection, {})
    last_cached_time = collection_caches.get(page, 0)

    if time() - last_cached_time < WAX_CACHE_TIME and collection in wax_dict and not force and not show_prices:
        # If cache has this collection and time hasn't yet passed, use cached dict
        return wax_dict[collection]
    if not (time() - last_cached_time < WAX_CACHE_TIME and collection in wax_dict and not force):
        try:
            params = {"limit": 24, "collection_name": collection, "page": page}
            async with session.get(atomic_api + "templates", params=params) as response:
                try:
                    json_data = await response.json()
                    if response.status == 429:
                        log("I've been rate limited by the wax_chain api.", "WARN")
                        return wax_dict[collection]
                    response_data = json_data["data"]
                except (aiohttp.ContentTypeError, KeyError) as e:
                    log(f"{type(e)} trying to fetch card distribution: {e}.", "WARN")
                    return wax_dict.get(collection, {})
        except aiohttp.ClientConnectionError:
            log("Unable to connect to api to fetch card distribution.", "WARN")
            return wax_dict[collection]
        base_addr = response_data[0]["collection"]["author"]
        wax_dict[collection] = {}
        if response_data[0]["collection"]["collection_name"] != collection:
            raise NameError("Collection not found.")
        templates = {
            int(item["template_id"]): {
                "name": item["name"],
                "issued_supply": int(item["issued_supply"]),
                "max_supply": int(item["max_supply"]),
            }
            for item in response_data
        }
        _tasks = []
        for template in templates:
            _tasks.append(asyncio.create_task(get_owners(template, session, num=templates[template]["issued_supply"])))
        responses: list[tuple[int, list[str]]] = await asyncio.gather(
            *_tasks
        )  # a list of the list of owners of each card
        try:
            cache_ages[collection][page] = time()
        except KeyError:
            cache_ages[collection] = {}
            cache_ages[collection][page] = time()
        for card_id, _response in responses:
            max_card = templates[card_id]["max_supply"]
            undistributed: int = _response.count(base_addr) + (max_card - templates[card_id]["issued_supply"])
            if max_card == 0:
                distributed_percentage = 0
            else:
                distributed_percentage = int((max_card - undistributed) / max_card * 100)
            card_dict = {
                "name": templates[card_id]["name"],
                "max_supply": templates[card_id]["max_supply"],
                "undistributed": undistributed,
                "distributed_percentage": distributed_percentage,
            }
            wax_dict[collection][card_id] = card_dict

    if show_prices:
        _tasks = []
        for card_id in wax_dict[collection]:
            _tasks.append(
                asyncio.create_task(
                    get_fair_price_for_card(card_id, session, detail=True)  # type: ignore[arg-type]
                )
            )
        new_responses = await asyncio.gather(*_tasks)
        for combined_resp in new_responses:
            # Values are split out like this for type checker
            _card_id: int = combined_resp[0]
            market: float = combined_resp[1]
            sale_ema: float = combined_resp[2]
            lowest_offer: float = combined_resp[3]
            wax_dict[collection][_card_id]["fair_price"] = str(market)
            wax_dict[collection][_card_id]["sale_ema"] = str(sale_ema)
            wax_dict[collection][_card_id]["lowest_offer"] = str(lowest_offer)

    return wax_dict[collection]


async def update_cache_cards(session: aiohttp.ClientSession, force: bool = False) -> dict[int, dict[str, int]]:
    global cache_cards, card_cache_age
    collection = DEFAULT_WAX_COLLECTION
    if time() - card_cache_age < WAX_CACHE_TIME and not force:
        # If cache has this collection and time hasn't yet passed, use cached dict
        return cache_cards
    try:
        params = {"limit": 1000, "collection_name": collection}
        async with session.get(atomic_api + "templates", params=params) as response:
            try:
                json_data = await response.json()
                if response.status == 429:
                    log("I've been rate limited by the wax_chain api.", "WARN")
                    return cache_cards
                response_data = json_data["data"]
            except aiohttp.ContentTypeError:
                log("ContentTypeError trying to fetch card info.", "WARN")
                return cache_cards
    except aiohttp.ClientConnectionError:
        log("Unable to connect to api to fetch card info.", "WARN")
        return cache_cards
    if response_data[0]["collection"]["collection_name"] != collection:
        raise NameError("Collection not found.")
    cache_cards = {
        int(item["immutable_data"].get("card_id", "0")): {
            "name": item["name"],
            "rarity": item["immutable_data"].get("rarity", ""),
            "artist": item["immutable_data"].get("credits", ""),
            "class": item["immutable_data"].get("class", "other"),
            "description": item["immutable_data"].get("description", ""),
            "banano_address": item["immutable_data"].get("banano_address", ""),
            "img": item["immutable_data"]["img"],
            "created": item["created_at_time"],
            "template_id": item["template_id"],
            "issued_supply": int(item["issued_supply"]),
            "max_supply": int(item["max_supply"]),
        }
        for item in response_data
    }
    return cache_cards


async def get_fair_price_for_card(
    template_id: int,
    session: aiohttp.ClientSession,
    detail: bool = False,
    force: bool = False,
) -> Union[float, tuple[int, float, float, float]]:
    if 0 < template_id < 1000:
        template_id = await get_template_id(template_id, session)
    global template_id_price_cache_ages, template_id_price_cache
    last_cached_time = template_id_price_cache_ages.get(template_id, 0)
    if time() - last_cached_time < WAX_CACHE_TIME and template_id in template_id_price_cache and not force:
        # If cache has this collection and time hasn't yet passed, use cached dict
        sale_ema, lowest_offer = template_id_price_cache[template_id]
    else:
        sale_ema = await get_geometric_regressed_sale_price(template_id, session)
        lowest_offer = await get_lowest_current_offer(template_id, session)
        template_id_price_cache_ages[template_id] = time()
        template_id_price_cache[template_id] = (sale_ema, lowest_offer)

    market: float = fair_est(sale_ema, lowest_offer)
    if not detail:
        return market
    return template_id, market, sale_ema, lowest_offer
