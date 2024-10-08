"""Helpers for creating actions on monkeysmatch contract. By Vyryn"""

from os import urandom
from hashlib import sha256
from aioeosabi import types, EosKey

contract = "monkeysmatch"


def gen_salt() -> str:
    keypair = EosKey()
    nonce: str = str(urandom(32))
    digest = f"match-a-monkey-{nonce}"
    prep_data = sha256(digest.encode("utf-8")).digest()
    return str(keypair.sign(prep_data))


def setsalt(salt: str = "", authorization=None) -> types.EosAction:
    if authorization is None:
        authorization = []
    if salt == "":
        salt = gen_salt()
    return types.EosAction(
        account=contract, name="setsalt", authorization=authorization, data={salt}
    )
