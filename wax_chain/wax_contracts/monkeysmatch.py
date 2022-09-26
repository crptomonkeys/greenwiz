"""Helpers for creating actions on monkeysmatch contract. By Vyryn"""
from os import urandom
from hashlib import sha256
from aioeos import types, EosKey

contract = "monkeysmatch"


def gen_salt() -> str:
    keypair = EosKey()
    nonce = urandom(32)
    digest = f"match-a-monkey-{nonce}"
    prep_data = sha256(digest.encode("utf-8")).digest()
    return keypair.sign(prep_data)


def setsalt(salt: str = None, authorization=None) -> types.EosAction:
    if authorization is None:
        authorization = []
    if salt is None:
        salt = gen_salt()
    return types.EosAction(
        account=contract, name="setsalt", authorization=authorization, data={salt}
    )
