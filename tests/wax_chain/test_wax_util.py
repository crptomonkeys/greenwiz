import asyncio
from collections import defaultdict
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

from pytest import MonkeyPatch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "greenwiz"))

from wax_chain import wax_util


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status: int) -> None:
        self._payload = payload
        self.status = status

    async def json(self, content_type: Any = None) -> dict[str, Any]:
        return self._payload

    async def __aenter__(self) -> "FakeResponse":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: Any,
    ) -> bool:
        return False


class FakeSession:
    def __init__(self, responses: dict[str, list[tuple[dict[str, Any], int]]]) -> None:
        self._responses = responses
        self.calls: defaultdict[str, int] = defaultdict(int)

    def get(self, url: str, params: dict[str, str] | None = None) -> FakeResponse:
        self.calls[url] += 1
        sequence = self._responses[url]
        index = min(self.calls[url] - 1, len(sequence) - 1)
        payload, status = sequence[index]
        return FakeResponse(payload, status)


def test_claimlink_confirmation_rotates_history_endpoints(monkeypatch: MonkeyPatch) -> None:
    async def no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(wax_util.asyncio, "sleep", no_sleep)

    bad_url = "https://bad.example"
    good_url = "https://good.example"
    responses = {
        f"{bad_url}{wax_util.wax_history_api}": [({"message": "upstream is unavailable"}, 500)],
        f"{good_url}{wax_util.wax_history_api}": [
            (
                {
                    "executed": True,
                    "actions": [{}, {"act": {"data": {"link_id": 12345}}}],
                },
                200,
            )
        ],
    }
    wax_con = wax_util.WaxConnection.__new__(wax_util.WaxConnection)
    wax_con.session = FakeSession(responses)
    wax_con.history_endpoints = [bad_url, good_url]
    wax_con.history_rpc = [SimpleNamespace(URL=bad_url), SimpleNamespace(URL=good_url)]
    wax_con.log = lambda *_args, **_kwargs: None

    link_id = asyncio.run(wax_con.get_link_id_and_confirm_claimlink_creation("tx-id"))

    assert link_id == "12345"
    assert wax_con.session.calls[f"{bad_url}{wax_util.wax_history_api}"] == 1
    assert wax_con.session.calls[f"{good_url}{wax_util.wax_history_api}"] == 1


def test_get_hyperion_actions_rotates_hyperion_endpoints() -> None:
    bad_url = "https://bad-hyperion.example"
    good_url = "https://good-hyperion.example"
    responses = {
        f"{bad_url}{wax_util.wax_actions_api}": [({"message": "error", "code": 500}, 500)],
        f"{good_url}{wax_util.wax_actions_api}": [({"actions": [{"id": 1}]}, 200)],
    }
    wax_con = wax_util.WaxConnection.__new__(wax_util.WaxConnection)
    wax_con.session = FakeSession(responses)
    wax_con.hyperion_rpc = [SimpleNamespace(URL=bad_url), SimpleNamespace(URL=good_url)]

    response = asyncio.run(wax_con.get_hyperion_actions({"account": "notify.world"}))

    assert response["actions"][0]["id"] == 1
    assert wax_con.session.calls[f"{bad_url}{wax_util.wax_actions_api}"] == 1
    assert wax_con.session.calls[f"{good_url}{wax_util.wax_actions_api}"] == 1
