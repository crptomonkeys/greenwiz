"""Helpers for creating actions on atomicassets contract. By Vyryn"""
from aioeos import types

contract = "atomicassets"


def acceptoffer():
    pass


def addcolauth():
    pass


def addconftoken():
    pass


def addnotifyacc():
    pass


def admincoledit():
    pass


def announcedepo():
    pass


def backasset():
    pass


def burnasset():
    pass


def canceloffer():
    pass


def createcol():
    pass


def createoffer():
    pass


def createschema():
    pass


def createtempl():
    pass


def declineoffer():
    pass


def extendschema():
    pass


def forbidnotify():
    pass


def init():
    pass


def locktemplate():
    pass


def logbackasset():
    pass


def logburnasset():
    pass


def logmint():
    pass


def lognewoffer():
    pass


def lognewtempl():
    pass


def logsetdata():
    pass


def logtransfer():
    pass


def mintasset(
    minter: str,
    to_addr: str,
    collection: str,
    schema: str,
    template_id: int = -1,
    immutable_data=None,
    mutable_data=None,
    authorization=None,
) -> types.EosAction:
    if authorization is None:
        authorization = []
    if mutable_data is None:
        mutable_data = []
    if immutable_data is None:
        immutable_data = []
    return types.EosAction(
        account=contract,
        name="mintasset",
        authorization=authorization,
        data={
            "authorized_minter": minter,
            "collection_name": collection,
            "schema_name": schema,
            "template_id": template_id,
            "new_asset_owner": to_addr,
            "immutable_data": immutable_data,
            "mutable_data": mutable_data,
            "tokens_to_back": [],
        },
    )


def payofferam():
    pass


def remcolauth():
    pass


def remnotifyacc():
    pass


def setassetdata():
    pass


def setcoldata():
    pass


def setmarketfee():
    pass


def setversion():
    pass


def transfer(
    from_addr: str,
    to_addr: str,
    asset_ids: list[int],
    memo: str = "",
    authorization=None,
) -> types.EosAction:
    if authorization is None:
        authorization = []
    return types.EosAction(
        account=contract,
        name="transfer",
        authorization=authorization,
        data={"from": from_addr, "to": to_addr, "asset_ids": asset_ids, "memo": memo},
    )


def withdraw():
    pass
