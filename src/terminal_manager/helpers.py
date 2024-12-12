from __future__ import annotations

import slugify

from .errors import NameKeyError


def name_to_key(name: str) -> str:
    """Name to key."""
    if not name:
        raise NameKeyError

    return slugify.slugify(name, separator="_")
