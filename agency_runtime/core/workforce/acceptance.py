"""Acceptance outcomes built only from artifacts the native host wrote.

ADR-0157 makes automatic contractor promotion part of the default lifecycle,
and AR-252 requires every counted outcome to bind host-authored producer and
verifier child evidence, the exact delivered card hashes and produced artifact
digest, a distinct governed verifier selected by inference, and that verifier's
accepted verdict for that exact artifact.

Nothing in this module reads a host, the filesystem, or the Store. It is handed
two already-verified host-child delivery proofs and one verdict, and answers a
single question: does this envelope establish exactly one acceptance, and if
not, which bounded reason refuses it. That keeps the rule decidable and
testable without a host, while leaving the host artifacts the only thing that
can satisfy it.

The producer and verifier proofs must be the sealed
``agency.host-child-delivery-proof.v1`` projection. An Agency-authored
assignment or lifecycle row cannot impersonate one, because it does not carry
that schema -- which is what ``agency_only_evidence`` names. Agency rows remain
a derived audit index, never the delivery authority.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final

ACCEPTANCE_ENVELOPE_SCHEMA: Final[str] = "agency.accepted-outcome.v1"
HOST_CHILD_PROOF_SCHEMA: Final[str] = "agency.host-child-delivery-proof.v1"

MAX_ACCEPTANCE_IDENTITY_CHARACTERS: Final[int] = 256
MAX_ACCEPTANCE_CARDS: Final[int] = 64

#: The whole vocabulary a refusal may use. Callers -- CLI, dashboard, hooks --
#: render these, so a new failure mode has to be named here rather than leak an
#: unbounded string, a stack trace, or host text into evidence.
ACCEPTANCE_REASONS: Final[frozenset[str]] = frozenset(
    {
        "accepted",
        "envelope_malformed",
        "agency_only_evidence",
        "producer_evidence_missing",
        "producer_not_host_proven",
        "producer_artifact_digest_missing",
        "producer_attribution_ambiguous",
        "contractor_card_not_delivered",
        "contractor_identity_mismatch",
        "verifier_evidence_missing",
        "verifier_not_host_proven",
        "verifier_not_inference_selected",
        "shared_producer_verifier_identity",
        "verdict_missing",
        "verdict_not_bound_to_verifier",
        "verdict_artifact_mismatch",
        "verdict_rejected",
        "replayed",
    }
)

_ACCEPTED_DECISION: Final[str] = "accepted"
_HEX: Final[frozenset[str]] = frozenset("0123456789abcdef")


@dataclass(frozen=True, slots=True)
class AcceptanceOutcome:
    """One envelope's verdict, and the identities a counted outcome carries.

    ``outcome_key`` is the replay identity: the same evidence presented twice
    produces the same key, so a second recording resolves to the first event
    rather than a second success. ``artifact_digest`` is the *distinctness*
    identity: promotion counts distinct produced artifacts, because two
    verdicts on one artifact are one piece of accepted work, not two.
    """

    accepted: bool
    reason: str
    outcome_key: str = ""
    artifact_digest: str = ""
    contractor_worker_id: str = ""
    manifest: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.reason not in ACCEPTANCE_REASONS:
            raise ValueError("acceptance reason is outside the bounded vocabulary")
        if self.accepted != (self.reason == "accepted"):
            raise ValueError("acceptance reason does not agree with the verdict")


def _text(value: object) -> str:
    """Return one bounded identity string, or empty for anything else.

    An over-long or non-string identity returns empty rather than raising, so
    every malformed shape lands on a bounded refusal reason instead of an
    exception the caller would have to classify.
    """

    if not isinstance(value, str):
        return ""
    stripped = value.strip()
    if not stripped or len(stripped) > MAX_ACCEPTANCE_IDENTITY_CHARACTERS:
        return ""
    return stripped


def _digest(value: object) -> str:
    digest = _text(value).casefold()
    if len(digest) != 64 or any(character not in _HEX for character in digest):
        return ""
    return digest


def _cards(proof: Mapping[str, Any]) -> tuple[tuple[str, str, str], ...]:
    """Project the delivered cards as exact (slug, version, prompt hash) triples."""

    entries = proof.get("cards")
    if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
        return ()
    cards: list[tuple[str, str, str]] = []
    for entry in list(entries)[:MAX_ACCEPTANCE_CARDS]:
        if not isinstance(entry, Mapping):
            return ()
        slug = _text(entry.get("specialist_slug"))
        version = _text(entry.get("specialist_version"))
        prompt_hash = _text(entry.get("specialist_prompt_hash"))
        if not slug or not version or not prompt_hash:
            return ()
        cards.append((slug, version, prompt_hash))
    return tuple(cards)


def _host_proof(proof: object, *, role: str) -> tuple[str, Mapping[str, Any] | None]:
    """Accept only a verified host-written delivery proof, or name the refusal."""

    if proof is None:
        return f"{role}_evidence_missing", None
    if not isinstance(proof, Mapping):
        return "envelope_malformed", None
    if _text(proof.get("schema")) != HOST_CHILD_PROOF_SCHEMA:
        return "agency_only_evidence", None
    if proof.get("verified_delivery") is not True:
        return f"{role}_not_host_proven", None
    if not _text(proof.get("child_id")) or not _text(proof.get("host")):
        return f"{role}_not_host_proven", None
    if not _cards(proof):
        return f"{role}_not_host_proven", None
    return "", proof


def _outcome_key(
    *,
    producer_child_id: str,
    artifact_digest: str,
    verifier_child_id: str,
    verifier_decision_id: str,
    verdict_id: str,
    contractor_prompt_hash: str,
) -> str:
    material = "\0".join(
        (
            ACCEPTANCE_ENVELOPE_SCHEMA,
            producer_child_id,
            artifact_digest,
            verifier_child_id,
            verifier_decision_id,
            verdict_id,
            contractor_prompt_hash,
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _refused(reason: str) -> AcceptanceOutcome:
    return AcceptanceOutcome(accepted=False, reason=reason)


def _contractor_card(envelope: Mapping[str, Any]) -> tuple[str, str, str] | None:
    """Read the exact card identity the outcome credits, or None if malformed."""

    card = envelope.get("contractor_card")
    if not isinstance(card, Mapping):
        return None
    slug = _text(card.get("specialist_slug"))
    version = _text(card.get("specialist_version"))
    prompt_hash = _text(card.get("specialist_prompt_hash"))
    if not slug or not version or not prompt_hash:
        return None
    return slug, version, prompt_hash


def _attribution_reason(
    producer: Mapping[str, Any],
    contractor_card: tuple[str, str, str],
) -> str:
    """Refuse unless exactly one delivered card is the contractor's own."""

    named = tuple(card for card in _cards(producer) if card[0] == contractor_card[0])
    if not named:
        return "contractor_card_not_delivered"
    if len(set(named)) > 1:
        # Two revisions of one specialist reached the same child, so which card
        # did the accepted work is unresolved. Attribution has to be exact:
        # promotion is a durable status change for one immutable identity.
        return "producer_attribution_ambiguous"
    if named[0] != contractor_card:
        return "contractor_card_not_delivered"
    return ""


