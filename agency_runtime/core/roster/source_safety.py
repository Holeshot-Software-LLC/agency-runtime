"""Pure, deterministic source-text safety scanning shared by roster boundaries."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

UNSAFE_TEXT_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
SUSPICIOUS_ENCODING_FINDING = "suspicious_source_encoding:markdown_heading_mojibake"
_SUSPICIOUS_HEADING_ENCODING_RE = re.compile(
    r"^#{1,6} (?:(?:[<=>](?:[\u0080-\u00ff]|')|¡) )|^#{1,6} =\r?\n ",
    re.MULTILINE,
)
_HIGH_SIGNAL_MOJIBAKE_RE = re.compile(
    r"(?:Ã[\u0080-\u00ff]|Â(?:[\u0080-\u00ff]|\s)|"
    r"â[\u0080-\u00ff\u20ac\u2018-\u2026]|ðŸ)"
)
_MAX_FINDING_CONTROL_GROUPS = 16
_MAX_FINDING_OFFSETS_PER_CONTROL = 16
_MAX_FINDING_BYTES = 4_096
_CONTROL_EVIDENCE_DOMAIN = b"agency.roster.unsafe-control-evidence.v1\0"
_DIGEST_RE = re.compile(r"[a-f0-9]{64}\Z")


@dataclass(frozen=True, slots=True)
class UnsafeSourceControl:
    """One unsafe control with bounded exact offsets and its total occurrence count."""

    codepoint: int
    byte_offsets: tuple[int, ...]
    total_count: int | None = None

    @property
    def count(self) -> int:
        return self.total_count if self.total_count is not None else len(self.byte_offsets)

    def public_dict(self) -> dict[str, object]:
        return {
            "codepoint": f"U+{self.codepoint:04X}",
            "count": self.count,
            "byte_offsets": list(self.byte_offsets),
            "offsets_truncated": self.count != len(self.byte_offsets),
        }


@dataclass(frozen=True, slots=True)
class SourceSafetyScan:
    """Stable control and high-signal encoding findings for one decoded source."""

    controls: tuple[UnsafeSourceControl, ...]
    suspicious_encoding: bool
    evidence_sha256: str = ""


def _unsafe_character(character: str) -> bool:
    return (
        bool(UNSAFE_TEXT_CONTROL_RE.fullmatch(character)) or unicodedata.category(character) == "Cf"
    )


def has_suspicious_source_encoding(content: str) -> bool:
    """Return true only for conservative, high-signal encoding-corruption markers."""

    if not isinstance(content, str):
        raise TypeError("source content must be text")
    return bool(
        "\ufffd" in content
        or "\ufeff" in content
        or _HIGH_SIGNAL_MOJIBAKE_RE.search(content)
        or _SUSPICIOUS_HEADING_ENCODING_RE.search(content)
    )


def is_unsafe_source_control(character: str) -> bool:
    """Return whether one character can invisibly alter source interpretation."""

    if not isinstance(character, str):
        raise TypeError("source character must be text")
    if len(character) != 1:
        raise ValueError("source character must contain exactly one codepoint")
    return _unsafe_character(character)


def contains_unsafe_source_control(content: str) -> bool:
    """Return whether decoded source contains a C0/C1 or Unicode format control."""

    if not isinstance(content, str):
        raise TypeError("source content must be text")
    return any(_unsafe_character(character) for character in content)


def scan_source_text(content: str) -> SourceSafetyScan:
    """Scan once, retaining bounded offsets and a commitment to every occurrence."""

    if not isinstance(content, str):
        raise TypeError("source content must be text")
    offsets: dict[int, list[int]] = {}
    counts: dict[int, int] = {}
    evidence = hashlib.sha256()
    evidence.update(_CONTROL_EVIDENCE_DOMAIN)
    byte_offset = 0
    for character in content:
        codepoint = ord(character)
        if _unsafe_character(character):
            counts[codepoint] = counts.get(codepoint, 0) + 1
            captured = offsets.setdefault(codepoint, [])
            if len(captured) < _MAX_FINDING_OFFSETS_PER_CONTROL:
                captured.append(byte_offset)
            evidence.update(codepoint.to_bytes(4, "big"))
            evidence.update(byte_offset.to_bytes(8, "big"))
        byte_offset += len(character.encode("utf-8"))
    controls = tuple(
        UnsafeSourceControl(
            codepoint,
            tuple(positions),
            counts[codepoint] if counts[codepoint] > len(positions) else None,
        )
        for codepoint, positions in sorted(offsets.items())
    )
    return SourceSafetyScan(
        controls,
        has_suspicious_source_encoding(content),
        evidence.hexdigest() if controls else "",
    )


def _controls_evidence_hash(controls: tuple[UnsafeSourceControl, ...]) -> str:
    """Hash a complete bounded control projection in canonical source-offset order."""

    if any(control.count != len(control.byte_offsets) for control in controls):
        raise ValueError("truncated controls require their source scan commitment")
    digest = hashlib.sha256()
    digest.update(_CONTROL_EVIDENCE_DOMAIN)
    occurrences = sorted(
        (offset, control.codepoint) for control in controls for offset in control.byte_offsets
    )
    for offset, codepoint in occurrences:
        digest.update(codepoint.to_bytes(4, "big"))
        digest.update(offset.to_bytes(8, "big"))
    return digest.hexdigest()


def _validated_control(control: UnsafeSourceControl) -> None:
    if (
        not isinstance(control, UnsafeSourceControl)
        or isinstance(control.codepoint, bool)
        or not isinstance(control.codepoint, int)
        or not 0 <= control.codepoint <= 0x10FFFF
        or not _unsafe_character(chr(control.codepoint))
        or not control.byte_offsets
        or len(control.byte_offsets) > _MAX_FINDING_OFFSETS_PER_CONTROL
        or any(
            isinstance(offset, bool) or not isinstance(offset, int) or offset < 0
            for offset in control.byte_offsets
        )
        or tuple(sorted(set(control.byte_offsets))) != control.byte_offsets
        or (
            control.total_count is not None
            and (
                isinstance(control.total_count, bool)
                or not isinstance(control.total_count, int)
                or control.total_count <= len(control.byte_offsets)
            )
        )
    ):
        raise ValueError("source safety scan control evidence is invalid")


def format_unsafe_control_finding(scan: SourceSafetyScan) -> str:
    """Format bounded evidence from a trusted ``scan_source_text`` result.

    A truncated projection cannot independently authenticate its digest because
    the omitted offsets are intentionally absent. Production callers therefore
    construct scans through ``scan_source_text``; this formatter only validates
    the digest's shape before carrying that scanner-owned commitment forward.
    """

    if not isinstance(scan, SourceSafetyScan):
        raise TypeError("source safety scan is invalid")
    if not scan.controls:
        return ""
    for control in scan.controls:
        _validated_control(control)
    if tuple(sorted({control.codepoint for control in scan.controls})) != tuple(
        control.codepoint for control in scan.controls
    ):
        raise ValueError("source safety scan controls must be unique and sorted")
    details: list[str] = []
    omitted = 0
    for index, control in enumerate(scan.controls):
        if index >= _MAX_FINDING_CONTROL_GROUPS:
            omitted += control.count
            continue
        detail = f"U+{control.codepoint:04X}x{control.count}"
        omitted += control.count - len(control.byte_offsets)
        detail += "@" + "|".join(str(offset) for offset in control.byte_offsets)
        details.append(detail)
    if omitted:
        evidence_hash = scan.evidence_sha256
        if not _DIGEST_RE.fullmatch(evidence_hash):
            evidence_hash = _controls_evidence_hash(scan.controls)
        details.append(f"truncated={omitted};evidence_sha256={evidence_hash}")
    finding = "unsafe_control:" + ",".join(details)
    if len(finding.encode("utf-8")) > _MAX_FINDING_BYTES:
        raise ValueError("source safety finding exceeds its byte limit")
    return finding


__all__ = [
    "SUSPICIOUS_ENCODING_FINDING",
    "UNSAFE_TEXT_CONTROL_RE",
    "SourceSafetyScan",
    "UnsafeSourceControl",
    "contains_unsafe_source_control",
    "format_unsafe_control_finding",
    "has_suspicious_source_encoding",
    "is_unsafe_source_control",
    "scan_source_text",
]
