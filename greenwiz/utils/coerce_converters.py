import re
from functools import wraps
from inspect import signature
from typing import Any, Callable


def convert(val: str) -> str:
    """Sanitize string parameters so they only contain 0-9, a-z, and _. Capitals are converted to lowercase."""
    val = re.sub(r" ", "_", val)
    return re.sub(r"\W+", "", val, flags=re.ASCII).lower()


def convert_dict(dic: dict[Any, Any]) -> dict[str, Any]:
    """Santitize dict keys so string values are all lowercase."""
    return {str(key).lower(): value for key, value in dic.items()}


def sanitize_name(func) -> Callable:  # type: ignore[type-arg]
    """Applies the above transformations to parameters of specific names in wrapped function args."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        sig = signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        if "name" in bound.arguments:
            bound.arguments["name"] = convert(bound.arguments["name"])
        if "dargs" in bound.arguments:
            bound.arguments["dargs"] = convert_dict(bound.arguments["dargs"])
        return func(*bound.args, **bound.kwargs)

    return wrapper
