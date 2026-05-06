import asyncio
from pathlib import Path
import sys

from pytest import MonkeyPatch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "greenwiz"))

from utils import green_api_wrapper


def test_get_monkeyconnect_wax_users_parses_wax_addresses(
    monkeypatch: MonkeyPatch,
) -> None:
    api = green_api_wrapper.GreenApi(session=None)
    monkeypatch.setattr(green_api_wrapper, "DISCORD_USER_LIST_AUTH_CODE", "abc123")
    monkeypatch.setattr(
        green_api_wrapper,
        "MONKEYCONNECT_DISCORD_USER_LIST_WAX_GET",
        "https://connect.cryptomonkeys.cc/accounts/api/v1/discord_user_list_wax/?code=",
    )

    async def fake_get_resp(_url: str):
        return {
            "success": True,
            "data": [
                {"753349150833115311": "jxcqy.wam"},
                {"1363261090267398396": " 4h.qy.wam "},
                {"328293174034563073": "MCONSTANT.GM"},
            ],
        }

    monkeypatch.setattr(api, "get_resp", fake_get_resp)
    result = asyncio.run(api.get_monkeyconnect_wax_users(force=True))

    assert result == {"jxcqy.wam", "4h.qy.wam", "mconstant.gm"}
    assert api.cached_monkeyconnect_wallet_to_discord_ids["jxcqy.wam"] == {
        753349150833115311
    }


def test_get_monkeyconnect_wax_users_returns_cached_when_auth_missing(
    monkeypatch: MonkeyPatch,
) -> None:
    api = green_api_wrapper.GreenApi(session=None)
    api.cached_monkeyconnect_wax_users = {"cached.wam"}
    monkeypatch.setattr(green_api_wrapper, "DISCORD_USER_LIST_AUTH_CODE", "")

    result = asyncio.run(api.get_monkeyconnect_wax_users(force=True))

    assert result == {"cached.wam"}


def test_get_monkeyconnect_wallet_to_discord_ids_parses_mapping(
    monkeypatch: MonkeyPatch,
) -> None:
    api = green_api_wrapper.GreenApi(session=None)
    monkeypatch.setattr(green_api_wrapper, "DISCORD_USER_LIST_AUTH_CODE", "abc123")

    async def fake_get_resp(_url: str):
        return {
            "success": True,
            "data": [
                {"753349150833115311": "jxcqy.wam"},
                {"1363261090267398396": "jxcqy.wam"},
            ],
        }

    monkeypatch.setattr(api, "get_resp", fake_get_resp)
    result = asyncio.run(api.get_monkeyconnect_wallet_to_discord_ids(force=True))

    assert result["jxcqy.wam"] == {753349150833115311, 1363261090267398396}