def _independence_reason(
    producer: Mapping[str, Any],
    verifier: Mapping[str, Any],
    *,
    contractor_slug: str,
) -> str:
    """Refuse a verifier that is the producer, its specialist, or its selection."""

    if _text(producer.get("child_id")) == _text(verifier.get("child_id")):
        return "shared_producer_verifier_identity"
    if any(card[0] == contractor_slug for card in _cards(verifier)):
        # A producer cannot verify its own work, and the same specialist running
        # as a second child is the same judgement, not a second one.
        return "shared_producer_verifier_identity"
    verifier_decision_id = _text(verifier.get("decision_id"))
    if not verifier_decision_id or verifier_decision_id == _text(producer.get("decision_id")):
        # The decision id is the recorded inference staffing identity
        # (ADR-0118). A verifier without its own decision was not independently
        # selected -- it is the producer's team read twice.
        return "verifier_not_inference_selected"
    return ""


def _verdict_reason(
    verdict: object,
    *,
    verifier_child_id: str,
    artifact_digest: str,
) -> tuple[str, str]:
    """Return the refusal reason and, when accepted, the verdict identity."""

    if verdict is None:
        return "verdict_missing", ""
    if not isinstance(verdict, Mapping):
        return "envelope_malformed", ""
    verdict_id = _text(verdict.get("verdict_id"))
    decision = _text(verdict.get("decision")).casefold()
    if not verdict_id or not decision:
        return "verdict_missing", ""
    if _text(verdict.get("verifier_child_id")) != verifier_child_id:
        return "verdict_not_bound_to_verifier", ""
    if _digest(verdict.get("artifact_digest")) != artifact_digest:
        return "verdict_artifact_mismatch", ""
    if decision != _ACCEPTED_DECISION:
        return "verdict_rejected", ""
    return "", verdict_id


