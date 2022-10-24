"""Helpers for creating actions on atomictoolsx contract. By Vyryn"""
from aioeos import types

contract = "atomictoolsx"


def announcelink(
    creator: str, key: str, asset_ids: list[int], memo: str, authorization=None
) -> types.EosAction:
    if authorization is None:
        authorization = []
    return types.EosAction(
        account=contract,
        name="announcelink",
        authorization=authorization,
        data={"creator": creator, "key": key, "asset_ids": asset_ids, "memo": memo},
    )


def auth():
    pass


def cancellink(link_id: int, authorization=None) -> types.EosAction:
    if authorization is None:
        authorization = []
    return types.EosAction(
        account=contract,
        name="cancellink",
        authorization=authorization,
        data={"link_id": link_id},
    )


def claimlink():
    pass


def init():
    pass


def loglinkstart():
    pass


def lognewlink():
    pass
