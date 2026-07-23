"""Stable workforce identities shared by contracts, storage, and receipts."""

from __future__ import annotations

import re
import uuid

_WORKER_NAMESPACE = uuid.UUID("6f09f53f-f4c2-5df5-8db9-f716ebc8db38")
_SLUG = re.compile(r"[a-z0-9][a-z0-9._-]{1,127}\Z")


def stable_worker_id(agent_slug: object) -> str:
    """Return a deterministic immutable UUID for one canonical agent slug."""

    slug = str(agent_slug or "").strip().casefold()
    if _SLUG.fullmatch(slug) is None:
        raise ValueError("worker slug is invalid")
    return str(uuid.uuid5(_WORKER_NAMESPACE, slug))


__all__ = ["stable_worker_id"]