def evaluate_acceptance(envelope: object) -> AcceptanceOutcome:
    """Decide whether one envelope records exactly one accepted outcome.

    Checks run in a fixed order so the same envelope always reports the same
    reason: envelope shape, producer proof, contractor attribution, verifier
    proof, producer/verifier distinctness, then the verdict itself. The first
    refusal wins, and a refusal never carries an outcome key -- there is
    nothing to count and nothing to replay.
    """

    if not isinstance(envelope, Mapping):
        return _refused("envelope_malformed")
    if _text(envelope.get("schema")) != ACCEPTANCE_ENVELOPE_SCHEMA:
        return _refused("envelope_malformed")

    contractor_worker_id = _text(envelope.get("contractor_worker_id"))
    contractor_card = _contractor_card(envelope)
    if not contractor_worker_id or contractor_card is None:
        return _refused("envelope_malformed")
    contractor_slug, contractor_version, contractor_prompt_hash = contractor_card

    reason, producer = _host_proof(envelope.get("producer"), role="producer")
    if producer is None:
        return _refused(reason)

    artifact_digest = _digest(producer.get("artifact_digest"))
    if not artifact_digest:
        return _refused("producer_artifact_digest_missing")

    reason = _attribution_reason(producer, contractor_card)
    if reason:
        return _refused(reason)

    reason, verifier = _host_proof(envelope.get("verifier"), role="verifier")
    if verifier is None:
        return _refused(reason)

    reason = _independence_reason(producer, verifier, contractor_slug=contractor_slug)
    if reason:
        return _refused(reason)

    producer_child_id = _text(producer.get("child_id"))
    verifier_child_id = _text(verifier.get("child_id"))
    verifier_decision_id = _text(verifier.get("decision_id"))
    reason, verdict_id = _verdict_reason(
        envelope.get("verdict"),
        verifier_child_id=verifier_child_id,
        artifact_digest=artifact_digest,
    )
    if reason:
        return _refused(reason)

    outcome_key = _outcome_key(
        producer_child_id=producer_child_id,
        artifact_digest=artifact_digest,
        verifier_child_id=verifier_child_id,
        verifier_decision_id=verifier_decision_id,
        verdict_id=verdict_id,
        contractor_prompt_hash=contractor_prompt_hash,
    )
    manifest = {
        "schema": ACCEPTANCE_ENVELOPE_SCHEMA,
        "acceptance_validated": True,
        "accepted_outcome_key": outcome_key,
        "contractor_worker_id": contractor_worker_id,
        "contractor_specialist_slug": contractor_slug,
        "contractor_specialist_version": contractor_version,
        "contractor_prompt_hash": contractor_prompt_hash,
        "producer_host": _text(producer.get("host")),
        "producer_child_id": producer_child_id,
        "producer_decision_id": _text(producer.get("decision_id")),
        "producer_artifact_digest": artifact_digest,
        "verifier_host": _text(verifier.get("host")),
        "verifier_child_id": verifier_child_id,
        "verifier_decision_id": verifier_decision_id,
        "verifier_specialist_slugs": sorted({card[0] for card in _cards(verifier)}),
        "verdict_id": verdict_id,
        "verdict_decision": _ACCEPTED_DECISION,
    }
    return AcceptanceOutcome(
        accepted=True,
        reason="accepted",
        outcome_key=outcome_key,
        artifact_digest=artifact_digest,
        contractor_worker_id=contractor_worker_id,
        manifest=manifest,
    )


def accepted_outcome_manifest(evidence_refs: object) -> dict[str, str] | None:
    """Read back one stored manifest, or None when the row is not an acceptance.

    ``promotion_readiness`` and the Store both need the same answer to "does
    this recorded row carry a validated host-evidenced acceptance", so the
    read-back lives beside the rule that writes it rather than being restated
    at each reader.
    """

    if not isinstance(evidence_refs, Mapping):
        return None
    if evidence_refs.get("acceptance_validated") is not True:
        return None
    if _text(evidence_refs.get("schema")) != ACCEPTANCE_ENVELOPE_SCHEMA:
        return None
    outcome_key = _digest(evidence_refs.get("accepted_outcome_key"))
    artifact_digest = _digest(evidence_refs.get("producer_artifact_digest"))
    producer_child_id = _text(evidence_refs.get("producer_child_id"))
    verifier_child_id = _text(evidence_refs.get("verifier_child_id"))
    verifier_decision_id = _text(evidence_refs.get("verifier_decision_id"))
    verdict_id = _text(evidence_refs.get("verdict_id"))
    contractor_prompt_hash = _text(evidence_refs.get("contractor_prompt_hash"))
    if not all(
        (
            outcome_key,
            artifact_digest,
            producer_child_id,
            verifier_child_id,
            verifier_decision_id,
            verdict_id,
            contractor_prompt_hash,
        )
    ):
        return None
    if producer_child_id == verifier_child_id:
        return None
    if _text(evidence_refs.get("verdict_decision")).casefold() != _ACCEPTED_DECISION:
        return None
    recomputed = _outcome_key(
        producer_child_id=producer_child_id,
        artifact_digest=artifact_digest,
        verifier_child_id=verifier_child_id,
        verifier_decision_id=verifier_decision_id,
        verdict_id=verdict_id,
        contractor_prompt_hash=contractor_prompt_hash,
    )
    if recomputed != outcome_key:
        # The stored key is derived from the stored identities. A row whose key
        # no longer follows from them was edited after the fact, so it is not
        # evidence of anything.
        return None
    return {
        "accepted_outcome_key": outcome_key,
        "artifact_digest": artifact_digest,
        "producer_child_id": producer_child_id,
        "verifier_child_id": verifier_child_id,
    }


__all__ = [
    "ACCEPTANCE_ENVELOPE_SCHEMA",
    "ACCEPTANCE_REASONS",
    "HOST_CHILD_PROOF_SCHEMA",
    "MAX_ACCEPTANCE_CARDS",
    "MAX_ACCEPTANCE_IDENTITY_CHARACTERS",
    "AcceptanceOutcome",
    "accepted_outcome_manifest",
    "evaluate_acceptance",
]
