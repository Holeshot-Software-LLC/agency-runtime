"""Cross-layer regression coverage for canonical digest ownership."""

from __future__ import annotations

import hashlib
import json

from agency_runtime.core.selector.receipt_projection import (
    _receipt_digest,
    routing_projection_digest,
)
from agency_runtime.core.store.preflight import _projection_digest
from agency_runtime.core.store.roster import _canonical_projection_digest
from agency_runtime.core.store.roster_authority import (
    _canonical_digest,
    _mapping_digest,
    roster_projection_digest,
)


def test_routing_and_store_projection_digests_share_exact_legacy_bytes() -> None:
    projection = {"z": "caf\N{LATIN SMALL LETTER E WITH ACUTE}", "a": [1, {"enabled": True}]}
    legacy_document = json.dumps(
        projection,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    expected = hashlib.sha256(legacy_document).hexdigest()

    assert routing_projection_digest(projection) == expected
    assert _receipt_digest(projection) == expected
    assert _projection_digest(projection) == expected
    assert routing_projection_digest({**projection, "z": "changed"}) != expected


def test_roster_digest_owner_preserves_bytes_mutation_and_domain_separation() -> None:
    projection = {"z": "caf\N{LATIN SMALL LETTER E WITH ACUTE}", "a": [1, {"enabled": True}]}
    label = "agency.test-roster-projection.v1"
    legacy_document = json.dumps(
        projection,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    expected = hashlib.sha256(label.encode("ascii") + b"\0" + legacy_document).hexdigest()

    assert roster_projection_digest(label, projection) == expected
    assert _canonical_projection_digest(label, projection) == expected
    assert _canonical_digest(label, projection) == expected
    assert _mapping_digest(label, projection) == expected
    assert roster_projection_digest(label, {**projection, "z": "changed"}) != expected
    assert roster_projection_digest("agency.other-domain.v1", projection) != expected
    assert routing_projection_digest(projection) != expected
